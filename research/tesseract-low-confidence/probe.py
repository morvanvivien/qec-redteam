"""Does sinter's tesseract adapter hide low-confidence decodes? Count them under perturbed noise.

The adapter returns predictions only; TesseractDecoder.low_confidence_flag is
set when the search gives up. This counts how often that happens.

    python research/tesseract-low-confidence/probe.py --shots 1500 --seed 99
"""

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tesseract_decoder import make_tesseract_sinter_decoders_dict  # noqa: E402

from redteam.decoders import dem_for  # noqa: E402
from redteam.mismatch import Setup, sample  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shots", type=int, default=1500)
    parser.add_argument("--seed", type=int, default=99)
    args = parser.parse_args()
    setup = Setup(5, 5, 0.002)
    nominal = setup.nominal()
    decoder = make_tesseract_sinter_decoders_dict()["tesseract"].compile_decoder_for_dem(dem=dem_for(nominal)).decoder
    for name in ("nominal", "tout x3", "ancilla chaude x100"):
        scenario = next(s for s in setup.scenarios() if s.name == name)
        dets, obs, _ = sample(scenario.true_circuits(nominal), args.shots, args.seed)
        low = wrong = wrong_low = 0
        for d, o in zip(dets, obs):
            w = bool(np.any(np.asarray(decoder.decode(d)).astype(bool) != o))
            wrong += w
            if decoder.low_confidence_flag:
                low += 1
                wrong_low += w
        print(f"{name:20s} low confidence {low}/{args.shots} (wrong among them {wrong_low}); wrong overall {wrong}", flush=True)


if __name__ == "__main__":
    main()
