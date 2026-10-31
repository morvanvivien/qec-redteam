Small addition: the effect is larger in Z memory than in the X-memory case above. Same d = 5 rotated surface code, SI1000 at p = 0.002 with Z-biased depolarizing channels, but `rotated_memory_z`, decoders built from the true DEM, same shots, 3 seeds x 200,000:

| | eta = 100 | eta = 1000 |
|---|---|---|
| `fusion_blossom` via sinter | 0.0565 % | 0.0562 % |
| same solver, parallel components merged | 0.0318 % | 0.0305 % |
| `pymatching` | 0.0318 % | 0.0305 % |
| ratio sinter / merged, McNemar p | 1.78, p = 5e-41 | 1.84, p = 3e-45 |

The merged version makes exactly the same number of errors as PyMatching in both cases (191 and 183 out of 600,000). In a tuned-versus-informed comparison this shows up as fusion-blossom doing *worse* when given the true (biased) DEM than when given the nominal one (error-rate ratio 0.61 at eta = 100, 0.65 at eta = 1000), which is how we noticed it again.

One correction to my offer above: I had missed the warning in CONTRIBUTING.md about AI-generated code. This analysis and my scripts were written with AI tools, so I will not open a PR. The fix is small if someone wants to write it: combine the components landing on the same detector pair before computing weights, as `deduplicate_hyperedges` already does in the mwpf adapter. `detector_error_model_to_fusion_blossom_solver_and_fault_masks` is still unchanged on main today.
