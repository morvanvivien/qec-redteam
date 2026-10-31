"""Le gross code d'IBM est chargé fidèlement et se perturbe comme le code de surface."""

import pytest

from redteam.perturb import rescale, sites
from redteam.qldpc import BASE_P, ROUNDS, _base, catalog, data_and_ancillas, gross_code


@pytest.fixture(scope="module")
def nominal():
    return gross_code(0.004)


def test_le_circuit_a_la_taille_du_code_144_12_12(nominal):
    assert nominal.num_detectors == 1728
    assert nominal.num_observables == 12
    data, ancillas = data_and_ancillas(nominal)
    assert len(data) == 144 and len(ancillas) == 144


def test_changer_p_multiplie_toutes_les_probabilites(nominal):
    noise = ("DEPOLARIZE1", "DEPOLARIZE2", "X_ERROR", "Z_ERROR", "M", "MX")
    args = {round(i.gate_args_copy()[0], 12) for i in nominal if i.name in noise and i.gate_args_copy()}
    assert args == {0.004}
    assert str(rescale(_base(), lambda s, p: p)) == str(_base())
    with pytest.raises(ValueError):
        gross_code(0.2)


def test_les_mesures_bruitees_sont_des_sites_d_un_meme_round(nominal):
    measure_rounds = {s.round for _, _, s in sites(nominal) if s is not None and s.kind == "measure"}
    assert measure_rounds == set(range(ROUNDS))
    depol2_rounds = {s.round for _, _, s in sites(nominal) if s is not None and s.kind == "depol2"}
    assert max(depol2_rounds) <= ROUNDS


def test_une_fuite_d_ancilla_ne_touche_que_son_round(nominal):
    leak = next(s for s in catalog(nominal, ROUNDS, 0.004) if s.name == "fuite ancilla")
    circuit = leak.true_circuits(nominal)[0]
    assert circuit.num_detectors == nominal.num_detectors
    halves = [i for i in circuit if i.name in ("M", "MX") and i.gate_args_copy() == [0.5]]
    assert len(halves) == 1 and len(halves[0].targets_copy()) == 1


def test_le_catalogue(nominal):
    names = [s.name for s in catalog(nominal, ROUNDS, 0.004)]
    assert names[0] == "nominal" and len(set(names)) == len(names)
    assert BASE_P == 0.001
