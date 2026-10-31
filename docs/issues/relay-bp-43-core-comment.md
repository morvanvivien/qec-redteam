Follow-up on the second problem (priors of exactly 1/2): we located why `<` alone does not fix a real leaked-qubit DEM, and what does.

A prior of exactly 1/2 is an erasure: `log_prior_ratios()` returns exactly 0 for it (only p = 0 is special-cased, to `N::max_value()`). In `compute_check_to_variable`, every outgoing message of a check takes the minimum (or second minimum) magnitude of the *other* incoming messages, so one incoming magnitude of 0 silences the check for every other variable, and the 1/2 variable itself only receives a non-zero magnitude from a check where it is the only zero. On a real leak DEM the columns at 1/2 form a **stopping set** of the Tanner graph: on the d = 5 rotated surface code (SI1000, p = 0.002, one ancilla or one data qubit randomized for one round, decomposed DEM, priors combined as in our earlier message), the 14 columns at exactly 1/2 touch 10 detectors, each at least twice. Hence every message into that set is exactly 0 at every iteration, its posteriors stay exactly 0 (the Mem-BP prior `prior * (1 - gamma) + posterior * gamma` and the random gammas of the Relay sets multiply a 0), and `compute_hard_decision` decides the whole set as "error" (`<= 0`) or as "no error" (`<`) without ever looking at the syndrome. The detectors fired around the leak are then explained by nobody, no Relay set converges, and `decode_detailed` returns the pre-iteration decoding. This is the classic erasure stopping set of BP; min-sum inherits it.

We checked this with a numpy replica of the `min_sum.rs` update rules (same message schedule, gamma0 = 0.1, 80 iterations, 200 sampled syndromes per case, seed 101):

| case | columns at 1/2 | detectors touched | stopping set | messages into the set / its posteriors | syndrome satisfied after 80 iterations, priors as given | priors clamped to 1/2 − 1e−5 |
|---|---|---|---|---|---|---|
| d = 5, central ancilla, middle round | 14 | 10 | yes | exactly 0 at every iteration | 2 / 200 | 67 / 200 |
| d = 5, central data qubit, middle round | 14 | 10 | yes | exactly 0 | 0 / 200 | 59 / 200 |
| d = 3, central ancilla | 12 | 7 | yes | exactly 0 | 1 / 200 | 79 / 200 |
| d = 3, central data qubit | 14 | 10 | yes | exactly 0 | 0 / 200 | 75 / 200 |

Clamping works because a log ratio of 4e−5 keeps a sign: the magnitudes are tiny but non-zero, the syndrome parities propagate, and on the stopping set min-sum behaves like a sign-only decoder. That is consistent with the numbers already posted (1.22 % with the clamp against 12.84 % with combined priors only, ancilla leak, 3 seeds).

We also tried the equivalent fix inside the core, independent of the stim module: in `MinSumBPDecoder::new`, replace any log prior ratio with |LLR| < 4e−5 by +4e−5, and use `<` in `compute_hard_decision` (patch against the 0.2.2 sdist, 20 lines). Built with maturin, `cargo test -p relay-bp --release` passes (13/13), the minimal example gives `[0, 0, 0]` with success, and the SHA-256 digest of the decodings on 300 random problems without 1/2 priors is unchanged. Same paired measurement as before (d = 5 rotated surface code, SI1000 p = 0.002, 3 seeds × 10,000 shots, decoders built from the true DEM, combined priors, **no Python-side clamp**):

| true noise | combined priors, published core | combined priors, patched core | combined + clamped, published core | PyMatching, true DEM |
|---|---|---|---|---|
| random ancilla randomized for one random round | 12.84 % | **1.24 %** [1.12; 1.38] | 1.22 % | 0.87 % |
| central data qubit randomized for one round | 5.60 % | **1.26 %** [1.14; 1.40] | 1.19 % | 1.01 % |

Known limit of this patch: with the fixed-point variants (`int_bits`/`frac_bits`), `N::from_f64(4e-5)` may round to 0; it only really covers F32/F64. A cleaner fix would treat priors of exactly 1/2 as erasures and peel them before BP. The patch and the scripts (stim, numpy, beliefmatching only) are available if useful.

One harmless detail noticed on the way: with `num_traits`, `is_negative(-0.0)` is true, so the signed zeros produced by `.neg()` flip sign parities between zero-magnitude messages; magnitudes stay zero, so decisions do not depend on it.
