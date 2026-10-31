"""Quick robustness checks for a stim-based decoder (QEC robustness profile v0.1, E1 and E2).

Self-contained: needs only stim, numpy and the decoder under test. Runs in a
few seconds. A decoder library can drop this file into its test suite and
adapt `DECODERS` (one function per decoder: DEM in, callable out).

E1  Holds up. A valid detector error model in which one ancilla is fully
    randomized for one round (priors of exactly 1/2 appear, some mechanisms
    merge) must build and decode without raising; the empty syndrome must
    predict no observable flip; decoding the same shots twice must give the
    same predictions.
E2  The true model does not hurt. On shots from that circuit, a decoder built
    from the true DEM must not make significantly more logical errors than
    the same decoder built from the nominal DEM (exact one-sided sign test on
    the discordant shots, alpha = 0.001).

Method, rationale and results on nine public decoders:
https://github.com/morvanvivien/qec-redteam (docs/profil-robustesse-v0.1.md).
"""

import math
from collections.abc import Callable

import numpy as np
import pytest
import stim

P = 0.002
DISTANCE = ROUNDS = 3
SEED = 20261001
SHOTS_E1, SHOTS_E2 = 500, 4000
ALPHA = 1e-3

Decoder = Callable[[np.ndarray], np.ndarray]


def pymatching_decoder(dem: stim.DetectorErrorModel) -> Decoder:
    import pymatching

    matching = pymatching.Matching.from_detector_error_model(dem)
    return lambda dets: matching.decode_batch(dets).astype(bool)


DECODERS: dict[str, Callable[[stim.DetectorErrorModel], Decoder]] = {"pymatching": pymatching_decoder}


def nominal_circuit() -> stim.Circuit:
    return stim.Circuit.generated(
        "surface_code:rotated_memory_z", distance=DISTANCE, rounds=ROUNDS,
        after_clifford_depolarization=P, before_round_data_depolarization=P,
        before_measure_flip_probability=P, after_reset_flip_probability=P,
    ).flattened()


def randomized_ancilla_circuit() -> stim.Circuit:
    """The nominal circuit with one ancilla fully depolarized during the second round."""
    nominal = nominal_circuit()
    measured_ancillas = next(i for i in nominal if i.name == "MR").targets_copy()
    ancilla = measured_ancillas[len(measured_ancillas) // 2].value
    out, measured = stim.Circuit(), 0
    for instruction in nominal:
        if instruction.name == "MR" and measured == 1:
            out.append("X_ERROR", [ancilla], 0.5)
        out.append(instruction)
        if instruction.name == "MR":
            measured += 1
        if instruction.name == "TICK" and measured == 1:
            out.append("DEPOLARIZE1", [ancilla], 0.75)
    return out


def dem_of(circuit: stim.Circuit) -> stim.DetectorErrorModel:
    return circuit.detector_error_model(decompose_errors=True, approximate_disjoint_errors=True, ignore_decomposition_failures=True)


def sign_test_p(worse: int, better: int) -> float:
    """One-sided exact p-value that `worse` discordant shots is not just chance against `better`."""
    n = worse + better
    return 1.0 if n == 0 else sum(math.comb(n, k) for k in range(worse, n + 1)) / 2**n


@pytest.mark.parametrize("name", sorted(DECODERS))
def test_e1_holds_up_on_a_randomized_ancilla(name):
    build = DECODERS[name]
    nominal, randomized = nominal_circuit(), randomized_ancilla_circuit()
    dets, _ = nominal.compile_detector_sampler(seed=SEED).sample(SHOTS_E1, separate_observables=True)
    assert np.array_equal(build(dem_of(nominal))(dets), build(dem_of(nominal))(dets)), "same shots, different predictions"
    zero = np.zeros((1, nominal.num_detectors), dtype=bool)
    assert not build(dem_of(nominal))(zero).any(), "empty syndrome flips an observable (nominal DEM)"
    informed = build(dem_of(randomized))
    leak_dets, _ = randomized.compile_detector_sampler(seed=SEED).sample(SHOTS_E1, separate_observables=True)
    informed(leak_dets)
    assert not informed(zero).any(), "empty syndrome flips an observable (DEM with a randomized ancilla)"


@pytest.mark.parametrize("name", sorted(DECODERS))
def test_e2_true_model_does_not_hurt(name):
    build = DECODERS[name]
    randomized = randomized_ancilla_circuit()
    dets, obs = randomized.compile_detector_sampler(seed=SEED).sample(SHOTS_E2, separate_observables=True)
    wrong_tuned = np.any(build(dem_of(nominal_circuit()))(dets) != obs, axis=1)
    wrong_informed = np.any(build(dem_of(randomized))(dets) != obs, axis=1)
    worse, better = int((wrong_informed & ~wrong_tuned).sum()), int((wrong_tuned & ~wrong_informed).sum())
    assert sign_test_p(worse, better) > ALPHA, f"true DEM hurts: {worse} shots worse, {better} better"
