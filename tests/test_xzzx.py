import numpy as np
import pymatching
import stim

from redteam.mismatch import Setup
from redteam.perturb import bias
from redteam.xzzx import _two, conjugated_data, xzzx


def test_two_qubit_swap_is_a_permutation():
    probs = list(np.arange(1, 16) / 1000)
    swapped = _two(probs, True, False)
    assert sorted(swapped) == sorted(probs)
    labels = [a + b for a in "IXYZ" for b in "IXYZ"][1:]
    assert swapped[labels.index("ZI")] == probs[labels.index("XI")]
    assert _two(probs, False, False) == probs


def test_every_interior_plaquette_has_two_conjugated_qubits():
    circuit = Setup(5, 5, 0.002, "x", True).nominal()
    conj = conjugated_data(circuit)
    coords = circuit.get_final_qubit_coordinates()
    data = {tuple(c): q for q, c in coords.items() if c[0] % 2 == 1 and c[1] % 2 == 1}
    interior = [(x, y) for (x, y) in {tuple(c) for c in coords.values()} if x % 2 == 0 and y % 2 == 0
                and all((x + dx, y + dy) in data for dx in (-1, 1) for dy in (-1, 1))]
    assert interior
    for x, y in interior:
        corners = [data[(x + dx, y + dy)] for dx in (-1, 1) for dy in (-1, 1)]
        assert sum(q in conj for q in corners) == 2


def test_noiseless_behaviour_and_total_noise_are_unchanged():
    nominal = Setup(3, 3, 0.002, "x", True).nominal()
    biased = bias(nominal, 1000.0)
    tailored = xzzx(biased)
    assert tailored.num_detectors == biased.num_detectors
    assert not tailored.without_noise().compile_detector_sampler().sample(10).any()

    def total(circuit):
        return sum(sum(i.gate_args_copy()) * len(i.targets_copy()) / (2 if i.name == "PAULI_CHANNEL_2" else 1)
                   for i in circuit.flattened() if i.name.startswith("PAULI_CHANNEL"))
    assert abs(total(tailored) - total(biased)) < 1e-9


def test_xzzx_helps_matching_under_strong_z_bias():
    biased = bias(Setup(3, 3, 0.002, "x", True).nominal(), 1000.0)
    rates = []
    for circuit in (biased, xzzx(biased)):
        dem = circuit.detector_error_model(decompose_errors=True, approximate_disjoint_errors=True, ignore_decomposition_failures=True)
        dets, obs = circuit.compile_detector_sampler(seed=7).sample(6000, separate_observables=True)
        pred = pymatching.Matching.from_detector_error_model(dem).decode_batch(dets)
        rates.append(np.any(pred != obs, axis=1).mean())
    assert rates[1] < 0.7 * rates[0]
