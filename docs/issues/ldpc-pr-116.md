Fixes #105.

`DenseOsdDecoder::osd_setup` has the same out-of-bounds write that #112 fixes in `OsdDecoder::osd_setup`: candidates have length `k`, but the weight-2 loop runs over `i, j < osd_order`. In LSD, `k` is the dimension of one cluster and `osd_order` is the global `lsd_order`, so `lsd_cs` hits this on ordinary decodes. That is the crash reported in #105.

#112 only touches `osd.hpp`, and `BpLsdDecoder` goes through `osd_dense.hpp`, so `lsd_cs` still writes out of bounds with #112 applied. This PR uses the same `min(osd_order, k)` bound, only touches `osd_dense.hpp` and its test, and does not conflict with #112.

### Verification

Linux, Python 3.12, built from source with `-D_GLIBCXX_ASSERTIONS` so that an out-of-bounds `std::vector::operator[]` aborts at once ([run](https://github.com/morvanvivien/ldpc/actions/runs/41219503381), [workflow and scripts](https://github.com/morvanvivien/ldpc/tree/verify-fix-105/verify)).

| | main | #112 alone | this PR alone | both |
|---|---|---|---|---|
| new test | abort | abort | pass | pass |
| d = 5 surface code, `lsd_cs` order 10, one decode per process, up to 60 shots | abort at shot 1 | abort at shot 1 | clean | clean |
| C++ driver on `DenseOsdDecoder`, order 10, k = 1, 5, 9 | abort | abort | not run | clean |

Without bounds checks, the C++ driver prints byte-identical decodings for main and for both fixes wherever main survives: 56 combinations of decoder, k and order, 500 decodes each.

Two limits:

- A default build usually does not notice the write, so the new test only fails on the old code when built with `-D_GLIBCXX_ASSERTIONS`.
- `test_soft_info_decoder.py::test_one_errored_syndrome_bit` and `test_long_rep_code` fail on main without any change, and fail the same way here. I left them alone. The other 127 tests in `python_test/` pass.

This fix and its verification were written with AI assistance.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
