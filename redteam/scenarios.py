"""Catalogue des bruits réels opposés au bruit nominal SI1000.

Un scénario est un mélange uniforme de variantes, chacune une règle de
réécriture site par site (voir perturb.py), suivi d'une transformation commune
facultative (diaphonie, biais). Une seule variante : bruit déterministe
(qubit chaud, dérive). Plusieurs : événement tiré au hasard à chaque tir
(fuite ou rafale à un endroit et un instant tirés au sort), et le taux mesuré
est le taux conditionnel à l'événement.

Le décodeur « informé » connaît le circuit réel de chaque tir : pour un
événement, il sait où et quand il a eu lieu (fuite annoncée). C'est la
référence d'un réglage parfait ; une moyenne des variantes ne l'est pas, elle
fait pire que le réglage nominal.
"""

from collections.abc import Callable
from dataclasses import dataclass, field

import stim

from redteam.perturb import MAX_PROBABILITY, Rule, Site, add_crosstalk, bias, rescale

Transform = Callable[[stim.Circuit], stim.Circuit]


def identity(site: Site, p: float) -> float:
    return p


@dataclass(frozen=True)
class Scenario:
    name: str
    family: str
    description: str
    rules: tuple[Rule, ...] = (identity,)
    post: Transform | None = field(default=None, compare=False)

    def true_circuits(self, nominal: stim.Circuit) -> list[stim.Circuit]:
        return [self._finish(rescale(nominal, rule)) for rule in self.rules]

    def _finish(self, circuit: stim.Circuit) -> stim.Circuit:
        return circuit if self.post is None else self.post(circuit)


# --- géométrie du code de surface tourné -------------------------------------------


def data_and_ancillas(circuit: stim.Circuit) -> tuple[list[int], list[int]]:
    """Qubits de données (mesure finale M ou MX) et ancillas (mesures MR ou MRX)."""
    data, ancillas = set(), set()
    for instruction in circuit.flattened():
        if instruction.name in ("M", "MX"):
            data.update(t.value for t in instruction.targets_copy())
        elif instruction.name in ("MR", "MRX"):
            ancillas.update(t.value for t in instruction.targets_copy())
    return sorted(data), sorted(ancillas)


def _center(circuit: stim.Circuit, qubits: list[int]) -> int:
    coords = circuit.get_final_qubit_coordinates()
    xs = [coords[q][0] for q in qubits]
    ys = [coords[q][1] for q in qubits]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    return min(qubits, key=lambda q: ((coords[q][0] - cx) ** 2 + (coords[q][1] - cy) ** 2, q))


def central_data_qubit(circuit: stim.Circuit) -> int:
    return _center(circuit, data_and_ancillas(circuit)[0])


def central_ancilla(circuit: stim.Circuit) -> int:
    return _center(circuit, data_and_ancillas(circuit)[1])


def central_coupler(circuit: stim.Circuit) -> tuple[int, int]:
    """Premier coupleur (paire CX) qui touche le qubit de données central."""
    q = central_data_qubit(circuit)
    for instruction in circuit.flattened():
        if instruction.name == "CX":
            values = [t.value for t in instruction.targets_copy()]
            for a, b in zip(values[::2], values[1::2]):
                if q in (a, b):
                    return (a, b)
    raise ValueError("aucune porte CX ne touche le qubit central")


def neighbourhood(circuit: stim.Circuit, center: int, radius: float) -> list[int]:
    coords = circuit.get_final_qubit_coordinates()
    x0, y0 = coords[center][:2]
    used = set(data_and_ancillas(circuit)[0]) | set(data_and_ancillas(circuit)[1])
    return sorted(q for q in used if (coords[q][0] - x0) ** 2 + (coords[q][1] - y0) ** 2 <= radius ** 2)


# --- règles ------------------------------------------------------------------------


def scale_kinds(factors: dict[str, float]) -> Rule:
    return lambda site, p: p * factors.get(site.kind, 1.0)


def hot_qubits(qubits: set[int], factor: float) -> Rule:
    return lambda site, p: p * factor if qubits.intersection(site.qubits) else p


def hot_coupler(pair: tuple[int, int], factor: float) -> Rule:
    key = frozenset(pair)
    return lambda site, p: p * factor if site.kind == "depol2" and frozenset(site.qubits) == key else p


def drift(rounds: int, final_factor: float) -> Rule:
    """Facteur qui croît linéairement de 1 au round 0 à `final_factor` au dernier round."""
    return lambda site, p: p * (1.0 + (final_factor - 1.0) * min(site.round, rounds) / rounds)


