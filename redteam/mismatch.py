"""Banc de désaccord : décodeur réglé sur le bruit nominal, tirs sous un bruit réel différent.

Pour chaque couple (scénario, décodeur), les mêmes tirs sont décodés deux fois :

    réglé    DEM du circuit nominal SI1000 (ce que le décodeur croit)
    informé  DEM du circuit réel du tir (ce qu'un réglage parfait donnerait ;
             pour un événement, le décodeur sait où et quand il a eu lieu)

La pénalité de réglage est le rapport des deux taux d'erreur logique, avec
un intervalle apparié. La dégradation est le taux réglé sous bruit réel
divisé par le taux du même décodeur sous bruit nominal (ligne « nominal »).

Chaque cellule tourne dans son propre processus : un décodeur qui plante ou
qui dépasse le délai donne une ligne « plantage » ou « délai », pas un banc mort.

    python -m redteam.mismatch --distance 5 --p 0.002 --decoders pymatching bposd --out out/mismatch
"""

import argparse
import csv
import multiprocessing as mp
import queue
import time
from dataclasses import asdict, dataclass, fields
from pathlib import Path

import numpy as np
import stim

from redteam.circuits import rotated_memory_si1000
from redteam.decoders import REGISTRY, build, dem_for
from redteam.scenarios import Scenario, biased_catalog, catalog
from redteam.stats import mcnemar_p, paired_ratio, wilson

DEFAULT_TARGET_ERRORS = 200
DEFAULT_MAX_SHOTS = 200_000
BATCH = 2_000


@dataclass(frozen=True)
class Setup:
    distance: int
    rounds: int
    p: float
    basis: str = "z"
    biased: bool = False
    code: str = "surface"

    def nominal(self) -> stim.Circuit:
        if self.code == "gross":
            from redteam.qldpc import gross_code

            return gross_code(self.p)
        return rotated_memory_si1000(self.distance, self.rounds, self.p, self.basis).flattened()

    def scenarios(self) -> list[Scenario]:
        if self.code == "gross":
            from redteam import qldpc

            return qldpc.catalog(self.nominal(), self.rounds, self.p)
        return biased_catalog(self.p) if self.biased else catalog(self.nominal(), self.rounds, self.p)


@dataclass
class Cell:
    scenario: str
    family: str
    decoder: str
    distance: int
    rounds: int
    p: float
    basis: str
    seed: int
    status: str = "ok"
    shots: int = 0
    errors_tuned: int = 0
    errors_informed: int = 0
    both: int = 0
    seconds: float = 0.0
    detail: str = ""

    @property
    def only_tuned(self) -> int:
        return self.errors_tuned - self.both

    @property
    def only_informed(self) -> int:
        return self.errors_informed - self.both

    def rate(self, errors: int) -> tuple[float, float, float]:
        low, high = wilson(errors, self.shots)
        return errors / self.shots, low, high

    def penalty(self) -> tuple[float, float, float]:
        return paired_ratio(self.both, self.only_tuned, self.only_informed, self.shots, seed=self.seed)

    def mcnemar(self) -> float:
        return mcnemar_p(self.only_tuned, self.only_informed)


