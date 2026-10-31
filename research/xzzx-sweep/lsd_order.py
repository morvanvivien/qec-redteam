"""BP+LSD sur le code XZZX : l'écart avec PyMatching vient-il de notre réglage prudent (lsd_0, ordre 0) ?

Compare, sur les mêmes tirs que sweep.py (graine 21), lsd_0 ordre 0 (notre réglage), lsd_e ordre 2 et
lsd_e ordre 4. La méthode lsd_cs n'est pas utilisée : elle corrompt la mémoire dès l'ordre 2 (ldpc #105).

    python research/xzzx-sweep/lsd_order.py --shots 100000
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from redteam.decoders import BP_MAX_ITER, MatrixCompiled, _matrices, dem_for  # noqa: E402
from redteam.stats import mcnemar_p, paired_ratio  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sweep import circuit_for  # noqa: E402

RUNS = Path(__file__).resolve().parent / "runs"


def main() -> None:
    from ldpc import BpLsdDecoder

    parser = argparse.ArgumentParser()
    parser.add_argument("--shots", type=int, default=100000)
    parser.add_argument("--seed", type=int, default=21)
    args = parser.parse_args()
    circuit = circuit_for("xzzx", 5, 0.002, 1000.0)
    dets, obs = circuit.compile_detector_sampler(seed=args.seed).sample(args.shots, separate_observables=True)
    ref = json.loads((RUNS / f"xzzx_pymatching_d5_eta1000_s{args.seed}.json").read_text())
    wrong_ref = np.zeros(args.shots, dtype=bool)
    wrong_ref[[i for i in ref["wrong"] if i < args.shots]] = True
    m = _matrices(dem_for(circuit))
    for method, order in (("lsd_0", 0), ("lsd_e", 2), ("lsd_e", 4)):
        decoder = BpLsdDecoder(m.check_matrix, error_channel=list(m.priors), max_iter=BP_MAX_ITER,
                               bp_method="minimum_sum", lsd_method=method, lsd_order=order)
        wrong = np.any(MatrixCompiled(decoder, m.observables_matrix).decode(dets) != obs, axis=1)
        both, only_a, only_b = int((wrong & wrong_ref).sum()), int((wrong & ~wrong_ref).sum()), int((~wrong & wrong_ref).sum())
        ratio, low, high = paired_ratio(both, only_a, only_b, args.shots, seed=1)
        print(f"{method} ordre {order}: {wrong.sum()}/{args.shots}, / PyMatching {ratio:.2f} [{low:.2f} ; {high:.2f}], McNemar p = {mcnemar_p(only_a, only_b):.1e}", flush=True)


if __name__ == "__main__":
    main()
