# relay-bp: the sinter integration sums edge priors and raises on a saturated qubit

Against `relay-bp` 0.2.2 from PyPI (latest release) and `src/relay_bp/stim/sinter/check_matrices.py` on `main` at `d185194` (21 July 2026). Not reported upstream: no open or closed issue of `trmue/relay` mentions it (read on 29 September 2026). **Nothing has been posted.**

## Cause

`CheckMatrices.from_dem` (decomposed DEM path) sets each edge prior to

```python
error_priors = dem_matrices.hyperedge_to_edge_matrix @ dem_matrices.priors
```

that is, the **sum** of the probabilities of the mechanisms that contain the edge. Independent mechanisms combine as `(1 - prod(1 - 2 p_i)) / 2`, which never exceeds 1/2; the sum does, and reaches 1 or more as soon as a few mechanisms near 1/2 share an edge (a leaked, dead or burst-hit qubit).

`prune_decided_errors` then treats every edge whose prior is `>= 1` as an error that certainly happened. Its syndrome bias is `np.sum(csc_matrix[:, to_one], axis=1).reshape(-1) % 2`, an `np.matrix` of shape `(1, n)`, which the Rust core rejects:

```
TypeError: argument 'detectors': 'matrix' object is not an instance of 'ndarray'
```

In 0.2.2 the observables bias is also computed from the check matrix instead of the observables matrix; `main` fixed that (`Fix syndrome pruning (#42)`), not the two points above.

## What it does

| Case | Effect |
|---|---|
| nominal SI1000 noise | nothing: largest summed prior 0.03 |
| one qubit depolarized at 0.2 per TICK for one round | some edges get a prior above 1/2 |
| same at 0.4 per TICK or more | at least one edge reaches 1: every decode raises |
| only the `np.matrix` fixed (one `np.asarray`) | no exception, but the wrongly "decided" edges bias the syndrome: logical error rate near 1/2 at d = 3 |

See `results-*.txt` for the numbers.

## On the gross code

`gross_half_prior.py` runs IBM's own `bicycle_bivariate_144_12_12_memory_Z` circuit (vendored in `third_party/relay_bp/`) with one qubit randomized for one round. The DEM is not decomposable, so there is no summed prior and no exception, but 59 priors are exactly 1/2: 74 of 150 shots wrong and 150 of 150 decodes failing to converge with the priors as given, 0 and 0 with the priors clamped below 1/2 or with the nominal DEM (seeds 5, 6, 7; `results-gross_half_prior-*.txt`).

## Files

| File | What it does |
|---|---|
| `repro_crash.py` | d = 3 memory experiment, one data qubit fully depolarized for one round, one decode: `TypeError` |
| `corrected.py` | the proposed fix (combined priors, 1-D ndarray biases) and a crash-fix-only variant, patched in-process for measurement |
| `measure_effect.py` | same shots decoded by published, crash-fix-only and corrected relay-bp, all compiled from the true DEM, PyMatching as yardstick; paired ratio and McNemar test |
| `results-*.txt` | outputs on Linux, CPython 3.11.15, stim 1.16.0, relay-bp 0.2.2 |

```
python research/relay-bp-priors/repro_crash.py
python research/relay-bp-priors/measure_effect.py --distance 5 --shots 10000 --seeds 101 102 103
```
