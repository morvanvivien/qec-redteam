"""Code de surface XZZX : le code de surface tourné avec une porte de Hadamard
sur un qubit de données de chaque paire diagonale, si bien que chaque
stabilisateur se lit X Z Z X. C'est le code proposé pour les qubits à biais
de bruit (qubits de chat).

Plutôt que de réécrire les portes, on conjugue le bruit : sur les qubits de
données concernés, les parts X et Z de chaque canal de Pauli sont échangées,
ce que fait exactement le même bruit physique vu à travers les Hadamard. Les
retournements de préparation et de mesure (X_ERROR, Z_ERROR) ne changent pas :
ils retournent un résultat dans les deux repères.
"""

import stim

SWAP = {"I": "I", "X": "Z", "Y": "Y", "Z": "X"}
LABELS_2 = [a + b for a in "IXYZ" for b in "IXYZ"][1:]


def conjugated_data(circuit: stim.Circuit) -> set[int]:
    """Qubits de données (coordonnées impaires) dont (x + y) / 2 est pair : une paire diagonale par plaquette."""
    return {q for q, (x, y) in circuit.get_final_qubit_coordinates().items()
            if x % 2 == 1 and y % 2 == 1 and int(x + y) // 2 % 2 == 0}


def _one(probs: list[float], swap: bool) -> list[float]:
    px, py, pz = probs
    return [pz, py, px] if swap else list(probs)


def _two(probs: list[float], swap_a: bool, swap_b: bool) -> list[float]:
    out = {}
    for (a, b), p in zip(LABELS_2, probs):
        out[(SWAP[a] if swap_a else a) + (SWAP[b] if swap_b else b)] = p
    return [out[label] for label in LABELS_2]


def xzzx(circuit: stim.Circuit, conjugated: set[int] | None = None) -> stim.Circuit:
    """Le même circuit, bruit conjugué par Hadamard sur `conjugated` (par défaut `conjugated_data`)."""
    if conjugated is None:
        conjugated = conjugated_data(circuit)
    out = stim.Circuit()
    for instruction in circuit.flattened():
        name, targets, args = instruction.name, instruction.targets_copy(), instruction.gate_args_copy()
        if name == "DEPOLARIZE1":
            name, args = "PAULI_CHANNEL_1", [args[0] / 3] * 3
        elif name == "DEPOLARIZE2":
            name, args = "PAULI_CHANNEL_2", [args[0] / 15] * 15
        if name == "PAULI_CHANNEL_1":
            for t in targets:
                out.append(name, [t], _one(args, t.value in conjugated))
        elif name == "PAULI_CHANNEL_2":
            for a, b in zip(targets[::2], targets[1::2]):
                out.append(name, [a, b], _two(args, a.value in conjugated, b.value in conjugated))
        else:
            out.append(instruction)
    return out
