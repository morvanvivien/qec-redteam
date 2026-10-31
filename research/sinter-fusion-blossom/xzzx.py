"""Constat 004 on the XZZX surface code, the code tailored to Z-biased noise.

The XZZX code is the rotated surface code with a Hadamard on one data qubit of
each diagonal pair, so that every stabilizer reads X Z Z X. Rather than
rewriting the gates, the noise is conjugated: on the Hadamard-conjugated data
qubits the X and Z parts of every Pauli channel are swapped, which is exactly
what the same physical noise does once seen through the Hadamards. Reset and
measurement flips (X_ERROR, Z_ERROR) are left alone: they flip outcomes in
either frame.

Same three decoders as parallel_edges.py, same shots: fusion-blossom as sinter
builds it, fusion-blossom with parallel edges merged, PyMatching.

    python research/sinter-fusion-blossom/xzzx.py --distance 5 --eta 1000 --seeds 11 12 13 --shots 26000
"""

import argparse
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from parallel_edges import components, decode, merged_solver  # noqa: E402
from sinter._decoding._decoding_fusion_blossom import detector_error_model_to_fusion_blossom_solver_and_fault_masks  # noqa: E402

from redteam.decoders import build, dem_for  # noqa: E402
from redteam.mismatch import Setup, sample  # noqa: E402
from redteam.perturb import bias  # noqa: E402
from redteam.stats import mcnemar_p, wilson  # noqa: E402
from redteam.xzzx import conjugated_data, xzzx  # noqa: E402

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--distance", type=int, default=5)
    parser.add_argument("--p", type=float, default=0.002)
    parser.add_argument("--eta", type=float, default=1000.0)
    parser.add_argument("--basis", choices=("x", "z"), default="x")
    parser.add_argument("--css", action="store_true", help="plain CSS surface code under the same noise, for comparison")
    parser.add_argument("--shots", type=int, default=26000)
    parser.add_argument("--seeds", type=int, nargs="+", default=[11, 12, 13])
    args = parser.parse_args()
    nominal = Setup(args.distance, args.distance, args.p, args.basis, True).nominal()
    biased = bias(nominal, args.eta)
    circuit = biased if args.css else xzzx(biased, conjugated_data(nominal))
    dem = dem_for(circuit)
    comps = components(dem)
    pairs = collections.Counter((a, b) for a, b, _, _ in comps)
    print(f"{'CSS' if args.css else 'XZZX'} d={args.distance} p={args.p} eta={args.eta:g} {args.basis.upper()} memory: "
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
        print(f"  seed {seed}: sinter fusion-blossom {a.sum()}, merged {b.sum()}, pymatching {c.sum()} / {args.shots}; "
              f"sinter-only {int((a & ~b).sum())}, merged-only {int((b & ~a).sum())}", flush=True)
        totals.update({"sinter": int(a.sum()), "merged": int(b.sum()), "pymatching": int(c.sum()),
                       "a_only": int((a & ~b).sum()), "b_only": int((b & ~a).sum()), "shots": args.shots})
    n = totals["shots"]
    for key in ("sinter", "merged", "pymatching"):
        low, high = wilson(totals[key], n)
        print(f"  pooled {key:10s} {totals[key]}/{n} = {totals[key] / n:.4e} [{low:.4e}, {high:.4e}]")
    print(f"  pooled sinter / merged = {totals['sinter'] / max(totals['merged'], 1):.3f}; McNemar p = {mcnemar_p(totals['a_only'], totals['b_only']):.1e}")


if __name__ == "__main__":
    main()
