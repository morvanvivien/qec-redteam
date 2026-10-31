# ldpc #105: out-of-bounds write in the OSD combination sweep

Root cause, reproducers and a verified fix for https://github.com/quantumgizmos/ldpc/issues/105, against `ldpc` 2.4.1 (commit `d3429964cd`).

## Cause

`DenseOsdDecoder::osd_setup()` (`src_cpp/osd_dense.hpp`, lines 84 to 95) and `OsdDecoder::osd_setup()` (`src_cpp/osd.hpp`, lines 90 to 99) build combination-sweep candidates of length `k` but set `candidate[i]` and `candidate[j]` for every `i < j < osd_order`. Any `k < osd_order` writes past the end of the vector. In LSD, `k` is the dimension of one cluster, so it can be far below `lsd_order`.

## Files

| File | What it does | Needs |
|---|---|---|
| `repro_osd_k.py` | `BpOsdDecoder(osd_method="osd_cs")` on matrices of chosen `k`: crashes exactly when `k < osd_order` | numpy, ldpc |
| `repro_lsd_single_decode.py` | `BpLsdDecoder(lsd_cs, 10)` aborts on one decode of one surface-code syndrome | stim, numpy, ldpc |
| `fix-combination-sweep-bounds.patch` | bounds both pair loops by `min(osd_order, k)` | |
| `test_combination_sweep.cpp` | C++ driver for both decoders, prints every decoding | the ldpc headers |
| `verify_fix.py` | runs four builds of the driver and checks the fix | the four executables |
| `results-*.txt` | outputs obtained on Windows 10, CPython 3.14.7 | |

## Build the driver

Any C++20 compiler. Here, clang 21 from the `ziglang` Python package, which needs no system install:

```
python -m pip install ziglang
python -m ziglang c++ -std=c++20 -O1 -D_LIBCPP_HARDENING_MODE=_LIBCPP_HARDENING_MODE_EXTENSIVE -I <headers> test_combination_sweep.cpp -o sweep_<variant>_hardened.exe
python -m ziglang c++ -std=c++20 -O1 -I <headers> test_combination_sweep.cpp -o sweep_<variant>_plain.exe
python verify_fix.py <build directory>
```

`<headers>` is a copy of `src_cpp/` from the commit above (`original`), or the same copy with the patch applied (`patched`). With libc++ hardening, any out-of-bounds `std::vector::operator[]` traps at once, whatever the allocator.

## Results

- Bounds-checked builds: the original traps exactly when `k < 10`, on both decoders; the patched build never traps.
- Unchecked builds: wherever the original survives, both builds print byte-identical decodings (46 cells of `(k, order)`, 500 decodes each).
- The released 2.4.1 wheel: the crash boundary follows `k < osd_order` (`results-repro_osd_k.txt`).

Not done: building the Python extension with the patch and running `python_test/`.