def randomize(qubits: set[int], first_round: int, last_round: int, strength: float = 1.0) -> Rule:
    """Qubits rendus aléatoires pendant une fenêtre de rounds : fuite approchée ou rafale.

    `strength` = 1 pousse chaque site touché à sa probabilité maximale (état
    complètement mélangé) ; une valeur plus faible interpole linéairement.
    """
    def rule(site: Site, p: float) -> float:
        if first_round <= site.round <= last_round and qubits.intersection(site.qubits):
            return p + strength * (MAX_PROBABILITY[site.kind] - p)
        return p
    return rule


# --- catalogue ---------------------------------------------------------------------


def catalog(nominal: stim.Circuit, rounds: int, p: float) -> list[Scenario]:
    """Scénarios pour un circuit nominal SI1000 à `rounds` rounds et paramètre `p`."""
    data, ancillas = data_and_ancillas(nominal)
    q_data, q_anc, coupler = central_data_qubit(nominal), central_ancilla(nominal), central_coupler(nominal)
    middle = rounds // 2
    out = [
        Scenario("nominal", "référence", "bruit réel identique au réglage"),
        Scenario("tout x3", "homogène", "tous les canaux x3", (scale_kinds(dict.fromkeys(("reset", "measure", "depol1", "depol2"), 3.0)),)),
        Scenario("mesure x6", "homogène", "retournements de mesure x6", (scale_kinds({"measure": 6.0}),)),
        Scenario("attente x10", "homogène", "dépolarisation à un qubit x10", (scale_kinds({"depol1": 10.0}),)),
    ]
    for factor in (10.0, 30.0, 100.0):
        out.append(Scenario(f"donnée chaude x{factor:g}", "local", f"qubit de données central {q_data}, tous ses canaux x{factor:g}", (hot_qubits({q_data}, factor),)))
        out.append(Scenario(f"ancilla chaude x{factor:g}", "local", f"ancilla centrale {q_anc}, tous ses canaux x{factor:g}", (hot_qubits({q_anc}, factor),)))
        out.append(Scenario(f"coupleur chaud x{factor:g}", "local", f"coupleur {coupler}, dépolarisation à deux qubits x{factor:g}", (hot_coupler(coupler, factor),)))
    for c in (1.0, 3.0):
        out.append(Scenario(f"diaphonie ZZ {c:g}p", "corrélé", f"erreur ZZ corrélée de probabilité {c:g}p sur chaque paire spectatrice après chaque couche CX", post=lambda circ, q=c * p: add_crosstalk(circ, q, "ZZ")))
        out.append(Scenario(f"diaphonie XX {c:g}p", "corrélé", f"erreur XX corrélée de probabilité {c:g}p sur chaque paire spectatrice", post=lambda circ, q=c * p: add_crosstalk(circ, q, "XX")))
    for length in (1, 2):
        leaks = tuple(randomize({q}, r, r + length - 1) for q in data for r in range(rounds))
        out.append(Scenario(f"fuite donnée {length}r", "corrélé", f"un qubit de données tiré au sort, rendu aléatoire pendant {length} round(s) tirés au sort", leaks))
        leaks = tuple(randomize({q}, r, r + length - 1) for q in ancillas for r in range(rounds))
        out.append(Scenario(f"fuite ancilla {length}r", "corrélé", f"une ancilla tirée au sort, rendue aléatoire pendant {length} round(s)", leaks))
    out.append(Scenario("fuite donnée centrale", "corrélé", f"qubit {q_data} rendu aléatoire au round {middle}", (randomize({q_data}, middle, middle),)))
    for final in (3.0, 10.0):
        out.append(Scenario(f"dérive x{final:g}", "temporel", f"tous les canaux, facteur de 1 à {final:g} du premier au dernier round", (drift(rounds, final),)))
    for strength in (0.1, 0.5):
        bursts = tuple(randomize(set(neighbourhood(nominal, q, 1.5)), r, r, strength) for q in data for r in range(rounds))
        out.append(Scenario(f"rafale {strength:g}", "temporel", f"un qubit de données et ses voisins, poussés à {strength:g} du maximum pendant un round tiré au sort", bursts))
    return out


def biased_catalog(p: float) -> list[Scenario]:
    """Scénarios biaisés vers Z, à combiner avec une mémoire X (sensible aux erreurs Z)."""
    out = [Scenario("nominal", "référence", "bruit réel identique au réglage")]
    for eta in (10.0, 100.0, 1000.0):
        out.append(Scenario(f"biais Z eta={eta:g}", "biaisé", f"dépolarisation remplacée par un canal biaisé vers Z (eta={eta:g}), même probabilité totale", post=lambda circ, e=eta: bias(circ, e)))
    return out
