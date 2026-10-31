# sinter's fusion_blossom decoder keeps parallel edges unmerged

Against sinter 1.16.0 and `glue/sample/src/sinter/_decoding/_decoding_fusion_blossom.py` on Stim `main` at 131793e (22 September 2026). Nothing has been posted.

`detector_error_model_to_fusion_blossom_solver_and_fault_masks` appends one edge per DEM error component and never combines components that share the same pair of detectors (sinter's mwpf adapter does, with `deduplicate_hyperedges`; PyMatching does natively). fusion-blossom accepts the parallel edges and matches on the cheapest one, i.e. on the probability of the single most likely component instead of the combined `(1 - prod(1 - 2 p_i)) / 2`.

| Case (d = 5 rotated surface code, p = 0.002, 3 seeds x 26,000 shots, true DEM) | sinter fusion_blossom | merged edges | PyMatching |
|---|---|---|---|
| X memory, Z-biased Pauli noise, eta = 1000 | 1.095 % | 0.869 % | 0.868 % |
| d = 3, X memory, eta = 1000 | 5.07 % | 1.50 % | 1.50 % |
| d = 7, X memory, eta = 1000 | 0.412 % | 0.386 % | 0.386 % |
| X memory, eta = 100 | 0.969 % | 0.812 % | 0.814 % |
| X memory, eta = 10 | 0.733 % | 0.738 % | 0.740 % |
| Z memory, plain SI1000 | 0.436 % | 0.432 % | 0.432 % |

Biased case: ratio 1.26, McNemar p = 2e-28. Depolarizing case: ratio 1.009, p = 0.83.

`parallel_edges.py` reproduces both lines; `results-*.txt` are its outputs (Linux, CPython 3.11.15, stim 1.16.0, sinter 1.16.0, fusion-blossom 0.2.13, PyMatching 2.4.0).
