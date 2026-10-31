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
