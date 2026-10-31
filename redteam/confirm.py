"""Rejouer une cassure candidate depuis zéro avant de l'écrire.

Trois contrôles, chacun dans un processus neuf :

1. même graine deux fois : les comptes doivent être identiques au tir près ;
2. graines indépendantes : chaque réplique doit montrer l'effet, intervalles
   à 95 % à l'appui ;
3. la somme des répliques donne le chiffre retenu.

    python -m redteam.confirm --distance 5 --p 0.002 --scenario "ancilla chaude x100" --decoder bposd --seeds 11 12 13
"""

import argparse
from dataclasses import dataclass
from pathlib import Path

from redteam.mismatch import Cell, Setup, run_isolated, write_csv
from redteam.stats import mcnemar_p, paired_ratio, wilson


@dataclass(frozen=True)
class Verdict:
    deterministic: bool
    replicas: list[Cell]
    pooled: Cell

    @property
    def all_ok(self) -> bool:
        return all(c.status == "ok" for c in self.replicas)


def pool(cells: list[Cell]) -> Cell:
    first = cells[0]
    total = Cell(first.scenario, first.family, first.decoder, first.distance, first.rounds, first.p, first.basis, seed=0)
    for c in cells:
        total.shots += c.shots
        total.errors_tuned += c.errors_tuned
        total.errors_informed += c.errors_informed
        total.both += c.both
        total.seconds += c.seconds
    return total


def confirm(setup: Setup, scenario: str, decoder: str, seeds: list[int], target: int, max_shots: int, timeout: float) -> Verdict:
    index = [s.name for s in setup.scenarios()].index(scenario)
    a = run_isolated(setup, index, decoder, seeds[0], target, max_shots, timeout)
    b = run_isolated(setup, index, decoder, seeds[0], target, max_shots, timeout)
    same = a.status == b.status == "ok" and (a.shots, a.errors_tuned, a.errors_informed, a.both) == (b.shots, b.errors_tuned, b.errors_informed, b.both)
    replicas = [a] + [run_isolated(setup, index, decoder, s, target, max_shots, timeout) for s in seeds[1:]]
    return Verdict(same, replicas, pool([c for c in replicas if c.status == "ok"] or replicas))


def describe(cell: Cell) -> str:
    if cell.status != "ok":
        return f"{cell.status} {cell.detail}"
    rate, low, high = cell.errors_tuned / cell.shots, *wilson(cell.errors_tuned, cell.shots)
    irate, ilow, ihigh = cell.errors_informed / cell.shots, *wilson(cell.errors_informed, cell.shots)
    ratio, plow, phigh = paired_ratio(cell.both, cell.only_tuned, cell.only_informed, cell.shots)
    return (f"{cell.shots} tirs ; réglé {cell.errors_tuned} ({rate:.3e} [{low:.3e}, {high:.3e}]) ; "
            f"informé {cell.errors_informed} ({irate:.3e} [{ilow:.3e}, {ihigh:.3e}]) ; "
            f"pénalité {ratio:.2f} [{plow:.2f}, {phigh:.2f}] ; McNemar p = {mcnemar_p(cell.only_tuned, cell.only_informed):.1e}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Rejouer une cassure candidate depuis zéro.")
    parser.add_argument("--out", type=Path, default=Path("out/confirm"))
    parser.add_argument("--distance", type=int, default=5)
    parser.add_argument("--rounds", type=int, default=None)
    parser.add_argument("--p", type=float, default=0.002)
    parser.add_argument("--basis", choices=("x", "z"), default="z")
    parser.add_argument("--biased", action="store_true")
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--decoder", required=True)
    parser.add_argument("--seeds", type=int, nargs="+", default=[11, 12, 13])
    parser.add_argument("--target-errors", type=int, default=400)
    parser.add_argument("--max-shots", type=int, default=400_000)
    parser.add_argument("--timeout", type=float, default=7200.0)
    args = parser.parse_args(argv)

    setup = Setup(args.distance, args.rounds or args.distance, args.p, args.basis, args.biased)
    verdict = confirm(setup, args.scenario, args.decoder, args.seeds, args.target_errors, args.max_shots, args.timeout)
    print(f"{args.decoder} / {args.scenario} / d={setup.distance} p={setup.p:g} base {setup.basis}")
    print(f"même graine rejouée : {'identique' if verdict.deterministic else 'DIFFÉRENT'}")
    for cell in verdict.replicas:
        print(f"  graine {cell.seed} : {describe(cell)}")
    print(f"  cumul : {describe(verdict.pooled)}")
    name = f"{args.decoder}_{args.scenario}_d{setup.distance}_p{setup.p:g}_{setup.basis}".replace(" ", "_")
    write_csv(verdict.replicas + [verdict.pooled], args.out / f"{name}.csv")


if __name__ == "__main__":
    main()
