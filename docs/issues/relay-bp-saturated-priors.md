Thanks for relay-bp. While testing decoders against non-nominal noise we hit two related problems when the detector error model contains a qubit that is fully randomized for a round (a crude model of leakage or a radiation burst). Both reproduce on 0.2.2 from PyPI and on `main` at d185194.

**1. `CheckMatrices.from_dem` sums edge priors, then raises.**
In the decomposed path, `error_priors = hyperedge_to_edge_matrix @ priors` adds the probabilities of the mechanisms sharing an edge. Independent mechanisms combine as `(1 - prod(1 - 2 p_i)) / 2`, which never exceeds 1/2; the sum reaches 1 or more as soon as a few mechanisms near 1/2 share an edge. `prune_decided_errors` then treats those edges as certain, and `np.sum(csc_matrix[:, to_one], axis=1)` returns an `np.matrix`, which the Rust core rejects on every decode:

```
TypeError: argument 'detectors': 'matrix' object is not an instance of 'ndarray'
```

Minimal script (stim + relay-bp only, d = 3, one data qubit depolarized at 0.75 for one round): largest edge prior after `from_dem` is 2.006, then the `TypeError`. The exception appears from a depolarization of 0.4 per TICK on a single qubit.

Converting the bias to an ndarray alone is not enough: the wrongly "decided" edges then bias the syndrome, and the logical error rate goes to ~50 % at d = 3 (13.8 % if the decoder is instead built from the nominal DEM, which ignores the event).

**2. Priors of exactly 1/2 in the min-sum core.**
A prior of 1/2 gives a log ratio of 0: those messages carry no sign, and `compute_hard_decision` uses `posterior <= 0`. Smallest example: one check, three columns with prior 0.5, empty syndrome:

```
MinSumBPDecoderF32 / RelayDecoderF32, priors [0.5, 0.5, 0.5], syndrome [0]
-> decoding [1, 1, 1], syndrome of it [1], success False (3680 iterations for Relay)
priors [0.49999] * 3 -> [0, 0, 0], success True, 3 iterations
```

`<` instead of `<=` fixes this example and leaves outputs unchanged on 300 random problems without 1/2 priors (identical SHA-256 of the decodings), but on a real leaked-ancilla DEM it is not sufficient. What worked for us was clamping priors just below 1/2 in `from_dem`.

**Measured effect of a combined fix** (combine priors, 1-D ndarray biases, clamp at 1/2 − 1e−5), d = 5 rotated surface code, SI1000 at p = 0.002, decoder compiled from the true DEM of each shot, 3 seeds × 10,000 shots, relay parameters as in decoder-bench:

| true noise | published | combined + clamped | built from nominal DEM | PyMatching, true DEM |
|---|---|---|---|---|
| random ancilla randomized for one random round | raises | 1.22 % | 3.94 % | 0.85 % |
| central data qubit randomized for one round | raises | 1.19 % | 2.71 % | 0.98 % |
| burst (strength 0.5) on a qubit and its neighbours | raises | 2.82 % | 7.73 % | 2.54 % |

Under nominal noise the combined priors differ from the summed ones by at most 2 % per edge; on 20,000 shots, 23 predictions change (97 vs 88 errors, not significant).

Scripts, outputs and the patch are available if useful. We have not tested qLDPC codes (e.g. the gross code), nor `decomposed_hyperedges=False`.
