Thanks for the careful write-up, it made this easy to chase. I think I found the cause, and a small fix.

### Root cause

The combination sweep in `DenseOsdDecoder::osd_setup()` (`src_cpp/osd_dense.hpp`, lines 84–95 at d3429964) builds candidates of length `k` but indexes them with `i, j < osd_order`:

```cpp
for (auto i = 0; i < this->osd_order; i++) {
    for (auto j = 0; j < this->osd_order; j++) {
        if (j <= i) continue;
        if (k > 0) {
            std::vector<uint8_t> osd_candidate;
            osd_candidate.resize(k, 0);
            osd_candidate[i] = 1;   // out of bounds when i >= k
            osd_candidate[j] = 1;   // out of bounds when j >= k
```

In LSD, `k` is the dimension of a single cluster (`not_pivot_cols.size()`), while `osd_order` is the global `lsd_order`. `apply_lsdw` grows a cluster towards `lsd_order` but can stop before reaching it (`cluster_growth_count <= initial_cluster_size`, among others), so `k < lsd_order` happens.

This accounts for everything in the issue:

- orders 0 and 1 are clean: with `osd_order <= 1` the pair loop produces nothing;
- `lsd_e` is clean: `decimal_to_binary_reverse(i, k)` stops at `k`;
- the platform dependence: the overflow is at most `osd_order - k` bytes past a `k`-byte allocation. On 64-bit glibc any request up to 24 bytes gets 24 usable bytes, so at `lsd_order <= 24` the writes stay inside the chunk and only `MALLOC_CHECK_` sees them. The Windows heap leaves less slack, so the same writes reach the next block: `0xC0000374`, and in a few runs `0xC0000005`.

### The same loop in `OsdDecoder`

`src_cpp/osd.hpp`, lines 90–99, has the same pair loop, without the `k > 0` guard. With a full check matrix `k = n - rank` is usually large, which is why `BpOsdDecoder(osd_method="osd_cs")` looked clean in your tests. With a small `k` it fails the same way. Released 2.4.1 wheel, Windows 10, CPython 3.14.7, one process per cell:

```
﻿ldpc 2.4.1, Python 3.14.7, win32

BpOsdDecoder, osd_method='osd_cs', osd_order=64
  k=1    CRASH (exit code 0xc0000374)
  k=2    CRASH (exit code 0xc0000374)
  k=4    CRASH (exit code 0xc0000374)
  k=8    CRASH (exit code 0xc0000374)
  k=16   CRASH (exit code 0xc0000005)
  k=24   CRASH (exit code 0xc0000374)
  k=32   CRASH (exit code 0xc0000374)
  k=48   CRASH (exit code 0xc0000374)
  k=60   clean
  k=63   clean
  k=64   clean
  k=65   clean
  k=80   clean
  k=120  clean

BpOsdDecoder, osd_method='osd_cs', osd_order=16
  k=1    CRASH (exit code 0xc0000374)
  k=2    CRASH (exit code 0xc0000374)
  k=4    CRASH (exit code 0xc0000374)
  k=8    CRASH (exit code 0xc0000005)
  k=16   clean
  k=24   clean
  k=32   clean
  k=48   clean
  k=60   clean
  k=63   clean
  k=64   clean
  k=65   clean
  k=80   clean
  k=120  clean

Controls at k=1
  osd_e  order 10  clean
  osd_cs order 1   clean
  osd_cs order 0   clean
```

At order 64, `k = 60` and `k = 63` overflow by only 1 to 4 bytes, which stays in allocator slack.

### One decode is enough

Rotated surface code, d=5, 5 rounds, memory Z, stim's built-in circuit noise at p=0.002, check matrices from `ldpc.ckt_noise.dem_matrices`. In a fresh process, a fresh `BpLsdDecoder(lsd_method="lsd_cs", lsd_order=10)` aborts with `0xC0000374` on its first decode of shot 29 (sampler seed 7). The same syndrome is clean with `lsd_cs` order 1, `lsd_e` order 10 and `lsd_0`.

### Fix

Bound both pair loops by `min(osd_order, k)`:

