`detector_error_model_to_fusion_blossom_solver_and_fault_masks` in `glue/sample/src/sinter/_decoding/_decoding_fusion_blossom.py` appends one edge per error component and never combines components that land on the same pair of detectors. fusion-blossom keeps the parallel edges and matches on the cheapest, so it sees the probability of the single most likely component instead of their combined probability `(1 - prod(1 - 2 p_i)) / 2`. The mwpf adapter next to it already merges identical hyperedges (`deduplicate_hyperedges`), and PyMatching merges parallel edges natively.

Under depolarizing noise this is invisible (one component dominates each edge). Under biased noise it is not. Rotated surface code d = 5, X memory, SI1000 at p = 0.002 with each depolarizing channel replaced by a Z-biased Pauli channel of the same total probability (eta = 1000), decoders built from the true DEM, same shots, 3 seeds x 26,000:

| | logical error rate |
|---|---|
| `fusion_blossom` via sinter | 1.095 % |
| same solver, parallel components merged before weighting | 0.869 % |
| `pymatching` | 0.868 % |

The gap is largest on small codes: at eta = 1000 it is 5.07 % vs 1.50 % at d = 3 (ratio 3.4) and 0.412 % vs 0.386 % at d = 7 (ratio 1.07, p = 0.008), the merged version matching PyMatching each time. At d = 5 it grows with the bias: ratio 0.99 at eta = 10 (p = 0.67), 1.19 at eta = 100 (p = 2e-18), 1.26 at eta = 1000. The DEM gives 3,724 edges over 502 distinct detector pairs, 480 of which carry parallel edges. McNemar test between the first two rows: p = 2e-28. With plain SI1000 (Z memory, same size) the two versions agree: 0.436 % vs 0.432 %, p = 0.83. Checked on sinter 1.16.0; the function is unchanged on main at 131793e.

A fix would group components by (detector pair, observable mask) and combine their probabilities before computing weights, as the mwpf adapter does. Happy to open a PR if that is welcome.
