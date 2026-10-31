"""Bruit SI1000 (superconducting inspired) appliqué à un circuit stim sans bruit.

Le modèle vient tel quel de decoder-bench (third_party/decoder_bench/noise.py,
MIT), lui-même dérivé de strilanc/honeycomb_threshold. Le reprendre à
l'identique est la condition pour reproduire leurs chiffres.

    portes à deux qubits      p
    portes à un qubit, attente p / 10
    réinitialisation          2 p
    mesure                    5 p
    attente pendant mesure    2 p
"""

import stim

from third_party.decoder_bench.noise import NoiseModel

# Au delà, l'erreur de mesure 5 p atteint 0,5 et la mesure ne porte plus d'information.
MAX_SI1000_P = 0.1


def si1000(circuit: stim.Circuit, p: float) -> stim.Circuit:
    if not 0.0 < p < MAX_SI1000_P:
        raise ValueError(f"p dans ]0, {MAX_SI1000_P}[ attendu, reçu {p}")
    return NoiseModel.SI1000(p).noisy_circuit(circuit)
