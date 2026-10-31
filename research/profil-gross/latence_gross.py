"""Temps de construction et de décodage par tir sur le gross code, nominal puis avec une ancilla aléatoire.

    python research/profil-gross/latence_gross.py bposd --shots 3
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from redteam.decoders import build, dem_for  # noqa: E402
from redteam.profil import GROSS, SEED, saturated  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("decoder")
    parser.add_argument("--shots", type=int, default=3)
    args = parser.parse_args()
    nominal = GROSS.nominal()
    for name, circuit in (("nominal", nominal), ("ancilla aléatoire", saturated(GROSS).true_circuits(nominal)[0])):
        start = time.perf_counter()
        decoder = build(args.decoder, dem_for(circuit))
        built = time.perf_counter() - start
        dets, _ = circuit.compile_detector_sampler(seed=SEED).sample(args.shots, separate_observables=True)
        times = []
        for row in dets:
            t = time.perf_counter()
            decoder.decode(row[None, :])
            times.append(time.perf_counter() - t)
        print(f"{args.decoder} {name}: construction {built:.1f} s, décodage par tir {min(times):.2f} à {max(times):.2f} s ({args.shots} tirs)", flush=True)


if __name__ == "__main__":
    main()
