"""Taux d'erreur logique de référence : Monte Carlo sans dédoublonnage, PyMatching, SI1000.

Sert à resserrer la barre d'erreur à bas p, là où la mesure couplée de
reproduce.py ne tire que ce qu'il faut pour atteindre sa cible de syndromes uniques.

    python -m redteam.montecarlo --p 0.001 0.0005 --max-shots 50000000
"""

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path

import sinter

from redteam.circuits import rotated_memory_si1000

DECODER = "pymatching"
DEFAULT_DISTANCE = 7
DEFAULT_MAX_SHOTS = 50_000_000
DEFAULT_WORKERS = 5


@dataclass(frozen=True)
class MonteCarloPoint:
    distance: int
    p: float
    basis: str
    shots: int
    errors: int

    @property
    def rate(self) -> float:
        return self.errors / self.shots

    @property
    def relative_error(self) -> float:
        """Écart type relatif du taux, 1 / racine du nombre d'erreurs."""
        return math.inf if self.errors == 0 else 1.0 / math.sqrt(self.errors)


def run_monte_carlo(
    distance: int,
    physical_errors: tuple[float, ...],
    max_shots: int,
    workers: int = DEFAULT_WORKERS,
    basis: str = "z",
    print_progress: bool = False,
) -> list[MonteCarloPoint]:
    if max_shots <= 0:
        raise ValueError(f"nombre de tirs positif attendu, reçu {max_shots}")
    tasks = [
        sinter.Task(
            circuit=rotated_memory_si1000(distance, distance, p, basis),
            json_metadata={"d": distance, "p": p, "basis": basis},
        )
        for p in physical_errors
    ]
    stats = sinter.collect(
        num_workers=workers,
        tasks=tasks,
        decoders=[DECODER],
        max_shots=max_shots,
        print_progress=print_progress,
    )
    points = [
        MonteCarloPoint(distance=s.json_metadata["d"], p=s.json_metadata["p"], basis=s.json_metadata["basis"], shots=s.shots, errors=s.errors)
        for s in stats
    ]
    return sorted(points, key=lambda point: point.p)


def write_csv(points: list[MonteCarloPoint], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["d", "p", "basis", "shots", "errors", "rate", "relative_error"])
        for point in points:
            writer.writerow([point.distance, point.p, point.basis, point.shots, point.errors, f"{point.rate:.6g}", f"{point.relative_error:.4f}"])


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Monte Carlo de référence, PyMatching, SI1000.")
    parser.add_argument("--out", type=Path, default=Path("out/decoder_bench/montecarlo.csv"))
    parser.add_argument("--distance", type=int, default=DEFAULT_DISTANCE)
    parser.add_argument("--p", type=float, nargs="+", required=True)
    parser.add_argument("--max-shots", type=int, default=DEFAULT_MAX_SHOTS)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    args = parser.parse_args(argv)

    points = run_monte_carlo(args.distance, tuple(args.p), args.max_shots, args.workers, print_progress=True)
    write_csv(points, args.out)
    for point in points:
        print(f"d={point.distance} p={point.p} : {point.errors} erreurs sur {point.shots} tirs, taux {point.rate:.4g} ± {100 * point.relative_error:.1f} %")


if __name__ == "__main__":
    main()
