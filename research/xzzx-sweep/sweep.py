"""Les neuf décodeurs sur le code XZZX sous bruit biaisé vers Z, contre le code de surface ordinaire.

Question : quels décodeurs profitent du code fait pour les qubits à biais de
bruit, et lesquels perdent ce gain (comme fusion-blossom via sinter, constat 004) ?
Chaque décodeur est construit sur le vrai DEM ; mêmes tirs pour tous les
décodeurs d'un même code et d'une même graine. Chaque exécution écrit la liste
des tirs faux, ce qui permet ensuite des comparaisons appariées avec PyMatching.

    python research/xzzx-sweep/sweep.py --code xzzx --decoder tesseract --seed 11 --shots 10000
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from redteam.decoders import build, dem_for  # noqa: E402
from redteam.mismatch import Setup  # noqa: E402
from redteam.perturb import bias  # noqa: E402
from redteam.xzzx import xzzx  # noqa: E402

OUT = Path(__file__).resolve().parent / "runs"
CHUNK = 500


def circuit_for(code: str, distance: int, p: float, eta: float):
    biased = bias(Setup(distance, distance, p, "x", True).nominal(), eta)
    return xzzx(biased) if code == "xzzx" else biased


def run(code: str, decoder: str, distance: int, p: float, eta: float, seed: int, shots: int, budget: float) -> dict:
    circuit = circuit_for(code, distance, p, eta)
    dets, obs = circuit.compile_detector_sampler(seed=seed).sample(shots, separate_observables=True)
    start = time.perf_counter()
    compiled = build(decoder, dem_for(circuit))
    wrong, done = [], 0
    while done < shots and time.perf_counter() - start < budget:
        pred = compiled.decode(dets[done:done + CHUNK])
        bad = np.flatnonzero(np.any(pred != obs[done:done + CHUNK], axis=1)) + done
        wrong.extend(int(i) for i in bad)
        done = min(done + CHUNK, shots)
    return {"code": code, "decoder": decoder, "distance": distance, "p": p, "eta": eta, "seed": seed,
            "shots": done, "errors": len(wrong), "wrong": wrong, "seconds": round(time.perf_counter() - start, 1)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", choices=("css", "xzzx"), required=True)
    parser.add_argument("--decoder", required=True)
    parser.add_argument("--distance", type=int, default=5)
    parser.add_argument("--p", type=float, default=0.002)
    parser.add_argument("--eta", type=float, default=1000.0)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--shots", type=int, default=10000)
    parser.add_argument("--budget", type=float, default=3000.0, help="secondes de décodage au plus ; le nombre de tirs décodés est noté")
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    result = run(args.code, args.decoder, args.distance, args.p, args.eta, args.seed, args.shots, args.budget)
    name = f"{args.code}_{args.decoder}_d{args.distance}_eta{args.eta:g}_s{args.seed}.json"
    (OUT / name).write_text(json.dumps(result))
    print(f"{name}: {result['errors']}/{result['shots']} en {result['seconds']} s", flush=True)


if __name__ == "__main__":
    main()
