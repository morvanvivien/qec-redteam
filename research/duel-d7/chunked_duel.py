"""Paired duel that survives restarts: each batch of shots is written as soon as it is decoded.

Same shots as redteam.duel for the same seed (batch k uses seed * 100003 + k),
but batches of --batch shots are appended to a JSON-lines file and skipped on
the next run, so a killed process loses at most one batch.

    python research/duel-d7/chunked_duel.py --distance 7 --p 0.003 --scenario "diaphonie ZZ 3p" --shots 3000 --seed 42
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from redteam.decoders import build, dem_for  # noqa: E402
from redteam.mismatch import Setup, sample  # noqa: E402
from redteam.stats import mcnemar_p, paired_ratio, wilson  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--distance", type=int, default=7)
    parser.add_argument("--p", type=float, default=0.003)
    parser.add_argument("--scenario", default="diaphonie ZZ 3p")
    parser.add_argument("--decoders", nargs=2, default=["pymatching", "tesseract"])
    parser.add_argument("--shots", type=int, default=3000)
    parser.add_argument("--batch", type=int, default=250)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-new", type=int, default=None, help="stop after this many new batches")
    parser.add_argument("--only", type=int, nargs="*", default=None, help="decode only these batch indices (to run several processes in parallel)")
    args = parser.parse_args()
    setup = Setup(args.distance, args.distance, args.p)
    name = f"d{args.distance}_p{args.p:g}_{args.scenario.replace(' ', '_')}_s{args.seed}_b{args.batch}"
    store = Path(__file__).resolve().parent / f"batches-{name}.jsonl"
    done = {json.loads(line)["batch"] for line in store.read_text().splitlines()} if store.exists() else set()
    nominal = setup.nominal()
    circuits = next(s for s in setup.scenarios() if s.name == args.scenario).true_circuits(nominal)
    ref, other = args.decoders
    compiled = {n: build(n, dem_for(nominal)) for n in args.decoders}
    new = 0
    for k in range(args.shots // args.batch):
        if k in done or (args.only is not None and k not in args.only):
            continue
        if args.max_new is not None and new >= args.max_new:
            return
        new += 1
        dets, obs, _ = sample(circuits, args.batch, args.seed * 100_003 + k)
        wrong = {n: np.any(compiled[n].decode(dets) != obs, axis=1) for n in args.decoders}
        a, b = wrong[other], wrong[ref]
        with store.open("a") as f:
            f.write(json.dumps({"batch": k, "shots": args.batch, other: int(a.sum()), ref: int(b.sum()), "both": int((a & b).sum())}) + "\n")
        print(f"batch {k} written", flush=True)
    rows = [json.loads(line) for line in store.read_text().splitlines()]
    n = sum(r["shots"] for r in rows)
    ea, eb, both = (sum(r[key] for r in rows) for key in (other, ref, "both"))
    ratio, low, high = paired_ratio(both, ea - both, eb - both, n, seed=args.seed)
    print(f"{args.scenario} d={args.distance} p={args.p:g} seed {args.seed}: {n} shots, {len(rows)} batches")
    for label, e in ((ref, eb), (other, ea)):
        lo, hi = wilson(e, n)
        print(f"  {label:12s} {e} errors, {e / n:.3e} [{lo:.3e}, {hi:.3e}]")
    print(f"  {other}/{ref} = {ratio:.2f} [{low:.2f}, {high:.2f}], McNemar p = {mcnemar_p(ea - both, eb - both):.1e}")


if __name__ == "__main__":
    main()