def sample(circuits: list[stim.Circuit], shots: int, seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Tirs d'un mélange uniforme de circuits, entièrement déterminés par `seed`.

    Rend les détections, les observables et l'indice du circuit de chaque tir.
    """
    rng = np.random.default_rng(seed)
    counts = rng.multinomial(shots, [1.0 / len(circuits)] * len(circuits))
    dets, obs, variant = [], [], []
    for index, (circuit, n) in enumerate(zip(circuits, counts)):
        if n == 0:
            continue
        sampler = circuit.compile_detector_sampler(seed=(seed * 1_000_003 + index) % 2**63)
        d, o = sampler.sample(int(n), separate_observables=True)
        dets.append(d)
        obs.append(o)
        variant.append(np.full(n, index))
    order = rng.permutation(shots)
    return np.concatenate(dets)[order], np.concatenate(obs)[order], np.concatenate(variant)[order]


def decode_informed(decoders: dict, circuits: list[stim.Circuit], decoder: str, dets: np.ndarray, variant: np.ndarray, num_obs: int) -> np.ndarray:
    """Chaque tir décodé avec le DEM de son propre circuit ; décodeurs construits à la demande."""
    out = np.zeros((dets.shape[0], num_obs), dtype=bool)
    for index in np.unique(variant):
        if index not in decoders:
            decoders[index] = build(decoder, dem_for(circuits[index]))
        mask = variant == index
        out[mask] = decoders[index].decode(dets[mask])
    return out


def run_cell(setup: Setup, scenario: Scenario, decoder: str, seed: int, target_errors: int, max_shots: int) -> Cell:
    nominal = setup.nominal()
    cell = Cell(scenario.name, scenario.family, decoder, setup.distance, setup.rounds, setup.p, setup.basis, seed)
    true_circuits = scenario.true_circuits(nominal)
    tuned = build(decoder, dem_for(nominal))
    informed: dict = {}
    start = time.perf_counter()
    batch = 0
    while cell.shots < max_shots and max(cell.errors_tuned, cell.errors_informed) < target_errors:
        n = min(BATCH, max_shots - cell.shots)
        dets, obs, variant = sample(true_circuits, n, seed * 100_003 + batch)
        wrong_tuned = np.any(tuned.decode(dets) != obs, axis=1)
        wrong_informed = np.any(decode_informed(informed, true_circuits, decoder, dets, variant, obs.shape[1]) != obs, axis=1)
        cell.shots += n
        cell.errors_tuned += int(wrong_tuned.sum())
        cell.errors_informed += int(wrong_informed.sum())
        cell.both += int((wrong_tuned & wrong_informed).sum())
        batch += 1
    cell.seconds = time.perf_counter() - start
    return cell


def _worker(setup: Setup, index: int, decoder: str, seed: int, target: int, max_shots: int, out: mp.Queue) -> None:
    scenario = setup.scenarios()[index]
    try:
        out.put(asdict(run_cell(setup, scenario, decoder, seed, target, max_shots)))
    except Exception as error:  # une exception Python est un résultat du banc, pas une panne
        out.put({"status": "exception", "detail": f"{type(error).__name__}: {error}"[:300]})


def run_isolated(setup: Setup, index: int, decoder: str, seed: int, target: int, max_shots: int, timeout: float) -> Cell:
    """Une cellule dans un processus neuf ; plantage et délai deviennent des lignes."""
    scenario = setup.scenarios()[index]
    ctx = mp.get_context("spawn")
    out = ctx.Queue()
    process = ctx.Process(target=_worker, args=(setup, index, decoder, seed, target, max_shots, out))
    process.start()
    try:
        result = out.get(timeout=timeout)
    except queue.Empty:
        result = None
    process.join(5)
    base = Cell(scenario.name, scenario.family, decoder, setup.distance, setup.rounds, setup.p, setup.basis, seed)
    if result is None:
        if process.is_alive():
            process.kill()
            base.status, base.detail = "délai", f"plus de {timeout:g} s"
        else:
            base.status, base.detail = "plantage", f"code de sortie {process.exitcode}"
        return base
    if "scenario" not in result:
        base.status, base.detail = result["status"], result["detail"]
        return base
    return Cell(**result)


def run_bench(setup: Setup, decoders: list[str], seed: int, target: int, max_shots: int, timeout: float, workers: int, only: list[str] | None = None) -> list[Cell]:
    from concurrent.futures import ThreadPoolExecutor

    names = [s.name for s in setup.scenarios()]
    jobs = [(i, d) for i, name in enumerate(names) if not only or name in only for d in decoders]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(run_isolated, setup, i, d, seed, target, max_shots, timeout) for i, d in jobs]
        return [f.result() for f in futures]


COLUMNS = [f.name for f in fields(Cell)] + ["rate_tuned", "rate_tuned_low", "rate_tuned_high", "rate_informed", "penalty", "penalty_low", "penalty_high", "mcnemar_p"]


def row(cell: Cell) -> dict:
    out = asdict(cell)
    if cell.status == "ok" and cell.shots > 0:
        r, lo, hi = cell.rate(cell.errors_tuned)
        pen, plo, phi = cell.penalty()
        out.update(rate_tuned=r, rate_tuned_low=lo, rate_tuned_high=hi, rate_informed=cell.errors_informed / cell.shots,
                   penalty=pen, penalty_low=plo, penalty_high=phi, mcnemar_p=cell.mcnemar())
    return out


def write_csv(cells: list[Cell], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for cell in cells:
            writer.writerow(row(cell))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Banc de désaccord bruit réel contre bruit nominal.")
    parser.add_argument("--out", type=Path, default=Path("out/mismatch"))
    parser.add_argument("--distance", type=int, default=5)
    parser.add_argument("--rounds", type=int, default=None)
    parser.add_argument("--p", type=float, default=0.002)
    parser.add_argument("--basis", choices=("x", "z"), default="z")
    parser.add_argument("--biased", action="store_true", help="catalogue biaisé vers Z")
    parser.add_argument("--code", choices=("surface", "gross"), default="surface", help="gross : code [[144,12,12]] d'IBM, d = 12, 12 rounds")
    parser.add_argument("--decoders", nargs="+", default=["pymatching"], choices=sorted(REGISTRY))
    parser.add_argument("--only", nargs="*", default=None, help="noms de scénarios à garder")
    parser.add_argument("--seed", type=int, default=20260929)
    parser.add_argument("--target-errors", type=int, default=DEFAULT_TARGET_ERRORS)
    parser.add_argument("--max-shots", type=int, default=DEFAULT_MAX_SHOTS)
    parser.add_argument("--timeout", type=float, default=3600.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--tag", default="", help="suffixe du fichier de résultats")
    args = parser.parse_args(argv)

    if args.code == "gross":
        args.distance, args.rounds = 12, 12
    setup = Setup(args.distance, args.rounds or args.distance, args.p, args.basis, args.biased, args.code)
    cells = run_bench(setup, args.decoders, args.seed, args.target_errors, args.max_shots, args.timeout, args.workers, args.only)
    name = f"{'gross_' if setup.code == 'gross' else ''}d{setup.distance}_r{setup.rounds}_p{setup.p:g}_{setup.basis}{'_biais' if setup.biased else ''}_s{args.seed}{'_' + args.tag if args.tag else ''}.csv"
    write_csv(cells, args.out / name)
    for cell in cells:
        r = row(cell)
        if cell.status != "ok":
            print(f"{cell.scenario:24s} {cell.decoder:15s} {cell.status} {cell.detail}")
        else:
            print(f"{cell.scenario:24s} {cell.decoder:15s} {cell.errors_tuned:6d}/{cell.shots:<7d} réglé {r['rate_tuned']:.3e} informé {r['rate_informed']:.3e} pénalité {r['penalty']:.2f} [{r['penalty_low']:.2f}, {r['penalty_high']:.2f}] {cell.seconds:.0f}s")


if __name__ == "__main__":
    main()
