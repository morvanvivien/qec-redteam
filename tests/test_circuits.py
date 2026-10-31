"""Le circuit de base est un code de surface tourné, mémoire Z, bruit circuit-level."""

import pytest

from redteam.circuits import rotated_memory_z


@pytest.mark.parametrize("d,expected_qubits", [(3, 17), (5, 49), (7, 97)])
def test_le_code_tourne_de_distance_d_a_2d2_moins_1_qubits(d, expected_qubits):
    circuit = rotated_memory_z(distance=d, rounds=d, p=0.001)
    # stim indexe les qubits sur une grille : seuls ceux qui ont des coordonnées sont utilisés.
    assert len(circuit.get_final_qubit_coordinates()) == expected_qubits


def test_le_circuit_porte_un_seul_observable_logique_et_des_detecteurs():
    circuit = rotated_memory_z(distance=3, rounds=3, p=0.001)
    assert circuit.num_observables == 1
    assert circuit.num_detectors > 0


def test_un_p_nul_donne_un_circuit_sans_bruit():
    circuit = rotated_memory_z(distance=3, rounds=3, p=0.0)
    texte = str(circuit)
    assert "DEPOLARIZE" not in texte
    assert "X_ERROR" not in texte


def test_un_p_hors_bornes_est_refuse():
    with pytest.raises(ValueError):
        rotated_memory_z(distance=3, rounds=3, p=0.6)
    with pytest.raises(ValueError):
        rotated_memory_z(distance=2, rounds=3, p=0.001)
