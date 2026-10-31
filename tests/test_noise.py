"""Le bruit SI1000 pose les bonnes probabilités sans toucher à la structure du circuit."""

import pytest

from redteam.circuits import rotated_memory_si1000


def noise_arguments(circuit, name):
    return {
        round(instruction.gate_args_copy()[0], 12)
        for instruction in circuit.flattened()
        if instruction.name == name
    }


def test_si1000_garde_les_detecteurs_et_l_observable_du_circuit_sans_bruit():
    circuit = rotated_memory_si1000(distance=7, rounds=7, p=0.005)
    assert circuit.num_detectors == 336
    assert circuit.num_observables == 1
    assert len(circuit.get_final_qubit_coordinates()) == 97


def test_si1000_applique_p_aux_portes_a_deux_qubits():
    circuit = rotated_memory_si1000(distance=3, rounds=3, p=0.005)
    assert noise_arguments(circuit, "DEPOLARIZE2") == {0.005}


def test_si1000_applique_5p_avant_mesure_et_2p_apres_reinitialisation():
    circuit = rotated_memory_si1000(distance=3, rounds=3, p=0.005)
    assert noise_arguments(circuit, "X_ERROR") == {0.025, 0.01}


def test_si1000_applique_p_sur_10_aux_portes_a_un_qubit_et_2p_a_l_attente_pendant_mesure():
    circuit = rotated_memory_si1000(distance=3, rounds=3, p=0.005)
    assert noise_arguments(circuit, "DEPOLARIZE1") == {0.0005, 0.01}


@pytest.mark.parametrize("p", [0.0, -0.001, 0.1, 0.5])
def test_un_p_hors_bornes_est_refuse(p):
    with pytest.raises(ValueError):
        rotated_memory_si1000(distance=3, rounds=3, p=p)


def test_une_base_inconnue_est_refusee():
    with pytest.raises(ValueError):
        rotated_memory_si1000(distance=3, rounds=3, p=0.001, basis="y")
