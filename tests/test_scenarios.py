"""Le catalogue produit des bruits réels compatibles avec le décodeur nominal."""

import pytest

from redteam.circuits import rotated_memory_si1000
from redteam.perturb import Site
from redteam.scenarios import (
    biased_catalog, catalog, central_ancilla, central_coupler, central_data_qubit,
    data_and_ancillas, drift, hot_coupler, hot_qubits, neighbourhood, randomize,
)


@pytest.fixture(scope="module")
def nominal():
    return rotated_memory_si1000(distance=3, rounds=3, p=0.001).flattened()


def test_donnees_et_ancillas_du_code_de_distance_3(nominal):
    data, ancillas = data_and_ancillas(nominal)
    assert len(data) == 9
    assert len(ancillas) == 8
    assert central_data_qubit(nominal) in data
    assert central_ancilla(nominal) in ancillas
    assert central_data_qubit(nominal) in central_coupler(nominal)


def test_le_voisinage_contient_le_centre(nominal):
    q = central_data_qubit(nominal)
    around = neighbourhood(nominal, q, 1.5)
    assert q in around and len(around) == 5


def test_regles_locales():
    hot = hot_qubits({3}, 10.0)
    assert hot(Site("depol2", (3, 4), 0), 0.001) == pytest.approx(0.01)
    assert hot(Site("depol2", (5, 4), 0), 0.001) == pytest.approx(0.001)
    coupler = hot_coupler((4, 3), 5.0)
    assert coupler(Site("depol2", (3, 4), 1), 0.001) == pytest.approx(0.005)
    assert coupler(Site("depol1", (3,), 1), 0.001) == pytest.approx(0.001)


def test_la_derive_va_de_1_au_facteur_final():
    rule = drift(4, 5.0)
    assert rule(Site("depol1", (0,), 0), 0.001) == pytest.approx(0.001)
    assert rule(Site("depol1", (0,), 4), 0.001) == pytest.approx(0.005)
    assert rule(Site("depol1", (0,), 9), 0.001) == pytest.approx(0.005)


def test_la_fuite_approchee_ne_touche_que_sa_fenetre():
    rule = randomize({7}, 1, 2)
    assert rule(Site("measure", (7,), 1), 0.005) == 0.5
    assert rule(Site("depol1", (7,), 2), 0.0001) == 0.75
    assert rule(Site("depol1", (7,), 3), 0.0001) == 0.0001
    assert rule(Site("depol1", (8,), 1), 0.0001) == 0.0001
    half = randomize({7}, 0, 0, strength=0.5)
    assert half(Site("measure", (7,), 0), 0.1) == pytest.approx(0.3)


def test_chaque_scenario_garde_les_detecteurs_et_la_structure(nominal):
    scenarios = catalog(nominal, rounds=3, p=0.001)
    names = [s.name for s in scenarios]
    assert names[0] == "nominal" and len(set(names)) == len(names)
    families = {s.family for s in scenarios}
    assert {"homogène", "local", "corrélé", "temporel"} <= families
    for scenario in scenarios:
        circuits = scenario.true_circuits(nominal)
        assert circuits
        for c in circuits[:2]:
            assert c.num_detectors == nominal.num_detectors
            assert c.num_observables == nominal.num_observables


def test_les_fuites_sont_des_melanges_sur_toutes_les_positions(nominal):
    leak = next(s for s in catalog(nominal, 3, 0.001) if s.name == "fuite donnée 1r")
    assert len(leak.rules) == 9 * 3


def test_le_catalogue_biaise_part_du_nominal():
    scenarios = biased_catalog(0.001)
    assert scenarios[0].name == "nominal"
    nominal = rotated_memory_si1000(3, 3, 0.001, "x").flattened()
    biased = scenarios[-1].true_circuits(nominal)[0]
    assert any(i.name == "PAULI_CHANNEL_1" for i in biased.flattened())
