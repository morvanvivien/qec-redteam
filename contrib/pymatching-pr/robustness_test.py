"""Robustness checks on detector error models with saturated priors.

Leakage-aware or recalibrated detector error models can contain mechanisms
with probability exactly 1/2 (a qubit fully randomized for one round). Such a
model is valid, and nominal-noise tests never produce one. These tests check
that PyMatching builds and decodes it, that the empty syndrome still predicts
no flip, that decoding is deterministic, and that decoding with the true model
is not significantly worse than decoding with the nominal one.
"""

import math

import numpy as np
import pytest
import stim

import pymatching

P = 0.002
DISTANCE = ROUNDS = 3
SEED = 20261001


def nominal_circuit() -> stim.Circuit:
    return stim.Circuit.generated(
        "surface_code:rotated_memory_z", distance=DISTANCE, rounds=ROUNDS,
        after_clifford_depolarization=P, before_round_data_depolarization=P,
        before_measure_flip_probability=P, after_reset_flip_probability=P,
    ).flattened()


def randomized_ancilla_circuit() -> stim.Circuit:
    """The nominal circuit with one ancilla fully depolarized during the second round."""
    nominal = nominal_circuit()
    measured = next(i for i in nominal if i.name == "MR").targets_copy()
    ancilla = measured[len(measured) // 2].value
    out, rounds = stim.Circuit(), 0
    for instruction in nominal:
        if instruction.name == "MR" and rounds == 1:
            out.append("X_ERROR", [ancilla], 0.5)
        out.append(instruction)
        if instruction.name == "MR":
            rounds += 1
        if instruction.name == "TICK" and rounds == 1:
            out.append("DEPOLARIZE1", [ancilla], 0.75)
    return out


def matching_for(circuit: stim.Circuit) -> pymatching.Matching:
    dem = circuit.detector_error_model(decompose_errors=True, approximate_disjoint_errors=True)
    return pymatching.Matching.from_detector_error_model(dem)


def sign_test_p(worse: int, better: int) -> float:
    """One-sided exact p-value that `worse` discordant shots out of `worse + better` is chance."""
    n = worse + better
    return 1.0 if n == 0 else sum(math.comb(n, k) for k in range(worse, n + 1)) / 2**n


def test_randomized_ancilla_dem_has_saturated_priors():
    dem = randomized_ancilla_circuit().detector_error_model(decompose_errors=True, approximate_disjoint_errors=True)
    priors = [inst.args_copy()[0] for inst in dem.flattened() if inst.type == "error"]
    assert max(priors) == pytest.approx(0.5)


def test_decodes_dem_with_saturated_priors():
    circuit = randomized_ancilla_circuit()
    matching = matching_for(circuit)
    dets, _ = circuit.compile_detector_sampler(seed=SEED).sample(500, separate_observables=True)
    first = matching.decode_batch(dets)
    assert first.shape == (500, circuit.num_observables)
    np.testing.assert_array_equal(first, matching_for(circuit).decode_batch(dets))
    assert not matching.decode(np.zeros(circuit.num_detectors, dtype=np.uint8)).any()


def test_true_model_does_not_hurt():
    circuit = randomized_ancilla_circuit()
    dets, obs = circuit.compile_detector_sampler(seed=SEED).sample(4000, separate_observables=True)
    wrong_nominal = np.any(matching_for(nominal_circuit()).decode_batch(dets) != obs, axis=1)
    wrong_true = np.any(matching_for(circuit).decode_batch(dets) != obs, axis=1)
    worse = int((wrong_true & ~wrong_nominal).sum())
    better = int((wrong_nominal & ~wrong_true).sum())
    assert sign_test_p(worse, better) > 1e-3, f"true DEM worse on {worse} shots, better on {better}"
