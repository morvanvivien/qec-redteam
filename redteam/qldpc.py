"""Gross code [[144, 12, 12]] d'IBM : circuit, géométrie et catalogue de bruits réels.

Le circuit vient tel quel des données de test de relay-bp (third_party/relay_bp,
Apache 2.0) : mémoire Z, 12 rounds, bruit circuit uniforme de probabilité p sur
tous les canaux. Les autres valeurs de p s'obtiennent en multipliant toutes les
probabilités, ce qui redonne exactement les fichiers d'IBM.

Le circuit n'a pas de coordonnées de qubits : pas de voisinage, donc ni
diaphonie ni rafale ici. Qubit « central » = le premier de sa catégorie ; sur ce
code tous les qubits de données jouent le même rôle (code bicyclique invariant
par translation).
"""

from functools import cache
from pathlib import Path

import stim

from redteam.perturb import MEASUREMENTS, rescale
from redteam.scenarios import Scenario, drift, hot_qubits, randomize, scale_kinds

CIRCUIT = Path(__file__).resolve().parents[1] / "third_party" / "relay_bp" / "gross_144_12_12_memory_Z_p0.001.stim"
BASE_P = 0.001
DISTANCE = 12
ROUNDS = 12


@cache
def _base() -> stim.Circuit:
    return stim.Circuit.from_file(CIRCUIT).flattened()


def gross_code(p: float) -> stim.Circuit:
    """Circuit du gross code sous bruit uniforme p, aplati."""
    if not 0.0 < p < 0.1:
        raise ValueError(f"p dans ]0 ; 0,1[ attendu, reçu {p}")
    factor = p / BASE_P
    return rescale(_base(), lambda site, q: q * factor)


def data_and_ancillas(circuit: stim.Circuit) -> tuple[list[int], list[int]]:
    """Données : cibles de la dernière couche de mesure ; ancillas : les autres qubits mesurés."""
    measured = [instruction for instruction in circuit.flattened() if instruction.name in MEASUREMENTS]
    data = {t.value for t in measured[-1].targets_copy()}
    others = {t.value for instruction in measured[:-1] for t in instruction.targets_copy()} - data
    return sorted(data), sorted(others)


def catalog(nominal: stim.Circuit, rounds: int, p: float) -> list[Scenario]:
    data, ancillas = data_and_ancillas(nominal)
    q_data, q_anc = data[0], ancillas[0]
    middle = rounds // 2
    out = [
        Scenario("nominal", "référence", "bruit réel identique au réglage"),
        Scenario("tout x3", "homogène", "tous les canaux x3", (scale_kinds(dict.fromkeys(("reset", "measure", "depol1", "depol2"), 3.0)),)),
        Scenario("mesure x6", "homogène", "retournements de mesure x6", (scale_kinds({"measure": 6.0}),)),
    ]
    for factor in (10.0, 100.0):
        out.append(Scenario(f"donnée chaude x{factor:g}", "local", f"qubit de données {q_data}, tous ses canaux x{factor:g}", (hot_qubits({q_data}, factor),)))
        out.append(Scenario(f"ancilla chaude x{factor:g}", "local", f"ancilla {q_anc}, tous ses canaux x{factor:g}", (hot_qubits({q_anc}, factor),)))
    out.append(Scenario("fuite donnée centrale", "corrélé", f"qubit {q_data} rendu aléatoire au round {middle}", (randomize({q_data}, middle, middle),)))
    out.append(Scenario("fuite ancilla", "corrélé", f"ancilla {q_anc} rendue aléatoire au round {middle}", (randomize({q_anc}, middle, middle),)))
    out.append(Scenario("fuite donnée 1r", "corrélé", "un qubit de données tiré au sort, aléatoire pendant un round tiré au sort",
                        tuple(randomize({q}, r, r) for q in data[::12] for r in range(0, rounds, 3))))
    out.append(Scenario("dérive x3", "temporel", "tous les canaux, facteur de 1 à 3 du premier au dernier round", (drift(rounds, 3.0),)))
    return out
