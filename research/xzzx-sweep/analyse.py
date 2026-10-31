"""Rassemble les exécutions de sweep.py : taux par décodeur et par code, rapports appariés à PyMatching.

    python research/xzzx-sweep/analyse.py --seeds 21 22 23
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from redteam.stats import mcnemar_p, paired_ratio, wilson  # noqa: E402

RUNS = Path(__file__).resolve().parent / "runs"
ORDER = ["pymatching", "fusion-blossom", "beliefmatching", "mwpf", "tesseract", "bposd", "bplsd", "stimbposd", "relay-bp"]


def load(code: str, decoder: str, seeds: list[int], distance: int, eta: float):
    wrong, shots = [], 0
    for seed in seeds:
        path = RUNS / f"{code}_{decoder}_d{distance}_eta{eta:g}_s{seed}.json"
        if not path.exists():
            return None
        run = json.loads(path.read_text())
        vec = np.zeros(run["shots"], dtype=bool)
        vec[run["wrong"]] = True
        wrong.append(vec)
        shots += run["shots"]
    return np.concatenate(wrong), shots


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, nargs="+", default=[21, 22, 23])
    parser.add_argument("--distance", type=int, default=5)
    parser.add_argument("--eta", type=float, default=1000.0)
    args = parser.parse_args()
    print(f"d = {args.distance}, eta = {args.eta:g}, graines {args.seeds}")
    print("| Décodeur | code ordinaire | XZZX | gain XZZX | XZZX / PyMatching [IC 95 %] | McNemar p |")
    print("|---|---|---|---|---|---|")
    ref = load("xzzx", "pymatching", args.seeds, args.distance, args.eta)
    for decoder in ORDER:
        css, xz = load("css", decoder, args.seeds, args.distance, args.eta), load("xzzx", decoder, args.seeds, args.distance, args.eta)
        if css is None or xz is None or ref is None:
            print(f"| {decoder} | manquant | | | | |")
            continue
        (wc, nc), (wx, nx) = css, xz
        rate_c, rate_x = wc.sum() / nc, wx.sum() / nx
        n = min(nx, len(ref[0]))
        a, b = wx[:n], ref[0][:n]
        both, only_a, only_b = int((a & b).sum()), int((a & ~b).sum()), int((~a & b).sum())
        ratio, low, high = paired_ratio(both, only_a, only_b, n, seed=1)
        lo_c, hi_c = wilson(int(wc.sum()), nc)
        lo_x, hi_x = wilson(int(wx.sum()), nx)
        print(f"| {decoder} | {rate_c:.3%} [{lo_c:.3%} ; {hi_c:.3%}] | {rate_x:.3%} [{lo_x:.3%} ; {hi_x:.3%}] | ×{rate_c / max(rate_x, 1e-12):.2f} | "
              f"{ratio:.2f} [{low:.2f} ; {high:.2f}] | {mcnemar_p(only_a, only_b):.1e} |")


if __name__ == "__main__":
    main()
