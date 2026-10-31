"""Suite de lsd_order.py : BP+OSD d'ordre 0 se comporte-t-il comme BP+LSD sur le code XZZX ?

Mêmes tirs (graine 21), même BP (min-sum, 100 itérations) ; seul le post-traitement change.

    python research/xzzx-sweep/lsd_vs_osd.py --shots 100000
"""

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from redteam.decoders import BP_MAX_ITER, MatrixCompiled, _matrices, dem_for  # noqa: E402
from redteam.stats import mcnemar_p, paired_ratio  # noqa: E402
from sweep import circuit_for  # noqa: E402


def main() -> None:
    from ldpc import BpLsdDecoder, BpOsdDecoder

    parser = argparse.ArgumentParser()
    parser.add_argument("--shots", type=int, default=100000)
    parser.add_argument("--seed", type=int, default=21)
    args = parser.parse_args()
    circuit = circuit_for("xzzx", 5, 0.002, 1000.0)
    dets, obs = circuit.compile_detector_sampler(seed=args.seed).sample(args.shots, separate_observables=True)
    m = _matrices(dem_for(circuit))
    common = dict(error_channel=list(m.priors), max_iter=BP_MAX_ITER, bp_method="minimum_sum")
    variants = {
        "BP+OSD osd_0": BpOsdDecoder(m.check_matrix, osd_method="osd_0", osd_order=0, **common),
        "BP+OSD osd_cs 10": BpOsdDecoder(m.check_matrix, osd_method="osd_cs", osd_order=10, **common),
        "BP+LSD lsd_0, 1 bit par pas": BpLsdDecoder(m.check_matrix, lsd_method="lsd_0", lsd_order=0, **common),
        "BP+LSD lsd_0, 4 bits par pas": BpLsdDecoder(m.check_matrix, lsd_method="lsd_0", lsd_order=0, bits_per_step=4, **common),
    }
    wrong = {name: np.any(MatrixCompiled(dec, m.observables_matrix).decode(dets) != obs, axis=1) for name, dec in variants.items()}
    ref = wrong["BP+OSD osd_cs 10"]
    for name, w in wrong.items():
        both, a, b = int((w & ref).sum()), int((w & ~ref).sum()), int((~w & ref).sum())
        ratio, low, high = paired_ratio(both, a, b, args.shots, seed=1)
        print(f"{name}: {w.sum()}/{args.shots}, / BP+OSD osd_cs 10 = {ratio:.2f} [{low:.2f} ; {high:.2f}], McNemar p = {mcnemar_p(a, b):.1e}", flush=True)


if __name__ == "__main__":
    main()