```diff
--- a/src_cpp/osd_dense.hpp
+++ b/src_cpp/osd_dense.hpp
@@ -81,16 +81,15 @@
                     this->osd_candidate_strings.push_back(osd_candidate);
                 }
 
-                for (auto i = 0; i < this->osd_order; i++) {
-                    for (auto j = 0; j < this->osd_order; j++) {
-                        if (j <= i) continue;
-                        if (k > 0) {
-                            std::vector<uint8_t> osd_candidate;
-                            osd_candidate.resize(k, 0);
-                            osd_candidate[i] = 1;
-                            osd_candidate[j] = 1;
-                            this->osd_candidate_strings.push_back(osd_candidate);
-                        }
+                // Pairs are drawn from the first osd_order non-pivot columns, and there are only k of them.
+                const int pair_limit = std::min(this->osd_order, this->k);
+                for (auto i = 0; i < pair_limit; i++) {
+                    for (auto j = i + 1; j < pair_limit; j++) {
+                        std::vector<uint8_t> osd_candidate;
+                        osd_candidate.resize(k, 0);
+                        osd_candidate[i] = 1;
+                        osd_candidate[j] = 1;
+                        this->osd_candidate_strings.push_back(osd_candidate);
                     }
                 }
             }
--- a/src_cpp/osd.hpp
+++ b/src_cpp/osd.hpp
@@ -1,6 +1,7 @@
 #ifndef BPOSD_H
 #define BPOSD_H
 
+#include <algorithm>
 #include <vector>
 #include <memory>
 #include <iterator>
@@ -87,13 +88,14 @@
                     this->osd_candidate_strings.push_back(osd_candidate);
                 }
 
-                for(int i = 0; i<this->osd_order;i++){
-                    for(int j = 0; j<this->osd_order; j++){
-                        if(j<=i) continue;
+                // Pairs are drawn from the first osd_order non-pivot columns, and there are only k of them.
+                const int pair_limit = std::min(this->osd_order, this->k);
+                for(int i = 0; i<pair_limit;i++){
+                    for(int j = i+1; j<pair_limit; j++){
                         std::vector<uint8_t> osd_candidate;
                         osd_candidate.resize(k,0);
                         osd_candidate[i]=1;
-                        osd_candidate[j]=1; 
+                        osd_candidate[j]=1;
                         this->osd_candidate_strings.push_back(osd_candidate);
                     }
                 }
```

For `osd_order <= k` this generates exactly the same candidates in the same order. For `osd_order > k` it only drops candidates whose in-range part is either a single-bit vector already produced by the first loop, or the zero vector. A candidate replaces the current solution only if its weight is strictly lower, so those candidates never change the result.

### Verification

I compiled the original and patched `osd_dense.hpp` and `osd.hpp` into a small C++ driver (below) with clang 21 and libc++ hardening, which traps on any out-of-bounds `std::vector::operator[]` whatever the allocator:

```
﻿1. Bounds-checked builds, order 10, 50 decodes
   path      k   original              patched
   dense     1   TRAP 0xc000001d       ok        
   dense     2   TRAP 0xc000001d       ok        
   dense     5   TRAP 0xc000001d       ok        
   dense     9   TRAP 0xc000001d       ok        
   dense    10   ok                    ok        
   dense    11   ok                    ok        
   dense    20   ok                    ok        
   sparse    1   TRAP 0xc000001d       ok        
   sparse    2   TRAP 0xc000001d       ok        
   sparse    5   TRAP 0xc000001d       ok        
   sparse    9   TRAP 0xc000001d       ok        
   sparse   10   ok                    ok        
   sparse   11   ok                    ok        
   sparse   20   ok                    ok        

2. Unchecked builds, identical output wherever the original survives, 500 decodes
   46 cells compared, 46 identical, 10 skipped because the original crashed

RESULT: all checks passed
```

- original: traps exactly when `k < osd_order`, for both `DenseOsdDecoder` and `OsdDecoder`;
- patched: never traps;
- without hardening, wherever the original survives, the two builds print byte-identical decodings.

So besides removing the memory corruption, the fix should not change any decoding result. It also suggests that `lsd_cs` results computed on glibc at `lsd_order <= 24`, where the writes stay inside the vector's own allocation, are not affected. For example, decoder-bench's `bplsd` wrapper uses `osd_method="osd_cs", osd_order=10`. At higher orders, or with other allocators, the overflow can reach neighbouring blocks and nothing general can be said.

Not done: building the Python extension with the patch and running `python_test/`. I only have the headers compiled through the driver. Happy to open a PR with the patch and a regression test in `python_test/test_bplsd.py` if that is useful.

<details>
<summary><code>repro_osd_k.py</code> (numpy + ldpc)</summary>

