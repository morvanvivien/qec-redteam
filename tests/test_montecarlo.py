"""Le Monte Carlo de référence compte les erreurs de PyMatching sur des tirs frais, sans dédoublonnage."""

import csv

import pytest

from redteam.montecarlo import MonteCarloPoint, run_monte_carlo, write_csv


def test_chaque_valeur_de_p_donne_un_point_avec_le_nombre_de_tirs_demande():
    points = run_monte_carlo(distance=3, physical_errors=(0.003, 0.005), max_shots=4000, workers=1)
    assert [point.p for point in points] == [0.003, 0.005]
    assert all(point.shots >= 4000 for point in points)
    assert all(0 <= point.errors <= point.shots for point in points)
    assert points[0].rate < points[1].rate


def test_l_erreur_relative_vaut_un_sur_racine_du_nombre_d_erreurs():
    point = MonteCarloPoint(distance=7, p=0.001, basis="z", shots=6_000_000, errors=400)
    assert point.rate == pytest.approx(400 / 6_000_000)
    assert point.relative_error == pytest.approx(0.05)


def test_un_point_sans_erreur_a_une_erreur_relative_infinie():
    point = MonteCarloPoint(distance=7, p=0.001, basis="z", shots=1000, errors=0)
    assert point.relative_error == float("inf")


def test_le_csv_porte_une_ligne_par_point(tmp_path):
    path = tmp_path / "mc" / "montecarlo.csv"
    write_csv([MonteCarloPoint(distance=7, p=0.001, basis="z", shots=6_000_000, errors=598)], path)
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows == [{"d": "7", "p": "0.001", "basis": "z", "shots": "6000000", "errors": "598", "rate": "9.96667e-05", "relative_error": "0.0409"}]
