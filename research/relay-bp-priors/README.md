# relay-bp: the sinter integration sums edge priors and raises on a saturated qubit

Against `relay-bp` 0.2.2 from PyPI (latest release) and `src/relay_bp/stim/sinter/check_matrices.py` on `main` at `d185194` (21 July 2026). Reported upstream in [trmue/relay#43](https://github.com/trmue/relay/issues/43) on 30 September 2026; the author opened the fix [trmue/relay#48](https://github.com/trmue/relay/pull/48) on 1 November 2026 (see the last section).

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
| `results-*-pr48.txt`, `environnement-pr48-linux.txt`, `verify-pr-48.yml`, `verify-pr-48-burst.yml` | the same scripts on the head of PR 48 (c3831ec), built from source on Linux by GitHub Actions |

```
python research/relay-bp-priors/repro_crash.py
python research/relay-bp-priors/measure_effect.py --distance 5 --shots 10000 --seeds 101 102 103
```

## Check of the upstream fix (PR 48)

[PR 48](https://github.com/trmue/relay/pull/48) combines the priors as `(1 - prod(1 - 2 p_i)) / 2`, clamps priors in `[1/2 - 1e-5, 1/2]` to `1/2 - 1e-5` on both paths of `CheckMatrices.from_dem`, returns 1-D `uint8` biases, and adds an opt-in floor `min_log_prior_ratio` on the magnitude of the log prior ratios in the min-sum core. We replayed the scripts of this folder on its head `c3831ec`, built from source on Linux ([first run](https://github.com/morvanvivien/relay/actions/runs/41352952071), workflow `verify-pr-48.yml`; [second run](https://github.com/morvanvivien/relay/actions/runs/41355173642), workflow `verify-pr-48-burst.yml`), nothing patched on our side:

| case | relay-bp 0.2.2 | PR 48 | PyMatching, same DEM |
|---|---|---|---|
| d = 5, random ancilla randomized for one round, seeds 101 to 103, 30,000 shots | `TypeError` | 367 / 30,000 = 1.22 % [1.11, 1.35] | 0.85 % |
| d = 5, central data qubit randomized for one round, seeds 101 to 103, 30,000 shots | `TypeError` | 356 / 30,000 = 1.19 % [1.07, 1.32] | 0.98 % |
| d = 5, burst (strength 0.5) on a qubit and its neighbours, seeds 101 to 103, 30,000 shots | `TypeError` | 846 / 30,000 = 2.82 % [2.64, 3.01] | 2.54 % |
| gross code, ancilla leak, seed 5, 30 shots | 14 / 30 wrong, 30 / 30 not converged | 0 / 30 wrong, 0 not converged | |
| gross code, ancilla leak, seed 6, 60 shots | 18 / 60 wrong, 60 / 60 not converged | 0 / 60 wrong, 0 not converged | |
| gross code, data qubit leak, seed 7, 60 shots | 42 / 60 wrong, 60 / 60 not converged | 0 / 60 wrong, 0 not converged | |

At d = 5 the counts are identical, seed by seed, to our clamped variant; on the two leak rows the same priors combined but not clamped still give 12.84 % and 5.60 %. The burst DEM has no prior within the clamp's range (largest 0.49998), so there the combination alone does it. In the core, without `min_log_prior_ratio`, the minimal example still decodes to `[1, 1, 1]` without success and the digest of 300 random problems is unchanged from 0.2.2; with `min_log_prior_ratio=4e-5` it decodes to `[0, 0, 0]` with success, and the digest is still unchanged.

```
python research/relay-bp-priors/repro_half_prior.py --min-log-prior-ratio 4e-5
```