```python
"""Out-of-bounds write in the OSD combination sweep: crash boundary follows k < osd_order.

Needs only numpy and ldpc. Each cell runs in its own process, because a heap
corruption kills the interpreter.

    python repro_osd_k.py

k = n - rank(H) is the number of non-pivot columns. The combination sweep builds
candidate vectors of length k and sets candidate[i] and candidate[j] for every
i < j < osd_order, so any k < osd_order writes past the end of the vector.
"""

import subprocess
import sys

CHILD = r"""
import sys
import numpy as np
from ldpc import BpOsdDecoder
from ldpc.mod2 import rank

k, order, method = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
checks = 40
n = checks + k
rng = np.random.default_rng(1000 + k)
while True:
    h = (rng.random((checks, n)) < 0.15).astype(np.uint8)
    if rank(h) == checks:
        break
assert n - rank(h) == k

for _ in range(20):
    decoder = BpOsdDecoder(h, error_rate=0.05, max_iter=2, bp_method="minimum_sum",
                           osd_method=method, osd_order=order)
    for _ in range(50):
        error = (rng.random(n) < 0.05).astype(np.uint8)
        decoder.decode((h @ error % 2).astype(np.uint8))
    del decoder
"""


def cell(k: int, order: int, method: str = "osd_cs") -> str:
    code = subprocess.run([sys.executable, "-c", CHILD, str(k), str(order), method], capture_output=True).returncode
    return "clean" if code == 0 else f"CRASH (exit code {code & 0xFFFFFFFF:#x})"


def main() -> None:
    import ldpc

    print(f"ldpc {ldpc.__version__}, Python {sys.version.split()[0]}, {sys.platform}")
    for order in (64, 16):
        print(f"\nBpOsdDecoder, osd_method='osd_cs', osd_order={order}")
        for k in (1, 2, 4, 8, 16, 24, 32, 48, 60, 63, 64, 65, 80, 120):
            print(f"  k={k:<4} {cell(k, order)}")
    print("\nControls at k=1")
    print(f"  osd_e  order 10  {cell(1, 10, 'osd_e')}")
    print(f"  osd_cs order 1   {cell(1, 1)}")
    print(f"  osd_cs order 0   {cell(1, 0)}")


if __name__ == "__main__":
    main()
```

</details>

<details>
<summary><code>repro_lsd_single_decode.py</code> (stim + numpy + ldpc)</summary>

```python
"""BpLsdDecoder(lsd_method='lsd_cs', lsd_order=10) aborts on a single decode.

Needs only stim, numpy and ldpc. Rotated surface code, d=5, 5 rounds, memory Z,
stim's built-in circuit noise at p=0.002. Each attempt runs in its own process:
a fresh interpreter, a fresh decoder, one decode.

    python repro_lsd_single_decode.py              # scan shots, report the first that aborts
    python repro_lsd_single_decode.py --shot 17    # decode only that shot
"""

import argparse
import subprocess
import sys

CHILD = r"""
import sys
import numpy as np
import stim
from ldpc.bplsd_decoder import BpLsdDecoder
from ldpc.ckt_noise.dem_matrices import detector_error_model_to_check_matrices

shot, order, method = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
p = 0.002
circuit = stim.Circuit.generated(
    "surface_code:rotated_memory_z", distance=5, rounds=5,
    after_clifford_depolarization=p, before_round_data_depolarization=p,
    before_measure_flip_probability=p, after_reset_flip_probability=p,
)
dem = circuit.detector_error_model(decompose_errors=True)
matrices = detector_error_model_to_check_matrices(dem)
detectors = circuit.compile_detector_sampler(seed=7).sample(shots=shot + 1)

decoder = BpLsdDecoder(matrices.check_matrix, error_channel=list(matrices.priors),
                       max_iter=20, bp_method="minimum_sum",
                       lsd_method=method, lsd_order=order)
decoder.decode(detectors[shot].astype(np.uint8))
del decoder
"""


def attempt(shot: int, order: int = 10, method: str = "lsd_cs") -> int:
    return subprocess.run([sys.executable, "-c", CHILD, str(shot), str(order), method], capture_output=True).returncode


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shot", type=int)
    parser.add_argument("--max-shots", type=int, default=200)
    args = parser.parse_args()

    import ldpc

    print(f"ldpc {ldpc.__version__}, Python {sys.version.split()[0]}, {sys.platform}")
    shots = [args.shot] if args.shot is not None else range(args.max_shots)
    for shot in shots:
        code = attempt(shot)
        if code != 0:
            print(f"shot {shot}: one decode with lsd_cs order 10 exits with {code & 0xFFFFFFFF:#x}")
            for method, order in (("lsd_cs", 1), ("lsd_e", 10), ("lsd_0", 0)):
                other = attempt(shot, order, method)
                print(f"  same shot, {method} order {order}: {'clean' if other == 0 else hex(other & 0xFFFFFFFF)}")
            return
    print("no single decode aborted in the scanned shots")


if __name__ == "__main__":
    main()
```

