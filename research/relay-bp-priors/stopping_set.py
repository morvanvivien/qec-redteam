"""Second cause of QEC-2026-005, located in relay-bp's min-sum core: a prior of exactly 1/2
is an erasure, and the erased columns of a leaked qubit form a *stopping set*.

What the Rust core does (`crates/relay_bp/src/bp/min_sum.rs`, identical on PyPI 0.2.2 and
main d185194 up to a SIMD refactor of `min_two_magnitudes`):

1. `log_prior_ratios()` = ln((1 - p) / p). A prior of exactly 1/2 gives exactly 0. Only
   p = 0 (ratio +inf) is special-cased, to `N::max_value()`; 0 is not.
2. `compute_check_to_variable`: every outgoing message of a check has magnitude min (or
   second min) of the *other* incoming magnitudes. One incoming message of magnitude 0
   therefore silences the check for every other variable, and a variable at 1/2 only gets a
   non-zero message from a check where it is the *only* zero.
3. `compute_variable_prior` (Mem-BP, gamma0 = 0.1): prior * (1 - gamma) + posterior * gamma.
   With prior 0 and posterior 0 this stays 0 for any gamma, including the random gammas of
   the Relay sets. No number of iterations changes an exact 0.
4. `compute_hard_decision`: `posterior <= 0` decides "error". For an exact 0 the decision is
   a tie-break that never looked at the syndrome; `<` only picks the other arbitrary side.

So if the set S of columns at exactly 1/2 is a stopping set of the Tanner graph (every
detector touched by S is touched by at least two columns of S), all messages into S are
exactly 0 at every iteration, the posteriors of S are exactly 0, S is decided all-1
(published) or all-0 (`<` patch), the detectors fired around the leak are never explained,
no Relay set converges, and the decoder returns the pre-iteration decoding. This is the
classic erasure stopping set of BP; min-sum inherits it.

Clamping the priors below 1/2 (1/2 - 1e-5, log ratio 4e-5) is what repairs it: the
magnitudes are tiny but non-zero, so the signs (the syndrome parities) propagate and the
min-sum dynamics on S become a sign-only decoder, which resolves the set.

This script checks the structural claim on the real DEMs (stim, beliefmatching's
check-matrix conversion, the combined priors of our corrected CheckMatrices), then
replays the min-sum + memory update rules of min_sum.rs in numpy on sampled syndromes,
with the priors as given and clamped. It is a *replica* of the core used to exhibit the
mechanism, not relay-bp itself; the effect on relay-bp's error rate is measured in
results-measure_effect-d5-clamped.txt.

    python research/relay-bp-priors/stopping_set.py --distance 5 --p 0.002 --shots 200
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp
from beliefmatching import detector_error_model_to_check_matrices

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from redteam.decoders import dem_for  # noqa: E402
from redteam.mismatch import Setup, sample  # noqa: E402
from redteam.scenarios import central_ancilla, central_data_qubit, randomize  # noqa: E402

HALF_CAP = 0.5 - 1e-5
GAMMA0 = 0.1
PRE_ITER = 80


def combine(hyperedge_to_edge, priors: np.ndarray) -> np.ndarray:
    """Edge prior of independent mechanisms: (1 - prod(1 - 2 p_i)) / 2, as in corrected.py."""
    with np.errstate(divide="ignore"):
        log_bias = np.log(np.clip(1.0 - 2.0 * priors, 0.0, None))
    return (1.0 - np.exp(hyperedge_to_edge @ log_bias)) / 2.0


def edge_matrices(dem):
    m = detector_error_model_to_check_matrices(dem, allow_undecomposed_hyperedges=True)
    priors = combine(m.hyperedge_to_edge_matrix, m.priors)
    return sp.csr_matrix(m.edge_check_matrix), priors


def stopping_set_report(check: sp.csr_matrix, columns: np.ndarray) -> tuple[bool, int, int]:
    """(is a stopping set, number of detectors touched, minimum number of S columns per touched detector)."""
    if len(columns) == 0:
        return False, 0, 0
    degrees = np.asarray(check[:, columns].sum(axis=1)).ravel()
    touched = degrees[degrees > 0]
    return bool(touched.min() >= 2), int(len(touched)), int(touched.min())


def min_sum_replica(check: sp.csr_matrix, llr: np.ndarray, syndromes: np.ndarray, iters: int, watch: np.ndarray) -> dict:
    """Min-sum with memory, same update rules and order as min_sum.rs, vectorised over shots.

    Returns the convergence mask after `iters` iterations, and whether every message into
    the watched columns and every watched posterior stayed exactly 0 throughout.
    """
    check = check.tocsr()
    check.sort_indices()
    indptr, cols = check.indptr, check.indices
    assert np.all(np.diff(indptr) > 0), "a detector without any edge would break reduceat"
    shots, nnz = syndromes.shape[0], len(cols)
    starts = indptr[:-1]
    incidence = sp.csr_matrix((np.ones(nnz), (np.arange(nnz), cols)), shape=(nnz, len(llr)))
    watched_edges = np.isin(cols, watch)
    v2c = np.tile(llr[cols], (shots, 1))
    posterior = np.tile(llr, (shots, 1))
    syndrome_sign = syndromes.astype(np.int8)
    zero_messages, zero_posteriors = True, True
    decision = np.zeros((shots, len(llr)), dtype=np.uint8)
    for _ in range(iters):
        # check to variable: parity of signs (sign bit, so -0.0 counts as negative, like num_traits), min and second min
        signs = np.signbit(v2c).astype(np.int8)
        parity = syndrome_sign ^ np.bitwise_xor.reduceat(signs, starts, axis=1)
        magnitude = np.abs(v2c)
        min1 = np.minimum.reduceat(magnitude, starts, axis=1)
        min1_edges = np.repeat(min1, np.diff(indptr), axis=1)
        is_min = magnitude == min1_edges
        duplicated = np.add.reduceat(is_min.astype(np.int32), starts, axis=1) >= 2
        min2 = np.minimum.reduceat(np.where(is_min, np.inf, magnitude), starts, axis=1)
        min2 = np.where(duplicated, min1, min2)
        out = np.where(is_min, np.repeat(min2, np.diff(indptr), axis=1), min1_edges)
        flip = (np.repeat(parity, np.diff(indptr), axis=1) ^ signs).astype(bool)
        c2v = np.where(flip, -out, out)
        if zero_messages and np.any(c2v[:, watched_edges] != 0.0):
            zero_messages = False
        # variable to check, with Mem-BP prior using the previous posterior
        prior_eff = llr[None, :] * (1.0 - GAMMA0) + posterior * GAMMA0
        column_sum = np.asarray(c2v @ incidence)
        posterior = prior_eff + column_sum
        v2c = (prior_eff + column_sum)[:, cols] - c2v
        if zero_posteriors and np.any(posterior[:, watch] != 0.0):
            zero_posteriors = False
        decision = (posterior <= 0.0).astype(np.uint8)
    decoded = np.asarray(check @ decision.T).T % 2
    converged = np.all(decoded == syndromes, axis=1)
    return {"converged": converged, "zero_messages": zero_messages, "zero_posteriors": zero_posteriors}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--distance", type=int, default=5)
    parser.add_argument("--p", type=float, default=0.002)
    parser.add_argument("--shots", type=int, default=200)
    parser.add_argument("--seed", type=int, default=101)
    args = parser.parse_args()
    setup = Setup(args.distance, args.distance, args.p)
    nominal = setup.nominal()
    middle = args.distance // 2
    cases = {
        "fuite ancilla centrale, round du milieu": randomize({central_ancilla(nominal)}, middle, middle),
        "fuite donnée centrale, round du milieu": randomize({central_data_qubit(nominal)}, middle, middle),
    }
    print(f"d = {args.distance}, p = {args.p:g}, {args.shots} tirs par cas, graine {args.seed}, replica min-sum + mémoire gamma0 = {GAMMA0}, {PRE_ITER} itérations")
    nominal_check, nominal_priors = edge_matrices(dem_for(nominal))
    print(f"nominal : {nominal_check.shape[1]} arêtes, {int((nominal_priors == 0.5).sum())} à exactement 1/2, max {nominal_priors.max():.4f}")
    from redteam.perturb import rescale

    for name, rule in cases.items():
        circuit = rescale(nominal, rule)
        check, priors = edge_matrices(dem_for(circuit))
        half = np.flatnonzero(priors == 0.5)
        stopping, touched, min_degree = stopping_set_report(check, half)
        print(f"\n{name} : {check.shape[1]} arêtes, {len(half)} à exactement 1/2, touchant {touched} détecteurs, "
              f"au moins {min_degree} colonne(s) à 1/2 par détecteur touché -> ensemble bloquant : {'OUI' if stopping else 'non'}")
        dets, _, _ = sample([circuit], args.shots, args.seed)
        syndromes = dets.astype(np.uint8)
        with np.errstate(divide="ignore"):
            llr = np.log((1.0 - priors) / priors)
        for label, values in (("a priori tels quels (1/2 -> rapport 0)", llr), ("a priori plafonnés à 1/2 - 1e-5", np.log((1.0 - np.minimum(priors, HALF_CAP)) / np.minimum(priors, HALF_CAP)))):
            r = min_sum_replica(check, values, syndromes, PRE_ITER, half)
            print(f"  {label:40s}: messages vers S tous nuls à chaque itération : {r['zero_messages']}, "
                  f"a posteriori de S tous nuls : {r['zero_posteriors']}, syndrome satisfait après {PRE_ITER} itérations : "
                  f"{int(r['converged'].sum())}/{args.shots}")


if __name__ == "__main__":
    main()
