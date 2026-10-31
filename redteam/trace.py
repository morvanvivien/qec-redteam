"""Inspection des traces HDF5 de decoder-bench.

Répond à trois questions sur une trace publiée : est elle dédoublonnée, son
circuit est il celui que nous reconstruisons, et combien d'erreurs PyMatching
fait il en la rejouant. Compare ensuite à un tirage frais de même taille.

    python -m redteam.trace <data>\traces
"""

import argparse
from dataclasses import dataclass
from pathlib import Path

import h5py
import numpy as np
import pymatching
import stim

from redteam.circuits import rotated_memory_si1000
from redteam.reproduce import BATCH_SHOTS, SEED_OFFSET, TRACE_NAME


@dataclass(frozen=True)
class TraceSummary:
    name: str
    distance: int
    p: float
    basis: str
    records: int
    detectors: int
    unique_records: int
    zero_syndromes: int
    mean_weight: float
    errors: int
    circuit_matches: bool

    @property
    def is_deduplicated(self) -> bool:
        return self.unique_records == self.records and self.zero_syndromes <= 1

    @property
    def rate(self) -> float:
        return self.errors / self.records


@dataclass(frozen=True)
class FreshReference:
    shots: int
    unique_records: int
    zero_syndromes: int
    mean_weight: float


def count_unique_rows(detectors: np.ndarray) -> int:
    packed = np.packbits(detectors, axis=1)
    return np.unique(packed, axis=0).shape[0]


def read_trace(path: Path) -> tuple[np.ndarray, np.ndarray, stim.Circuit]:
    with h5py.File(path, "r") as f:
        detectors = f["syndromes"][:]
        observables = f["observables"][:]
        text = f["circuit"][()]
    return detectors, observables, stim.Circuit(text.decode() if isinstance(text, bytes) else str(text))


def summarize_trace(path: Path) -> TraceSummary:
    match = TRACE_NAME.match(path.name)
    if match is None:
        raise ValueError(f"nom de trace illisible : {path.name}")
    distance, p, basis = int(match["d"]), float(match["p"]), match["basis"]

    detectors, observables, circuit = read_trace(path)
    predictions = pymatching.Matching.from_stim_circuit(circuit).decode_batch(detectors)
    ours = rotated_memory_si1000(distance, distance, p, basis)
    return TraceSummary(
        name=path.name,
        distance=distance,
        p=p,
        basis=basis,
        records=len(detectors),
        detectors=detectors.shape[1],
        unique_records=count_unique_rows(detectors),
        zero_syndromes=int((~detectors.any(axis=1)).sum()),
        mean_weight=float(detectors.sum(axis=1).mean()),
        errors=int(np.any(predictions != observables, axis=1).sum()),
        circuit_matches=str(circuit) == str(ours),
    )


def fresh_reference(distance: int, p: float, basis: str, shots: int = BATCH_SHOTS, seed: int = SEED_OFFSET) -> FreshReference:
    """Ce que donne un tirage de Monte Carlo non dédoublonné de même taille."""
    circuit = rotated_memory_si1000(distance, distance, p, basis)
    detectors = circuit.compile_detector_sampler(seed=seed).sample(shots=shots)
    return FreshReference(
        shots=shots,
        unique_records=count_unique_rows(detectors),
        zero_syndromes=int((~detectors.any(axis=1)).sum()),
        mean_weight=float(detectors.sum(axis=1).mean()),
    )


def report(summaries: list[TraceSummary], references: list[FreshReference]) -> str:
    lines = [
        "# Traces publiées de decoder-bench, comparées à un tirage frais",
        "",
        "| trace | enregistrements | doublons | syndromes nuls | poids moyen | circuit identique | erreurs PyMatching | taux |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for s in summaries:
        lines.append(
            f"| {s.name} | {s.records} | {s.records - s.unique_records} | {s.zero_syndromes} | {s.mean_weight:.2f} "
            f"| {'oui' if s.circuit_matches else 'NON'} | {s.errors} | {s.rate:.4g} |"
        )
    lines += [
        "",
        "| tirage frais | tirs | syndromes uniques | syndromes nuls | poids moyen |",
        "|---|---|---|---|---|",
    ]
    for s, r in zip(summaries, references):
        lines.append(f"| d={s.distance} p={s.p} | {r.shots} | {r.unique_records} | {r.zero_syndromes} | {r.mean_weight:.2f} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Inspecte les traces HDF5 de decoder-bench.")
    parser.add_argument("directory", type=Path)
    parser.add_argument("--out", type=Path, default=Path("out/decoder_bench/traces.md"))
    args = parser.parse_args(argv)

    paths = sorted(args.directory.glob("*.h5"))
    if not paths:
        raise SystemExit(f"aucune trace .h5 dans {args.directory}")
    summaries = [summarize_trace(path) for path in paths]
    references = [fresh_reference(s.distance, s.p, s.basis) for s in summaries]

    text = report(summaries, references)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