</details>

<details>
<summary><code>test_combination_sweep.cpp</code> (C++ driver used for the before/after check)</summary>

```cpp
// Exercises the OSD combination sweep with k non-pivot columns and a given order.
//
//   test_combination_sweep <dense|sparse> K ORDER DECODES
//
// Prints one line per decode (the decoded bit string) so that two builds can be
// compared byte for byte. Built against libc++ with hardening, any out-of-bounds
// std::vector::operator[] traps immediately, whatever the allocator.

#include <cstdio>
#include <cstdlib>
#include <random>
#include <string>
#include <vector>

#include "osd_dense.hpp"

namespace {

// m x (m + k) matrix of rank m whose k non-pivot columns all come before the
// rank is full: e_0 .. e_{m-2}, then k random combinations of those rows, then
// e_{m-1}. PluDecomposition::rref stops at full rank, so the order matters.
std::vector<std::vector<int>> make_columns(int m, int k, std::mt19937 &rng) {
    std::vector<std::vector<int>> columns;
    for (int r = 0; r < m - 1; r++) columns.push_back({r});
    std::bernoulli_distribution coin(0.3);
    for (int c = 0; c < k; c++) {
        std::vector<int> rows;
        for (int r = 0; r < m - 1; r++) if (coin(rng)) rows.push_back(r);
        if (rows.empty()) rows.push_back(c % (m - 1));
        columns.push_back(rows);
    }
    columns.push_back({m - 1});
    return columns;
}

std::vector<uint8_t> random_syndrome(const std::vector<std::vector<int>> &columns, int m, std::mt19937 &rng) {
    std::vector<uint8_t> syndrome(m, 0);
    std::bernoulli_distribution flip(0.08);
    for (const auto &column: columns)
        if (flip(rng))
            for (int r: column) syndrome[r] ^= 1;
    return syndrome;
}

void print_bits(const std::vector<uint8_t> &bits) {
    std::string line;
    for (auto b: bits) line.push_back(b ? '1' : '0');
    std::puts(line.c_str());
}

int run_dense(int k, int order, int decodes) {
    const int m = 24, n = m + k;
    std::mt19937 rng(1234 + k);
    auto columns = make_columns(m, k, rng);
    auto plu = ldpc::gf2dense::PluDecomposition(m, n, columns);
    plu.rref();
    if (static_cast<int>(plu.not_pivot_cols.size()) != k) {
        std::fprintf(stderr, "unexpected dimension %zu\n", plu.not_pivot_cols.size());
        return 2;
    }
    std::vector<double> weights(n, 1.0);
    auto decoder = ldpc::osd::DenseOsdDecoder(columns, plu, ldpc::osd::COMBINATION_SWEEP, order, n, m, weights);
    for (int i = 0; i < decodes; i++) {
        auto syndrome = random_syndrome(columns, m, rng);
        print_bits(decoder.osd_decode(syndrome));
    }
    return 0;
}

int run_sparse(int k, int order, int decodes) {
    const int m = 24, n = m + k;
    std::mt19937 rng(4321 + k);
    auto columns = make_columns(m, k, rng);
    ldpc::bp::BpSparse pcm(m, n);
    for (int c = 0; c < n; c++)
        for (int r: columns[c]) pcm.insert_entry(r, c);
    std::vector<double> channel(n, 0.05);
    auto decoder = ldpc::osd::OsdDecoder(pcm, ldpc::osd::COMBINATION_SWEEP, order, channel);
    std::uniform_real_distribution<double> llr(-2.0, 4.0);
    for (int i = 0; i < decodes; i++) {
        auto syndrome = random_syndrome(columns, m, rng);
        std::vector<double> log_prob_ratios(n);
        for (auto &x: log_prob_ratios) x = llr(rng);
        print_bits(decoder.decode(syndrome, log_prob_ratios));
    }
    return 0;
}

}  // namespace

int main(int argc, char **argv) {
    if (argc != 5) {
        std::fprintf(stderr, "usage: %s <dense|sparse> K ORDER DECODES\n", argv[0]);
        return 2;
    }
    const std::string which = argv[1];
    const int k = std::atoi(argv[2]), order = std::atoi(argv[3]), decodes = std::atoi(argv[4]);
    return which == "dense" ? run_dense(k, order, decodes) : run_sparse(k, order, decodes);
}
```

</details>
