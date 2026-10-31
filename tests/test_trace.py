"""L'inspection d'une trace dit si elle est dédoublonnée et rejoue le décodage."""

import h5py
import numpy as np
import pytest

from redteam.circuits import rotated_memory_si1000
from redteam.trace import fresh_reference, summarize_trace

DISTANCE = 3
P = 0.005
SHOTS = 3000


def write_trace(path, detectors, observables, circuit):
    with h5py.File(path, "w") as f:
        f.create_dataset("syndromes", data=detectors, dtype=np.bool_)
        f.create_dataset("observables", data=observables, dtype=np.bool_)
        f.create_dataset("circuit", data=str(circuit), dtype=h5py.string_dtype(encoding="utf-8"))


@pytest.fixture
def sample():
    circuit = rotated_memory_si1000(DISTANCE, DISTANCE, P, "z")
    detectors, observables = circuit.compile_detector_sampler(seed=42).sample(shots=SHOTS, separate_observables=True)
    return circuit, detectors, observables


def test_une_trace_brute_contient_des_doublons_et_plusieurs_syndromes_nuls(tmp_path, sample):
    circuit, detectors, observables = sample
    path = tmp_path / f"surface_circuit_{DISTANCE}_{P}_z.h5"
    write_trace(path, detectors, observables, circuit)

    summary = summarize_trace(path)

    assert summary.records == SHOTS
    assert summary.detectors == circuit.num_detectors
    assert summary.unique_records < summary.records
    assert summary.zero_syndromes > 1
    assert summary.is_deduplicated is False
    assert summary.circuit_matches is True
    assert 0 <= summary.errors <= SHOTS


def test_une_trace_dedoublonnee_n_a_aucun_doublon_et_au_plus_un_syndrome_nul(tmp_path, sample):
    circuit, detectors, observables = sample
    _, first = np.unique(detectors, axis=0, return_index=True)
    first.sort()
    path = tmp_path / f"surface_circuit_{DISTANCE}_{P}_z.h5"
    write_trace(path, detectors[first], observables[first], circuit)

    summary = summarize_trace(path)

    assert summary.records == len(first)
    assert summary.unique_records == summary.records
    assert summary.zero_syndromes <= 1
    assert summary.is_deduplicated is True


def test_un_circuit_different_du_notre_est_signale(tmp_path, sample):
    _, detectors, observables = sample
    other = rotated_memory_si1000(DISTANCE, DISTANCE, 0.001, "z")
    path = tmp_path / f"surface_circuit_{DISTANCE}_{P}_z.h5"
    write_trace(path, detectors, observables, other)

    assert summarize_trace(path).circuit_matches is False


def test_un_nom_de_trace_illisible_est_refuse(tmp_path, sample):
    circuit, detectors, observables = sample
    path = tmp_path / "trace.h5"
    write_trace(path, detectors, observables, circuit)
    with pytest.raises(ValueError):
        summarize_trace(path)


def test_la_reference_fraiche_compte_les_syndromes_nuls_et_uniques():
    reference = fresh_reference(distance=DISTANCE, p=P, basis="z", shots=SHOTS, seed=42)
    assert reference.shots == SHOTS
    assert 1 < reference.zero_syndromes < SHOTS
    assert reference.unique_records < SHOTS
    assert reference.mean_weight > 0
