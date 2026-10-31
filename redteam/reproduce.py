"""Reproduction des chiffres publiés de decoder-bench pour PyMatching.

Pour chaque point publié, on tire des syndromes frais avec le même circuit et
le même bruit, on décode, et on mesure deux taux sur les mêmes tirs :

    brut          erreurs / tirs, l'estimateur de Monte Carlo habituel
    dédoublonné   erreurs / syndromes uniques, ce que mesure une trace de
                  decoder-bench générée avec store_unique=True

    python -m redteam.reproduce --out out/decoder_bench
"""

import argparse
import csv
import re
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pymatching

from redteam.circuits import rotated_memory_si1000
from redteam.dedup import empty_seen, first_occurrences
from redteam.stats import two_proportion_z

PUBLISHED_CSV = Path(__file__).resolve().parent.parent / "third_party" / "decoder_bench" / "benchmark_results.csv"
TRACE_NAME = re.compile(r"^(?P<code>[a-z]+)_(?P<noise>circuit|phenom|code_capacity)_(?P<d>\d+)_(?P<p>[\d.]+)_(?P<basis>[xz])\.h5$")
# decoder-bench tire un million de syndromes par itération, graine = itération + 42.
BATCH_SHOTS = 1_000_000
SEED_OFFSET = 42
MAX_BATCHES = 200
SIGNIFICANT_Z = 3.0
# Le CSV publie un taux, pas un nombre d'erreurs : taux * tirs doit tomber sur un entier.
ERROR_COUNT_TOLERANCE = 1e-3


@dataclass(frozen=True)
class PublishedPoint:
    distance: int
    p: float
    basis: str
    shots: int
    errors: int

    @property
    def rate(self) -> float:
        return self.errors / self.shots


@dataclass(frozen=True)
class MeasuredPoint:
    published: PublishedPoint
    raw_shots: int
    raw_errors: int
    unique_records: int
    unique_errors: int
    reached_target: bool
    seconds: float

    @property
    def raw_rate(self) -> float:
        return self.raw_errors / self.raw_shots

    @property
    def unique_rate(self) -> float:
        return self.unique_errors / self.unique_records

    @property
    def z_raw(self) -> float:
        return two_proportion_z(self.raw_errors, self.raw_shots, self.published.errors, self.published.shots)

    @property
    def z_unique(self) -> float:
        return two_proportion_z(self.unique_errors, self.unique_records, self.published.errors, self.published.shots)


def published_error_count(rate: float, shots: int, source: str) -> int:
    """Nombre d'erreurs derrière un taux publié, refusé s'il ne tombe pas sur un entier."""
    product = rate * shots
    errors = round(product)
    if abs(product - errors) > ERROR_COUNT_TOLERANCE:
        raise ValueError(f"{source} : taux {rate} sur {shots} tirs ne donne pas un nombre entier d'erreurs ({product})")
    return errors


def load_published(decoder: str, code: str, noise: str, distance: int, basis: str, path: Path = PUBLISHED_CSV) -> list[PublishedPoint]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    points: dict[float, PublishedPoint] = {}
    for row in rows:
        match = TRACE_NAME.match(row["filename"])
        if match is None or row["decoder"] != decoder:
            continue
        if (match["code"], match["noise"], int(match["d"]), match["basis"]) != (code, noise, distance, basis):
            continue
        p = float(match["p"])
        if p in points:
            raise ValueError(f"{row['filename']} : deux lignes publiées pour le même point")
        shots = int(row["shots"])
        points = {**points, p: PublishedPoint(
            distance=distance,
            p=p,
            basis=basis,
            shots=shots,
            errors=published_error_count(float(row["logical_error_rate"]), shots, row["filename"]),
        )}
    return [points[p] for p in sorted(points)]


