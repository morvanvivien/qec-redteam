Follow-up: the second problem (priors of exactly 1/2) also shows up on the gross code, where it matters most.

We took `bicycle_bivariate_144_12_12_memory_Z` from your own `tests/testdata` (p = 0.001 file, all probabilities scaled to p = 0.003) and randomized a single qubit for one round (every channel touching it pushed to its maximum: 3/4 for single-qubit depolarization, 1/2 for its measurement flip). The DEM is not decomposable, so `CheckMatrices.from_dem` takes the non-decomposed path: no summed priors, no exception. But the DEM then has 59 columns with a prior of exactly 1/2.

Same shots, `RelayDecoderF32` with decoder-bench parameters (gamma0 0.1, pre_iter 80, num_sets 60, set_max_iter 60, stop_nconv 3), a shot counted wrong if any of the 12 observables is wrong:

| decoder built from | wrong shots | `success == False` | median iterations |
|---|---|---|---|
| true DEM, priors as given | 74 / 150 (49 %) | 150 / 150 | 3680 (budget exhausted) |
| true DEM, priors clamped to 1/2 − 1e−5 | 0 / 150 | 0 / 150 | 407–519 |
| nominal DEM (ignores the event) | 0 / 150 | 0 / 150 | 246–368 |

Three independent seeds (5, 6, 7), one ancilla leak and one data-qubit leak. Clamping the priors just below 1/2 in `from_dem` removes the problem and leaves every prior below the cap unchanged.
