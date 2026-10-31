"""La mesure de latence rend une distribution cohérente, tir par tir."""

import numpy as np

from redteam.latency import measure, summarize, time_shots
from redteam.mismatch import Setup

SETUP = Setup(distance=3, rounds=3, p=0.002)


class Sleepy:
    def decode(self, dets):
        return np.zeros((dets.shape[0], 1), dtype=bool)


def test_une_duree_par_tir_positive():
    durations = time_shots(Sleepy(), np.zeros((20, 8), dtype=bool))
    assert durations.shape == (20,)
    assert (durations > 0).all()


def test_le_resume_ordonne_les_quantiles():
    durations = np.arange(1, 1001, dtype=float)
    summary = summarize("s", "d", SETUP, durations, np.ones(1000, dtype=int), floor_us=0.5)
    assert summary.p50_us <= summary.p90_us <= summary.p99_us <= summary.p999_us <= summary.max_us == 1000
    assert summary.per_round(summary.max_us) == 1000 / 3


def test_mesure_sur_un_scenario_du_catalogue():
    summary, durations, weights = measure(SETUP, "ancilla chaude x100", "pymatching", shots=200, seed=1, warmup=10)
    assert summary.shots == 200 == len(durations) == len(weights)
    assert summary.mean_weight > 0
    assert summary.floor_us > 0
