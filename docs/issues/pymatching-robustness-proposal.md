Would you be interested in a small, self-contained test for PyMatching's test suite?

It checks two things on a distance-3 rotated surface code memory circuit from `stim.Circuit.generated`, with one ancilla fully randomized for one round (priors of exactly 1/2 appear in the DEM):

1. **Holds up**: `Matching.from_detector_error_model` builds and decodes that valid DEM without raising, the empty syndrome predicts no flip, and decoding the same shots twice gives the same predictions.
2. **The true model does not hurt**: on shots from that circuit, a decoder built from the true DEM is not significantly worse than one built from the nominal DEM (exact sign test on discordant shots, alpha = 0.001).

PyMatching 2.4.0 passes both, in about 0.7 s, and so do fusion-blossom, mwpf, tesseract, beliefmatching, stimbposd and ldpc's BP+OSD / BP+LSD. The case is not hypothetical: the same test fails on relay-bp 0.2.2, where a randomized qubit makes every decode raise (reported in trmue/relay#43). The point would be a cheap guard against regressions on inputs that leakage-aware or recalibrated DEMs produce, which nominal-noise tests never exercise.

The file needs only stim, numpy and pymatching, uses a fixed seed, and has no network or file access. If this sounds useful I can open a PR adding it under `tests/`; happy to adapt names, sizes or thresholds to your conventions.
