Add robustness tests for detector error models with saturated priors

Follows up on #187.

Leakage-aware or recalibrated detector error models can contain mechanisms with probability exactly 1/2, for instance when one qubit is fully randomized for one round. Such a model is valid, but nominal-noise tests never produce one. This PR adds `tests/matching/robustness_test.py` with three checks on a distance-3 rotated surface code memory circuit from `stim.Circuit.generated`, with one ancilla fully depolarized during the second round:

1. the DEM really contains priors of 1/2 (guards the test itself);
2. `Matching.from_detector_error_model` builds and decodes it, decoding is deterministic, and the empty syndrome predicts no flip;
3. on shots from that circuit, decoding with the true DEM is not significantly worse than with the nominal DEM (exact one-sided sign test on discordant shots, alpha = 1e-3).

Needs only stim, numpy and pymatching; fixed seed; no network or file access; runs in under a second. PyMatching 2.4.0 passes. The same checks fail on relay-bp 0.2.2 (trmue/relay#43), which is the kind of regression they are meant to catch.

Happy to rename, move or resize anything to fit your conventions.
