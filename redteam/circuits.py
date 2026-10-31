"""Circuits de référence : code de surface tourné avec bruit circuit-level uniforme.

Le bruit « uniforme » applique la même probabilité p à quatre canaux, c'est le
modèle standard des générateurs de stim et de la plupart des benchmarks publics.
"""

import stim

from redteam.noise import si1000

MIN_DISTANCE = 3
MAX_PHYSICAL_ERROR = 0.5
BASES = ("x", "z")


def check_geometry(distance: int, rounds: int) -> None:
    if distance < MIN_DISTANCE or distance % 2 == 0:
        raise ValueError(f"distance impaire >= {MIN_DISTANCE} attendue, reçu {distance}")
    if rounds < 1:
        raise ValueError(f"rounds >= 1 attendu, reçu {rounds}")


def rotated_memory_si1000(distance: int, rounds: int, p: float, basis: str = "z") -> stim.Circuit:
    """Mémoire sur code de surface tourné, bruit SI1000, construction de decoder-bench."""
    check_geometry(distance, rounds)
    if basis not in BASES:
        raise ValueError(f"base parmi {BASES} attendue, reçu {basis!r}")
    noiseless = stim.Circuit.generated(
        f"surface_code:rotated_memory_{basis}",
        distance=distance,
        rounds=rounds,
    )
    return si1000(noiseless, p)


def rotated_memory_z(distance: int, rounds: int, p: float) -> stim.Circuit:
    """Expérience de mémoire Z sur code de surface tourné de distance `distance`."""
    check_geometry(distance, rounds)
    if not 0.0 <= p < MAX_PHYSICAL_ERROR:
        raise ValueError(f"p dans [0, {MAX_PHYSICAL_ERROR}) attendu, reçu {p}")
    return stim.Circuit.generated(
        "surface_code:rotated_memory_z",
        distance=distance,
        rounds=rounds,
        after_clifford_depolarization=p,
        before_round_data_depolarization=p,
        before_measure_flip_probability=p,
        after_reset_flip_probability=p,
    )
