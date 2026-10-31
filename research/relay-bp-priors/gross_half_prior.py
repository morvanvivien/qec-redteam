"""Effect of priors of exactly 1/2 on relay-bp on IBM's gross code [[144, 12, 12]].

On the gross code the DEM is not decomposable, so relay-bp's CheckMatrices takes
the non-decomposed path: no summed priors, no exception. A fully randomized
qubit still gives columns with a prior of exactly 1/2, the case that trips the
min-sum core (see repro_half_prior.py).

Same shots decoded by three relay-bp decoders (decoder-bench parameters):

    informed   compiled from the true DEM, priors as given (some exactly 1/2)
    clamped    same, priors clamped to 1/2 - 1e-5
    tuned      compiled from the nominal DEM (ignores the event)

A shot is wrong if any of the 12 logical observables is mispredicted.

    python research/relay-bp-priors/gross_half_prior.py --p 0.003 --shots 30 --seed 5
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import relay_bp  # noqa: E402
from relay_bp.stim.sinter.check_matrices import CheckMatrices  # noqa: E402

from redteam.decoders import dem_for  # noqa: E402
from redteam.mismatch import Setup  # noqa: E402
from redteam.stats import wilson  # noqa: E402

RELAY = dict(gamma0=0.1, pre_iter=80, num_sets=60, set_max_iter=60, gamma_dist_interval=(-0.24, 0.66), stop_nconv=3)
CAP = 0.5 - 1e-5


def decoder(dem, cap: bool):
    m = CheckMatrices.from_dem(dem)
    if m.syndrome_bias is not None:
        raise RuntimeError("decided errors on this DEM: not the case studied here")
    priors = np.minimum(m.error_priors, CAP) if cap else m.error_priors
    return relay_bp.RelayDecoderF32(m.check_matrix, error_priors=priors, **RELAY), m


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--p", type=float, default=0.003)
    parser.add_argument("--scenario", default="fuite ancilla")
    parser.add_argument("--shots", type=int, default=30)
    parser.add_argument("--seed", type=int, default=5)
    args = parser.parse_args()
    setup = Setup(12, 12, args.p, code="gross")
    nominal = setup.nominal()
    scenario = next(s for s in setup.scenarios() if s.name == args.scenario)
    real = scenario.true_circuits(nominal)[0]
    dets, obs = real.compile_detector_sampler(seed=args.seed).sample(args.shots, separate_observables=True)
    dem_real = dem_for(real)
    half = int((CheckMatrices.from_dem(dem_real).error_priors == 0.5).sum())
    print(f"gross code p={args.p} « {scenario.name} » ({scenario.description}), graine {args.seed}, {args.shots} tirs, colonnes à 1/2 : {half}", flush=True)
    for name, dem, cap in (("informed", dem_real, False), ("clamped", dem_real, True), ("tuned", dem_for(nominal), False)):
        dec, m = decoder(dem, cap)
        wrong = fails = 0
        iterations, seconds = [], []
        for s, o in zip(dets.astype(np.uint8), obs):
            start = time.perf_counter()
            r = dec.decode_detailed(s)
            seconds.append(time.perf_counter() - start)
            e = np.asarray(r.decoding)
            wrong += int(np.any(((m.observables_matrix @ e) % 2).astype(bool) != o))
            fails += int(not r.success)
            iterations.append(r.iterations)
        low, high = wilson(wrong, args.shots)
        print(f"  {name:9s} erreurs {wrong}/{args.shots} = {wrong / args.shots:.3f} [{low:.3f}, {high:.3f}], "
              f"échecs de convergence {fails}, itérations médiane {int(np.median(iterations))} max {max(iterations)}, "
              f"secondes par tir médiane {np.median(seconds):.2f} max {max(seconds):.2f}", flush=True)


if __name__ == "__main__":
    main()
