"""Minimal reproduction: relay-bp's sinter integration raises on a DEM with one saturated qubit.

Only stim, numpy and relay-bp are used. A distance-3 rotated surface code memory
experiment with uniform circuit noise p = 0.002; one data qubit is fully
depolarized during the second round (DEPOLARIZE1(0.75) at each of its TICKs of
that round), a crude model of a leaked qubit. stim builds the detector error
model; relay-bp's SinterDecoder_RelayBP compiles it and decodes one shot.

Expected: a prediction. Observed with relay-bp 0.2.2 (and with
check_matrices.py from main at d185194):
    TypeError: argument 'detectors': 'matrix' object is not an instance of 'ndarray'
"""

import numpy as np
import stim
from relay_bp.stim.sinter.check_matrices import CheckMatrices
from relay_bp.stim.sinter.decoders import SinterDecoder_RelayBP

P = 0.002
LEAKED = 12  # a data qubit of the d = 3 layout below, at (5, 3)


def leaky_circuit() -> stim.Circuit:
    base = stim.Circuit.generated(
        "surface_code:rotated_memory_z", distance=3, rounds=3,
        after_clifford_depolarization=P, before_round_data_depolarization=P,
        before_measure_flip_probability=P, after_reset_flip_probability=P,
    ).flattened()
    out, round_index = stim.Circuit(), 0
    for instruction in base:
        out.append(instruction)
        if instruction.name == "MR":
            round_index += 1
        if instruction.name == "TICK" and round_index == 1:
            out.append("DEPOLARIZE1", [LEAKED], 0.75)
    return out


def main() -> None:
    circuit = leaky_circuit()
    dem = circuit.detector_error_model(decompose_errors=True, approximate_disjoint_errors=True, ignore_decomposition_failures=True)
    matrices = CheckMatrices.from_dem(dem, prune_decided_errors=False)
    print(f"largest edge prior after from_dem: {matrices.error_priors.max():.3f} (a probability combined from independent mechanisms never exceeds 0.5)")
    decoder = SinterDecoder_RelayBP().compile_decoder_for_dem(dem=dem)
    dets = circuit.compile_detector_sampler(seed=1).sample(1)
    packed = np.packbits(dets, axis=1, bitorder="little")
    try:
        decoder.decode_shots_bit_packed(bit_packed_detection_event_data=packed)
        print("decoded without error")
    except TypeError as error:
        print(f"TypeError: {error}")


if __name__ == "__main__":
    main()
