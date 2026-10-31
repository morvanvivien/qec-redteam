"""Bruit réel différent du bruit nominal : réécriture d'un circuit SI1000 site par site.

Le décodeur est réglé sur le circuit nominal ; le circuit perturbé produit les
tirs. Les deux gardent exactement les mêmes détecteurs et observables, seules
les probabilités des canaux de bruit changent, et des canaux s'ajoutent.

Un site de bruit est décrit par son type, ses qubits et son round :

    reset     retournement juste après une réinitialisation
    measure   retournement juste avant une mesure
    depol1    dépolarisation à un qubit (porte, attente, attente pendant mesure)
    depol2    dépolarisation à deux qubits après une porte CX ou CZ

Le round d'un site est le nombre de couches de mesure déjà passées : 0 avant la
première mesure des ancillas, `rounds` pour la mesure finale des données.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass

import stim

FLIP_CHANNELS = ("X_ERROR", "Y_ERROR", "Z_ERROR")
MEASUREMENTS = ("M", "MR", "MX", "MY", "MRX", "MRY", "MZ", "MRZ")
RESETS = ("R", "RX", "RY", "RZ")
TWO_QUBIT_GATES = ("CX", "CZ", "CNOT", "ZCX", "ZCZ")
KINDS = ("reset", "measure", "depol1", "depol2")
# Ni porte ni mesure : ne referment pas une couche de mesure.
PASSIVE = ("DEPOLARIZE1", "DEPOLARIZE2", "X_ERROR", "Y_ERROR", "Z_ERROR", "PAULI_CHANNEL_1", "PAULI_CHANNEL_2",
           "E", "ELSE_CORRELATED_ERROR", "DETECTOR", "OBSERVABLE_INCLUDE", "QUBIT_COORDS", "SHIFT_COORDS")
MAX_PROBABILITY = {"reset": 0.5, "measure": 0.5, "depol1": 0.75, "depol2": 15 / 16}


@dataclass(frozen=True)
class Site:
    kind: str
    qubits: tuple[int, ...]
    round: int


Rule = Callable[[Site, float], float]


def _kind(name: str, previous: str | None, following: str | None, noisy_measure: bool = False) -> str | None:
    if name in MEASUREMENTS:
        # Mesure qui porte elle-même sa probabilité de retournement, M(p).
        return "measure" if noisy_measure else None
    if name == "DEPOLARIZE1":
        return "depol1"
    if name == "DEPOLARIZE2":
        return "depol2"
    if name in FLIP_CHANNELS:
        if following in MEASUREMENTS:
            return "measure"
        if previous in RESETS or previous in MEASUREMENTS:
            return "reset"
    return None


def _clip(kind: str, p: float) -> float:
    if p < 0.0:
        raise ValueError(f"probabilité négative pour un site {kind} : {p}")
    return min(p, MAX_PROBABILITY[kind])


def _groups(targets: list[stim.GateTarget], width: int) -> list[tuple[int, ...]]:
    values = [t.value for t in targets]
    return [tuple(values[i:i + width]) for i in range(0, len(values), width)]


def sites(circuit: stim.Circuit) -> Iterable[tuple[int, stim.CircuitInstruction, Site | None]]:
    """Parcourt le circuit aplati : (indice, instruction, site de bruit ou None).

    Une couche de mesure est une suite de mesures que ne sépare aucune porte
    (seulement du bruit ou des annotations) : M puis MX dans un même round compte
    une fois. Le round avance à la première mesure
    de chaque couche ; les retournements portés par la mesure elle-même, M(p),
    appartiennent au round qui se termine.
    """
    flat = list(circuit.flattened())
    current_round = 0
    layer_open = False
    for index, instruction in enumerate(flat):
        name = instruction.name
        previous = flat[index - 1].name if index > 0 else None
        following = flat[index + 1].name if index + 1 < len(flat) else None
        measured_round = current_round
        if name in MEASUREMENTS:
            if layer_open:
                measured_round = current_round - 1
            else:
                current_round += 1
                layer_open = True
        elif name not in PASSIVE:
            layer_open = False
        kind = _kind(name, previous, following, bool(instruction.gate_args_copy()))
        if kind is None:
            yield index, instruction, None
            continue
        if kind == "measure" and name in MEASUREMENTS and any(t.is_inverted_result_target for t in instruction.targets_copy()):
            raise ValueError("mesure à résultat inversé non prise en charge")
        width = 2 if kind == "depol2" else 1
        round_of_site = measured_round if name in MEASUREMENTS else current_round
        for group in _groups(instruction.targets_copy(), width):
            yield index, instruction, Site(kind, group, round_of_site)


def rescale(circuit: stim.Circuit, rule: Rule) -> stim.Circuit:
    """Nouveau circuit où chaque site de bruit prend la probabilité `rule(site, p)`.

    Les cibles d'une même instruction sont regroupées par probabilité, dans
    l'ordre d'origine, pour garder un circuit compact et lisible.
    """
    out = stim.Circuit()
    pending: list[tuple[str, float, tuple[int, ...]]] = []
    last_index = None

    def flush() -> None:
        for name, p, qubits in pending:
            if name in MEASUREMENTS:
                # Une mesure ne disparaît jamais, même sans bruit.
                out.append(name, list(qubits), p)
            elif p > 0.0:
                out.append(name, list(qubits), p)
        pending.clear()

    for index, instruction, site in sites(circuit):
        if index != last_index:
            flush()
            last_index = index
        if site is None:
            out.append(instruction)
            continue
        p = _clip(site.kind, rule(site, instruction.gate_args_copy()[0]))
        if pending and pending[-1][0] == instruction.name and pending[-1][1] == p:
            name, _, qubits = pending[-1]
            pending[-1] = (name, p, qubits + site.qubits)
        else:
            pending.append((instruction.name, p, site.qubits))
    flush()
    return out


def two_qubit_layers(circuit: stim.Circuit) -> list[tuple[int, list[tuple[int, int]]]]:
    """Couches de portes à deux qubits : (indice dans le circuit aplati, paires)."""
    layers = []
    for index, instruction in enumerate(circuit.flattened()):
        if instruction.name in TWO_QUBIT_GATES:
            pairs = [(a, b) for a, b in _groups(instruction.targets_copy(), 2)]
            layers.append((index, pairs))
    return layers


def spectator_pairs(circuit: stim.Circuit, pairs: list[tuple[int, int]], reach: float = 1.5) -> list[tuple[int, int]]:
    """Paires de qubits voisins appartenant à deux portes différentes de la même couche.

    Deux qubits sont voisins quand leurs coordonnées sont à moins de `reach`
    (diagonale du réseau tourné : racine de 2). C'est le lieu de la diaphonie
    entre portes simultanées.
    """
    coords = circuit.get_final_qubit_coordinates()
    owner = {q: i for i, pair in enumerate(pairs) for q in pair}
    found = set()
    qubits = sorted(owner)
    for i, a in enumerate(qubits):
        for b in qubits[i + 1:]:
            if owner[a] == owner[b]:
                continue
            (xa, ya), (xb, yb) = coords[a][:2], coords[b][:2]
            if (xa - xb) ** 2 + (ya - yb) ** 2 <= reach ** 2:
                found.add((a, b))
    return sorted(found)


def add_crosstalk(circuit: stim.Circuit, probability: float, pauli: str = "ZZ", reach: float = 1.5) -> stim.Circuit:
    """Ajoute, après chaque couche CX, une erreur corrélée sur les paires spectatrices.

    `pauli` vaut "ZZ", "XX" ou "DEP" (dépolarisation à deux qubits). Le cas ZZ
    est la diaphonie de type couplage résiduel entre transmons voisins.
    """
    if not 0.0 <= probability <= 0.5:
        raise ValueError(f"probabilité de diaphonie dans [0, 0,5] attendue, reçu {probability}")
    if pauli not in ("ZZ", "XX", "DEP"):
        raise ValueError(f"pauli parmi ZZ, XX, DEP attendu, reçu {pauli!r}")
    flat = circuit.flattened()
    inserts = {index: spectator_pairs(flat, pairs, reach) for index, pairs in two_qubit_layers(flat)}
    out = stim.Circuit()
    for index, instruction in enumerate(flat):
        out.append(instruction)
        # Le bruit SI1000 de la porte suit la porte : on insère après lui.
        anchor = index - 1 if instruction.name == "DEPOLARIZE2" else None
        if anchor in inserts and probability > 0.0:
            for a, b in inserts[anchor]:
                if pauli == "DEP":
                    out.append("DEPOLARIZE2", [a, b], probability)
                else:
                    p1 = pauli[0]
                    out.append("CORRELATED_ERROR", [stim.target_pauli(a, p1), stim.target_pauli(b, p1)], probability)
    return out


def bias(circuit: stim.Circuit, eta: float) -> stim.Circuit:
    """Remplace la dépolarisation par un canal de Pauli biaisé vers Z, à probabilité totale égale.

    À un qubit, `eta` = pZ / (pX + pY), la convention de Tuckett et al. ;
    eta = 0,5 redonne le canal dépolarisant. À deux qubits, `eta` est le rapport
    de la masse des termes faits de Z et de I (IZ, ZI, ZZ) à celle des douze
    autres, répartie à parts égales dans chaque groupe ; eta = 0,25 redonne le
    canal dépolarisant. Les retournements de mesure restent inchangés.
    """
    if eta <= 0.0:
        raise ValueError(f"eta positif attendu, reçu {eta}")
    out = stim.Circuit()
    for instruction in circuit.flattened():
        name = instruction.name
        if name == "DEPOLARIZE1":
            p = instruction.gate_args_copy()[0]
            pz = p * eta / (eta + 1.0)
            out.append("PAULI_CHANNEL_1", instruction.targets_copy(), [(p - pz) / 2, (p - pz) / 2, pz])
        elif name == "DEPOLARIZE2":
            out.append("PAULI_CHANNEL_2", instruction.targets_copy(), _biased_two_qubit(instruction.gate_args_copy()[0], eta))
        else:
            out.append(instruction)
    return out


def _biased_two_qubit(p: float, eta: float) -> list[float]:
    # Ordre de stim : IX IY IZ XI XX XY XZ YI YX YY YZ ZI ZX ZY ZZ.
    labels = [a + b for a in "IXYZ" for b in "IXYZ"][1:]
    z_only = [set(label) <= {"I", "Z"} for label in labels]
    n_z, n_other = sum(z_only), len(labels) - sum(z_only)
    pz_total = p * eta / (eta + 1.0)
    return [pz_total / n_z if z else (p - pz_total) / n_other for z in z_only]
