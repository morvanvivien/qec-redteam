"""Le banc de désaccord est reproductible et isole les plantages."""

import numpy as np
import pytest

from redteam.circuits import rotated_memory_si1000
from redteam.mismatch import Cell, Setup, row, run_cell, run_isolated, sample, write_csv
from redteam.stats import mcnemar_p, paired_ratio, wilson

SETUP = Setup(distance=3, rounds=3, p=0.002)


def scenario(name):
    return next(s for s in SETUP.scenarios() if s.name == name)


def test_l_echantillonnage_d_un_melange_est_fixe_par_la_graine():
    circuits = [rotated_memory_si1000(3, 3, p).flattened() for p in (0.001, 0.01)]
    a = sample(circuits, 500, seed=3)
    b = sample(circuits, 500, seed=3)
    c = sample(circuits, 500, seed=4)
    assert all(np.array_equal(x, y) for x, y in zip(a, b))
    assert not np.array_equal(a[0], c[0])
    assert set(np.unique(a[2])) == {0, 1}


def test_sous_bruit_nominal_regle_et_informe_sont_identiques():
    cell = run_cell(SETUP, scenario("nominal"), "pymatching", seed=1, target_errors=20, max_shots=20_000)
    assert cell.errors_tuned == cell.errors_informed == cell.both
    assert cell.errors_tuned >= 20
    assert cell.penalty()[0] == 1.0


def test_une_cellule_rejouee_avec_la_meme_graine_donne_les_memes_comptes():
    a = run_cell(SETUP, scenario("ancilla chaude x100"), "pymatching", seed=5, target_errors=30, max_shots=10_000)
    b = run_cell(SETUP, scenario("ancilla chaude x100"), "pymatching", seed=5, target_errors=30, max_shots=10_000)
    assert (a.shots, a.errors_tuned, a.errors_informed, a.both) == (b.shots, b.errors_tuned, b.errors_informed, b.both)


def test_un_melange_est_decode_variante_par_variante():
    cell = run_cell(SETUP, scenario("fuite ancilla 1r"), "pymatching", seed=2, target_errors=30, max_shots=10_000)
    assert cell.status == "ok" and cell.shots > 0
    assert cell.errors_informed <= cell.errors_tuned * 2


def test_la_cellule_isolee_renvoie_une_ligne(tmp_path):
    index = [s.name for s in SETUP.scenarios()].index("nominal")
    cell = run_isolated(SETUP, index, "pymatching", seed=1, target=5, max_shots=2_000, timeout=120)
    assert cell.status == "ok" and cell.shots > 0
    write_csv([cell, Cell("x", "y", "z", 3, 3, 0.002, "z", 1, status="plantage")], tmp_path / "a.csv")
    assert (tmp_path / "a.csv").read_text(encoding="utf-8").count("\n") == 3
    assert "penalty" in row(cell)


def test_wilson_encadre_le_taux():
    low, high = wilson(10, 1000)
    assert low < 0.01 < high
    assert wilson(0, 100)[0] == 0.0
    with pytest.raises(ValueError):
        wilson(5, 0)


def test_rapport_apparie_et_mcnemar():
    ratio, low, high = paired_ratio(both=50, only_a=150, only_b=10, shots=10_000)
    assert ratio == pytest.approx(200 / 60)
    assert 1.0 < low < ratio < high
    assert mcnemar_p(150, 10) < 1e-20
    assert mcnemar_p(10, 10) == 1.0
    assert paired_ratio(0, 3, 0, 100)[0] == float("inf")
