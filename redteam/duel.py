"""Duel apparié : plusieurs décodeurs réglés sur le nominal, décodant exactement les mêmes tirs.

Sert à affirmer un renversement de classement (« A bat B sous bruit nominal,
B bat A sous tel bruit réel ») avec un intervalle apparié, pas deux taux
mesurés sur des tirs différents.

    python -m redteam.duel --distance 5 --p 0.002 --scenario "diaphonie ZZ 3p" --decoders pymatching tesseract --shots 100000
"""

import argparse
from dataclasses import dataclass

import numpy as np

from redteam.decoders import REGISTRY, build, dem_for
from redteam.mismatch import BATCH, Setup, sample
from redteam.stats import mcnemar_p, paired_ratio, wilson


@dataclass
class Duel:
    scenario: str
    shots: int
    wrong: dict[str, np.ndarray]

    def errors(self, name: str) -> int:
        return int(self.wrong[name].sum())

    def versus(self, a: str, b: str, seed: int = 0) -> tuple[float, float, float, float]:
        """Rapport des taux de A sur B, son intervalle à 95 % et la valeur p de McNemar."""
        wa, wb = self.wrong[a], self.wrong[b]
        both, only_a, only_b = int((wa & wb).sum()), int((wa & ~wb).sum()), int((~wa & wb).sum())
        ratio, low, high = paired_ratio(both, only_a, only_b, self.shots, seed=seed)
        return ratio, low, high, mcnemar_p(only_a, only_b)


def duel(setup: Setup, scenario_name: str, decoders: list[str], shots: int, seed: int) -> Duel:
    scenario = next(s for s in setup.scenarios() if s.name == scenario_name)
    nominal = setup.nominal()
    circuits = scenario.true_circuits(nominal)
    compiled = {name: build(name, dem_for(nominal)) for name in decoders}
    wrong = {name: [] for name in decoders}
    done, batch = 0, 0
    while done < shots:
        n = min(BATCH, shots - done)
        dets, obs, _ = sample(circuits, n, seed * 100_003 + batch)
        for name, decoder in compiled.items():
            wrong[name].append(np.any(decoder.decode(dets) != obs, axis=1))
        done += n
        batch += 1
    return Duel(scenario_name, shots, {name: np.concatenate(w) for name, w in wrong.items()})


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Duel apparié de décodeurs réglés sur le nominal.")
    parser.add_argument("--distance", type=int, default=5)
    parser.add_argument("--rounds", type=int, default=None)
    parser.add_argument("--p", type=float, default=0.002)
    parser.add_argument("--basis", choices=("x", "z"), default="z")
    parser.add_argument("--scenario", nargs="+", default=["nominal"])
    parser.add_argument("--decoders", nargs="+", default=["pymatching", "tesseract"], choices=sorted(REGISTRY))
    parser.add_argument("--shots", type=int, default=50_000)
    parser.add_argument("--seed", type=int, default=20260929)
    args = parser.parse_args(argv)

    setup = Setup(args.distance, args.rounds or args.distance, args.p, args.basis)
    reference = args.decoders[0]
    for scenario in args.scenario:
        result = duel(setup, scenario, args.decoders, args.shots, args.seed)
        print(f"{scenario} — d={setup.distance} p={setup.p:g} base {setup.basis} — {result.shots} tirs, graine {args.seed}")
        for name in args.decoders:
            low, high = wilson(result.errors(name), result.shots)
            line = f"  {name:15s} {result.errors(name):6d} erreurs, {result.errors(name) / result.shots:.3e} [{low:.3e}, {high:.3e}]"
            if name != reference:
                ratio, rlow, rhigh, p = result.versus(name, reference, args.seed)
                line += f" | {name}/{reference} = {ratio:.2f} [{rlow:.2f}, {rhigh:.2f}], McNemar p = {p:.1e}"
            print(line, flush=True)


if __name__ == "__main__":
    main()
