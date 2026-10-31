"""BpLsdDecoder(lsd_method='lsd_cs', lsd_order=10) aborts on a single decode.

Needs only stim, numpy and ldpc. Rotated surface code, d=5, 5 rounds, memory Z,
stim's built-in circuit noise at p=0.002. Each attempt runs in its own process:
a fresh interpreter, a fresh decoder, one decode.

    python repro_lsd_single_decode.py              # scan shots, report the first that aborts
    python repro_lsd_single_decode.py --shot 17    # decode only that shot
"""

import argparse
import subprocess
import sys

CHILD = r"""
import sys
import numpy as np
import stim
from ldpc.bplsd_decoder import BpLsdDecoder
from ldpc.ckt_noise.dem_matrices import detector_error_model_to_check_matrices

shot, order, method = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
p = 0.002
circuit = stim.Circuit.generated(
    "surface_code:rotated_memory_z", distance=5, rounds=5,
    after_clifford_depolarization=p, before_round_data_depolarization=p,
    before_measure_flip_probability=p, after_reset_flip_probability=p,
)
dem = circuit.detector_error_model(decompose_errors=True)
matrices = detector_error_model_to_check_matrices(dem)
detectors = circuit.compile_detector_sampler(seed=7).sample(shots=shot + 1)

decoder = BpLsdDecoder(matrices.check_matrix, error_channel=list(matrices.priors),
                       max_iter=20, bp_method="minimum_sum",
                       lsd_method=method, lsd_order=order)
decoder.decode(detectors[shot].astype(np.uint8))
del decoder
"""


def attempt(shot: int, order: int = 10, method: str = "lsd_cs") -> int:
    return subprocess.run([sys.executable, "-c", CHILD, str(shot), str(order), method], capture_output=True).returncode


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shot", type=int)
    parser.add_argument("--max-shots", type=int, default=200)
    args = parser.parse_args()

    import ldpc

    print(f"ldpc {ldpc.__version__}, Python {sys.version.split()[0]}, {sys.platform}")
    shots = [args.shot] if args.shot is not None else range(args.max_shots)
    for shot in shots:
        code = attempt(shot)
        if code != 0:
            print(f"shot {shot}: one decode with lsd_cs order 10 exits with {code & 0xFFFFFFFF:#x}")
            for method, order in (("lsd_cs", 1), ("lsd_e", 10), ("lsd_0", 0)):
                other = attempt(shot, order, method)
                print(f"  same shot, {method} order {order}: {'clean' if other == 0 else hex(other & 0xFFFFFFFF)}")
            return
    print("no single decode aborted in the scanned shots")


if __name__ == "__main__":
    main()