def measure_point(
    published: PublishedPoint,
    target_records: int | None = None,
    batch_shots: int = BATCH_SHOTS,
    max_batches: int = MAX_BATCHES,
) -> MeasuredPoint:
    """Tire des lots jusqu'à collecter `target_records` syndromes uniques."""
    target = published.shots if target_records is None else target_records
    circuit = rotated_memory_si1000(published.distance, published.distance, published.p, published.basis)
    matcher = pymatching.Matching.from_stim_circuit(circuit)

    if target <= 0:
        raise ValueError(f"cible d'enregistrements positive attendue, reçu {target}")

    started = time.perf_counter()
    seen = empty_seen(width=(circuit.num_detectors + 7) // 8)
    raw_shots = raw_errors = unique_records = unique_errors = 0
    reached_target = False
    for batch in range(max_batches):
        sampler = circuit.compile_detector_sampler(seed=batch + SEED_OFFSET)
        detectors, observables = sampler.sample(shots=batch_shots, bit_packed=True, separate_observables=True)
        predictions = matcher.decode_batch(detectors, bit_packed_shots=True, bit_packed_predictions=True)
        failed = np.any(predictions != observables, axis=1)
        mask, seen, stopped_at = first_occurrences(detectors, seen, remaining=target - unique_records)

        raw_shots += batch_shots
        raw_errors += int(failed.sum())
        unique_records += int(mask.sum())
        unique_errors += int(failed[mask].sum())
        if stopped_at is not None:
            reached_target = True
            break

    return MeasuredPoint(
        published=published,
        raw_shots=raw_shots,
        raw_errors=raw_errors,
        unique_records=unique_records,
        unique_errors=unique_errors,
        reached_target=reached_target,
        seconds=time.perf_counter() - started,
    )


def verdict(z: float) -> str:
    return "conforme" if abs(z) < SIGNIFICANT_Z else "ÉCART"


def write_csv(results: list[MeasuredPoint], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "d", "p", "basis", "published_shots", "published_errors", "published_rate",
            "raw_shots", "raw_errors", "raw_rate", "z_raw",
            "unique_records", "unique_errors", "unique_rate", "z_unique",
            "reached_target", "seconds",
        ])
        for r in results:
            pub = r.published
            writer.writerow([
                pub.distance, pub.p, pub.basis, pub.shots, pub.errors, f"{pub.rate:.6g}",
                r.raw_shots, r.raw_errors, f"{r.raw_rate:.6g}", f"{r.z_raw:.2f}",
                r.unique_records, r.unique_errors, f"{r.unique_rate:.6g}", f"{r.z_unique:.2f}",
                r.reached_target, round(r.seconds, 1),
            ])


def write_report(results: list[MeasuredPoint], path: Path) -> None:
    lines = [
        "# Reproduction de decoder-bench, PyMatching, code de surface, SI1000",
        "",
        "Taux d'erreur logique par tir. z = écart au chiffre publié, en écarts types ;",
        f"au delà de {SIGNIFICANT_Z:g} en valeur absolue, les deux mesures ne décrivent pas la même grandeur.",
        "",
        "| d | p | publié | brut | z brut | dédoublonné | z dédoublonné | tirs bruts pour la cible |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        pub = r.published
        target = f"{r.raw_shots:,}".replace(",", " ") + ("" if r.reached_target else " (cible non atteinte)")
        lines.append(
            f"| {pub.distance} | {pub.p} | {pub.rate:.4g} | {r.raw_rate:.4g} | {r.z_raw:+.1f} {verdict(r.z_raw)} "
            f"| {r.unique_rate:.4g} | {r.z_unique:+.1f} {verdict(r.z_unique)} | {target} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Reproduit les chiffres publiés de decoder-bench pour PyMatching.")
    parser.add_argument("--out", type=Path, default=Path("out/decoder_bench"))
    parser.add_argument("--distance", type=int, default=7)
    parser.add_argument("--basis", choices=["x", "z"], default="z")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--max-batches", type=int, default=MAX_BATCHES)
    args = parser.parse_args(argv)

    published = load_published("pymatching", "surface", "circuit", args.distance, args.basis)
    if not published:
        raise SystemExit(f"aucun chiffre publié pour d={args.distance}, base {args.basis}")

    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(measure_point, point, None, BATCH_SHOTS, args.max_batches) for point in published]
        results = [future.result() for future in futures]

    write_csv(results, args.out / "reproduction.csv")
    write_report(results, args.out / "reproduction.md")
    print((args.out / "reproduction.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
