"""Expérience de base : seuil du code de surface décodé par PyMatching (MWPM).

Sert à prouver que la chaîne stim + sinter + pymatching tourne sur ce poste et
donne les courbes attendues : sous le seuil, une distance plus grande réduit le
taux d'erreur logique ; au dessus, elle l'augmente.

    python -m redteam.baseline --out out/baseline
"""

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path

import sinter

from redteam.circuits import rotated_memory_z

DEFAULT_DISTANCES = (3, 5, 7)
DEFAULT_PHYSICAL_ERRORS = (0.001, 0.002, 0.003, 0.004, 0.005, 0.006, 0.007, 0.008, 0.010, 0.012)
DEFAULT_MAX_SHOTS = 200_000
DEFAULT_MAX_ERRORS = 1_000
DEFAULT_WORKERS = 5
DECODER = "pymatching"


@dataclass(frozen=True)
class BaselineConfig:
    distances: tuple[int, ...] = DEFAULT_DISTANCES
    physical_errors: tuple[float, ...] = DEFAULT_PHYSICAL_ERRORS
    max_shots: int = DEFAULT_MAX_SHOTS
    max_errors: int = DEFAULT_MAX_ERRORS
    workers: int = DEFAULT_WORKERS


def build_tasks(config: BaselineConfig) -> list[sinter.Task]:
    """Une tâche par couple (distance, p), avec rounds = distance."""
    return [
        sinter.Task(
            circuit=rotated_memory_z(distance=d, rounds=d, p=p),
            json_metadata={"d": d, "r": d, "p": p},
        )
        for d in config.distances
        for p in config.physical_errors
    ]


def run_baseline(config: BaselineConfig, print_progress: bool = False) -> list[sinter.TaskStats]:
    return sinter.collect(
        num_workers=config.workers,
        tasks=build_tasks(config),
        decoders=[DECODER],
        max_shots=config.max_shots,
        max_errors=config.max_errors,
        print_progress=print_progress,
    )


def per_round_error_rate(shot_error_rate: float, rounds: int) -> float:
    """Taux d'erreur logique par round, à partir du taux par shot sur `rounds` rounds."""
    if shot_error_rate <= 0.0:
        return 0.0
    return sinter.shot_error_rate_to_piece_error_rate(shot_error_rate, pieces=rounds)


def write_csv(stats: list[sinter.TaskStats], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["decoder", "d", "r", "p", "shots", "errors", "discards", "seconds", "shot_error_rate", "round_error_rate"])
        for s in sorted(stats, key=lambda s: (s.json_metadata["d"], s.json_metadata["p"])):
            m = s.json_metadata
            shot_rate = s.errors / s.shots if s.shots else math.nan
            writer.writerow([
                s.decoder, m["d"], m["r"], m["p"], s.shots, s.errors, s.discards,
                round(s.seconds, 2), f"{shot_rate:.6g}", f"{per_round_error_rate(shot_rate, m['r']):.6g}",
            ])


def write_plot(stats: list[sinter.TaskStats], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 5))
    sinter.plot_error_rate(
        ax=ax,
        stats=stats,
        x_func=lambda s: s.json_metadata["p"],
        group_func=lambda s: f"d={s.json_metadata['d']}",
        failure_units_per_shot_func=lambda s: s.json_metadata["r"],
    )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("erreur physique p (bruit circuit-level uniforme)")
    ax.set_ylabel("erreur logique par round")
    ax.set_title("Code de surface tourné, mémoire Z, décodeur PyMatching")
    ax.grid(which="both", alpha=0.3)
    ax.legend()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Seuil du code de surface décodé par PyMatching.")
    parser.add_argument("--out", type=Path, default=Path("out/baseline"))
    parser.add_argument("--distances", type=int, nargs="+", default=list(DEFAULT_DISTANCES))
    parser.add_argument("--p", type=float, nargs="+", default=list(DEFAULT_PHYSICAL_ERRORS))
    parser.add_argument("--max-shots", type=int, default=DEFAULT_MAX_SHOTS)
    parser.add_argument("--max-errors", type=int, default=DEFAULT_MAX_ERRORS)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    args = parser.parse_args(argv)

    config = BaselineConfig(
        distances=tuple(args.distances),
        physical_errors=tuple(args.p),
        max_shots=args.max_shots,
        max_errors=args.max_errors,
        workers=args.workers,
    )
    stats = run_baseline(config, print_progress=True)
    write_csv(stats, args.out / "baseline.csv")
    write_plot(stats, args.out / "baseline.png")
    print(f"écrit : {args.out / 'baseline.csv'} et {args.out / 'baseline.png'}")


if __name__ == "__main__":
    main()
