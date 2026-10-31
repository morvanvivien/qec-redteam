"""Effect of the summed edge priors on relay-bp's logical error rate, from scratch.

Both decoders are *informed*: they are compiled from the DEM of the true circuit
of each shot (the best a calibration can do). Same shots, same relay-bp
parameters as decoder-bench; only CheckMatrices differs:

    published   relay-bp 0.2.2 as installed (summed priors, np.matrix bias)
    crashfix    summed priors kept, only the bias turned into an ndarray: an edge
                whose summed prior reaches 1 is then treated as certain
    corrected   corrected.CombinedCheckMatrices (combined priors, ndarray bias)
    clamped     corrected.ClampedCheckMatrices (the same, priors clamped below 1/2)

A published decoder that raises is reported as such. PyMatching, informed the
same way, is the yardstick. `tuned-relay` and `tuned-pymatching` are compiled
from the nominal DEM instead (they do not know about the event): if informed
relay-bp does worse than tuned relay-bp, the true model hurts it.

    python research/relay-bp-priors/measure_effect.py --seeds 101 102 103
"""

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import corrected  # noqa: E402
from redteam import decoders  # noqa: E402
from redteam.decoders import build, dem_for  # noqa: E402
from redteam.mismatch import Setup, sample  # noqa: E402
from redteam.stats import mcnemar_p, paired_ratio, wilson  # noqa: E402

NAMES = ("published", "crashfix", "corrected", "clamped", "pymatching", "tuned-relay", "tuned-pymatching")
SCENARIOS = ("ancilla chaude x100", "donnée chaude x100", "fuite donnée centrale", "fuite ancilla 1r", "rafale 0.5")


def build_corrected(dem, variant: str = "corrected"):
    from relay_bp.stim.sinter import decoders as relay_decoders

    original = relay_decoders.CheckMatrices
    {"crashfix": corrected.patch_crash_fix_only, "clamped": corrected.patch_clamped}.get(variant, corrected.patch)()
    try:
        return decoders.build_relay(dem)
    finally:
        relay_decoders.CheckMatrices = original


def informed(name: str, circuits, cache: dict, dets, variant, nominal=None) -> np.ndarray | str:
    out = np.zeros((dets.shape[0], 1), dtype=bool)
    if name.startswith("tuned-"):
        if "tuned" not in cache:
            cache["tuned"] = build(name.removeprefix("tuned-").replace("relay", "relay-bp"), dem_for(nominal))
        return cache["tuned"].decode(dets)
    for index in np.unique(variant):
        if index not in cache:
            dem = dem_for(circuits[index])
            if name in ("corrected", "crashfix", "clamped"):
                cache[index] = build_corrected(dem, name)
            else:
                cache[index] = build("relay-bp" if name == "published" else name, dem)
        mask = variant == index
        try:
            out[mask] = cache[index].decode(dets[mask])
        except TypeError as error:
            return f"TypeError: {error}"
    return out


def run(setup: Setup, scenario_name: str, seed: int, shots: int) -> dict:
    scenario = next(s for s in setup.scenarios() if s.name == scenario_name)
    circuits = scenario.true_circuits(setup.nominal())
    dets, obs, variant = sample(circuits, shots, seed)
    result = {"scenario": scenario_name, "seed": seed, "shots": shots}
    wrong = {}
    for name in NAMES:
        predictions = informed(name, circuits, {}, dets, variant, setup.nominal())
        if isinstance(predictions, str):
            result[name] = predictions
            continue
        wrong[name] = np.any(predictions != obs, axis=1)
        result[name] = int(wrong[name].sum())
    reference = "published" if "published" in wrong else "crashfix"
    a, b = wrong[reference], wrong["corrected"]
    result["ratio"] = (reference, paired_ratio(int((a & b).sum()), int((a & ~b).sum()), int((~a & b).sum()), shots, seed=seed))
    result["mcnemar_p"] = mcnemar_p(int((a & ~b).sum()), int((~a & b).sum()))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--distance", type=int, default=5)
    parser.add_argument("--p", type=float, default=0.002)
    parser.add_argument("--shots", type=int, default=20_000)
    parser.add_argument("--seeds", type=int, nargs="+", default=[101, 102, 103])
    parser.add_argument("--scenarios", nargs="+", default=list(SCENARIOS))
    args = parser.parse_args()
    setup = Setup(args.distance, args.distance, args.p)
    for scenario in args.scenarios:
        totals = dict.fromkeys(NAMES, 0)
        for seed in args.seeds:
            r = run(setup, scenario, seed, args.shots)
            line = f"{scenario:22s} seed {seed}: " + ", ".join(f"{k} {r[k] if isinstance(r[k], int) else 'raises'}" for k in NAMES)
            reference, (ratio, low, high) = r["ratio"]
            line += f" | {reference}/corrected {ratio:.2f} [{low:.2f}, {high:.2f}], McNemar p = {r['mcnemar_p']:.1e}"
            print(line, flush=True)
            for k in totals:
                totals[k] = totals[k] + r[k] if isinstance(r[k], int) and isinstance(totals[k], int) else "raises"
        n = args.shots * len(args.seeds)
        summary = []
        for k, v in totals.items():
            if isinstance(v, int):
                low, high = wilson(v, n)
                summary.append(f"{k} {v}/{n} = {v / n:.3e} [{low:.3e}, {high:.3e}]")
            else:
                summary.append(f"{k} raises TypeError")
        print(f"{scenario:22s} pooled: " + "; ".join(summary), flush=True)


if __name__ == "__main__":
    main()
