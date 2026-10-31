"""sinter's fusion_blossom decoder keeps parallel edges instead of merging them.

`detector_error_model_to_fusion_blossom_solver_and_fault_masks` (stim's
glue/sample/src/sinter/_decoding/_decoding_fusion_blossom.py, unchanged on
main at 131793e) appends one edge per DEM error component. Components that
land on the same pair of detectors are never combined, so the matching sees
the single most likely of them instead of their combined probability,
(1 - prod(1 - 2 p_i)) / 2. PyMatching merges them.

This script decodes the same shots with fusion-blossom as sinter builds it,
fusion-blossom with parallel edges merged (same rescaling as sinter), and
PyMatching, all compiled from the true DEM. Default case: rotated surface code
d = 5, X memory, SI1000 at p = 0.002 whose depolarization is replaced by a
Z-biased Pauli channel (eta = 1000, same total probability).

    python research/sinter-fusion-blossom/parallel_edges.py --seeds 11 12 13 --shots 26000
"""

import argparse
import collections
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import fusion_blossom  # noqa: E402
from sinter._decoding._decoding_fusion_blossom import (  # noqa: E402
    detector_error_model_to_fusion_blossom_solver_and_fault_masks,
    iter_flatten_model,
)

from redteam.decoders import build, dem_for  # noqa: E402
from redteam.mismatch import Setup, sample  # noqa: E402
from redteam.stats import mcnemar_p, wilson  # noqa: E402


def components(dem):
    out = []

    def handle(p, dets, frames):
        if p == 0 or not dets:
            return
        if len(dets) == 1:
            dets = [dets[0], dem.num_detectors]
        out.append((min(dets), max(dets), p, sum(1 << k for k in frames)))

    iter_flatten_model(dem, handle_error=handle, handle_detector_coords=lambda d, c: None)
    return out


def merged_solver(dem):
    """Same construction as sinter, parallel components combined first (per observable mask, most likely mask kept)."""
    by_mask = collections.defaultdict(float)
    for a, b, p, mask in components(dem):
        q = by_mask[(a, b, mask)]
        by_mask[(a, b, mask)] = q * (1 - p) + p * (1 - q)
    best = {}
    for (a, b, mask), q in by_mask.items():
        if (a, b) not in best or q > best[(a, b)][0]:
            best[(a, b)] = (q, mask)
    edges = [(a, b, math.log((1 - min(q, 0.5)) / min(q, 0.5)), mask) for (a, b), (q, mask) in best.items()]
    top = max(1e-4, max(w for _, _, w, _ in edges))
    init = fusion_blossom.SolverInitializer(dem.num_detectors + 1, [(a, b, round(w * 2**10 / top) * 2) for a, b, w, _ in edges], [dem.num_detectors])
    return fusion_blossom.SolverSerial(init), np.array([m for *_, m in edges], dtype=np.uint64)


def decode(solver, masks, dets):
    out = np.zeros(len(dets), dtype=np.uint64)
    for i, d in enumerate(dets):
        solver.solve(fusion_blossom.SyndromePattern(np.flatnonzero(d)))
        chosen = solver.subgraph()
        out[i] = np.bitwise_xor.reduce(masks[chosen]) if len(chosen) else 0
        solver.clear()
    return (out & 1).astype(bool)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--distance", type=int, default=5)
    parser.add_argument("--p", type=float, default=0.002)
    parser.add_argument("--scenario", default="biais Z eta=1000")
    parser.add_argument("--nominal", action="store_true", help="plain SI1000 in Z memory instead of the biased X memory")
    parser.add_argument("--basis", choices=("x", "z"), default="x", help="memory basis of the biased case (x by default; z for the mirror)")
    parser.add_argument("--shots", type=int, default=26000)
    parser.add_argument("--seeds", type=int, nargs="+", default=[11, 12, 13])
    args = parser.parse_args()
    setup = Setup(args.distance, args.distance, args.p, "z", False) if args.nominal else Setup(args.distance, args.distance, args.p, args.basis, True)
    nominal = setup.nominal()
    circuit = nominal if args.nominal else next(s for s in setup.scenarios() if s.name == args.scenario).true_circuits(nominal)[0]
    dem = dem_for(circuit)
    comps = components(dem)
    pairs = collections.Counter((a, b) for a, b, _, _ in comps)
    print(f"d={args.distance} p={args.p} {'SI1000 Z memory' if args.nominal else args.scenario + ', ' + args.basis.upper() + ' memory'}: "
          f"{len(comps)} edges from sinter, {len(pairs)} distinct detector pairs, {sum(c > 1 for c in pairs.values())} pairs with parallel edges", flush=True)
    sinter_solver, sinter_masks = detector_error_model_to_fusion_blossom_solver_and_fault_masks(dem)
    merged, merged_masks = merged_solver(dem)
    matching = build("pymatching", dem)
    totals = collections.Counter()
    for seed in args.seeds:
        dets, obs, _ = sample([circuit], args.shots, seed)
        obs = obs[:, 0]
        a = decode(sinter_solver, sinter_masks, dets) != obs
        b = decode(merged, merged_masks, dets) != obs
        c = matching.decode(dets)[:, 0] != obs
        line = f"  seed {seed}: sinter fusion-blossom {a.sum()}, merged {b.sum()}, pymatching {c.sum()} / {args.shots}; sinter-only {int((a & ~b).sum())}, merged-only {int((b & ~a).sum())}"
        print(line, flush=True)
        totals.update({"sinter": int(a.sum()), "merged": int(b.sum()), "pymatching": int(c.sum()), "a_only": int((a & ~b).sum()), "b_only": int((b & ~a).sum()), "shots": args.shots})
    n = totals["shots"]
    for key in ("sinter", "merged", "pymatching"):
        low, high = wilson(totals[key], n)
        print(f"  pooled {key:10s} {totals[key]}/{n} = {totals[key] / n:.4e} [{low:.4e}, {high:.4e}]")
    print(f"  pooled sinter / merged = {totals['sinter'] / max(totals['merged'], 1):.3f}; McNemar p = {mcnemar_p(totals['a_only'], totals['b_only']):.1e}")


if __name__ == "__main__":
    main()
