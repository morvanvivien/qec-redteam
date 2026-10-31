"""Before/after check of the combination-sweep fix with the four builds of test_combination_sweep.cpp.

1. Bounds-checked builds (libc++ hardening): the original must trap exactly when
   k < order; the patched build must never trap.
2. Unchecked builds: wherever the original survives, both builds must print
   byte-identical decodings.

    python verify_fix.py <data>\build
"""

import subprocess
import sys
from pathlib import Path

build = Path(sys.argv[1])
EXE = {(variant, mode): build / f"sweep_{variant}_{mode}.exe" for variant in ("original", "patched") for mode in ("hardened", "plain")}


def run(variant, mode, which, k, order, decodes):
    result = subprocess.run([str(EXE[variant, mode]), which, str(k), str(order), str(decodes)], capture_output=True)
    return result.returncode & 0xFFFFFFFF, result.stdout


failures = 0

print("1. Bounds-checked builds, order 10, 50 decodes")
print(f"   {'path':<7}{'k':>4}   original              patched")
for which in ("dense", "sparse"):
    for k in (1, 2, 5, 9, 10, 11, 20):
        original, _ = run("original", "hardened", which, k, 10, 50)
        patched, _ = run("patched", "hardened", which, k, 10, 50)
        expected_trap = k < 10
        ok = (original != 0) == expected_trap and patched == 0
        failures += not ok
        label = lambda code: "ok" if code == 0 else f"TRAP {code:#x}"
        print(f"   {which:<7}{k:>4}   {label(original):<22}{label(patched):<10}{'' if ok else '  <-- unexpected'}")

print("\n2. Unchecked builds, identical output wherever the original survives, 500 decodes")
compared = identical = skipped = 0
for which in ("dense", "sparse"):
    for k in (1, 2, 3, 5, 8, 10, 15):
        for order in (2, 3, 5, 10):
            original_code, original_out = run("original", "plain", which, k, order, 500)
            patched_code, patched_out = run("patched", "plain", which, k, order, 500)
            if patched_code != 0:
                failures += 1
                print(f"   {which} k={k} order={order}: patched build exited {patched_code:#x}  <-- unexpected")
                continue
            if original_code != 0:
                skipped += 1
                continue
            compared += 1
            if original_out == patched_out:
                identical += 1
            else:
                failures += 1
                print(f"   {which} k={k} order={order}: outputs differ  <-- unexpected")
print(f"   {compared} cells compared, {identical} identical, {skipped} skipped because the original crashed")

print("\nRESULT:", "all checks passed" if failures == 0 else f"{failures} unexpected result(s)")
sys.exit(1 if failures else 0)
