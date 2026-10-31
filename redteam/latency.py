"""Latence de décodage tir par tir sous bruit perturbé : distribution complète, pas la moyenne.

Un décodeur temps réel doit tenir chaque round, pas seulement en moyenne :
une queue lourde (p99, max) fait déborder la file des syndromes. Chaque tir
est décodé seul, chronométré en nanosecondes, avec le décodeur réglé sur le
bruit nominal. Le temps inclut l'appel Python de l'adaptateur, mesuré à part
sur un syndrome nul (plancher).

    python -m redteam.latency --distance 5 --p 0.002 --decoders pymatching bposd --shots 5000
"""

import argparse
import csv
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from redteam.decoders import REGISTRY, build, dem_for
from redteam.mismatch import Setup, sample

QUANTILES = (0.5, 0.9, 0.99, 0.999)


@dataclass(frozen=True)
class Latency:
    scenario: str
    decoder: str
    distance: int
    rounds: int
    p: float
    shots: int
    floor_us: float
    mean_us: float
    p50_us: float
    p90_us: float
    p99_us: float
    p999_us: float
    max_us: float
    max_weight: int
    mean_weight: float

    def per_round(self, value_us: float) -> float:
        return value_us / self.rounds


def time_shots(decoder, dets: np.ndarray) -> np.ndarray:
    """Durée de décodage de chaque tir, en microsecondes."""
    out = np.empty(dets.shape[0])
    for i in range(dets.shape[0]):
        one = dets[i:i + 1]
        start = time.perf_counter_ns()
        decoder.decode(one)
        out[i] = (time.perf_counter_ns() - start) / 1000.0
    return out


def summarize(scenario: str, decoder: str, setup: Setup, durations: np.ndarray, weights: np.ndarray, floor_us: float) -> Latency:
    q = np.quantile(durations, QUANTILES)
    return Latency(
        scenario, decoder, setup.distance, setup.rounds, setup.p, len(durations), floor_us,
        float(durations.mean()), *map(float, q), float(durations.max()), int(weights.max()), float(weights.mean()),
    )


def measure(setup: Setup, scenario_name: str, decoder: str, shots: int, seed: int, warmup: int = 50) -> tuple[Latency, np.ndarray, np.ndarray]:
    """Rend le résumé, les durées et les poids de syndrome de chaque tir."""
    scenario = next(s for s in setup.scenarios() if s.name == scenario_name)
    compiled = build(decoder, dem_for(setup.nominal()))
    dets, _, _ = sample(scenario.true_circuits(setup.nominal()), shots + warmup, seed)
    time_shots(compiled, dets[:warmup])
    zero = np.zeros((warmup, dets.shape[1]), dtype=bool)
    floor_us = float(np.median(time_shots(compiled, zero)))
    durations = time_shots(compiled, dets[warmup:])
    weights = dets[warmup:].sum(axis=1)
    return summarize(scenario_name, decoder, setup, durations, weights, floor_us), durations, weights


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Distribution de la latence de décodage sous bruit perturbé.")
    parser.add_argument("--out", type=Path, default=Path("out/latency"))
    parser.add_argument("--distance", type=int, default=5)
    parser.add_argument("--p", type=float, default=0.002)
    parser.add_argument("--decoders", nargs="+", default=["pymatching"], choices=sorted(REGISTRY))
    parser.add_argument("--scenarios", nargs="+", default=["nominal", "tout x3", "ancilla chaude x100", "fuite ancilla 1r", "rafale 0.5", "diaphonie XX 1p"])
    parser.add_argument("--shots", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20260929)
    args = parser.parse_args(argv)

    setup = Setup(args.distance, args.distance, args.p)
    args.out.mkdir(parents=True, exist_ok=True)
    rows = []
    for decoder in args.decoders:
        for scenario in args.scenarios:
            summary, durations, weights = measure(setup, scenario, decoder, args.shots, args.seed)
            rows.append(summary)
            print(f"{decoder:15s} {scenario:22s} p50 {summary.p50_us:9.1f} µs  p99 {summary.p99_us:9.1f}  p99,9 {summary.p999_us:9.1f}  max {summary.max_us:10.1f}  (plancher {summary.floor_us:.1f})", flush=True)
            name = f"{decoder}_{scenario}".replace(" ", "_")
            np.savez_compressed(args.out / f"d{setup.distance}_p{setup.p:g}_{name}.npz", durations=durations, weights=weights)
    with (args.out / f"latence_d{setup.distance}_p{setup.p:g}_s{args.seed}.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(rows[0])))
        writer.writeheader()
        for summary in rows:
            writer.writerow(asdict(summary))


if __name__ == "__main__":
    main()
