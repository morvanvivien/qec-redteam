"""La chaîne stim + sinter + pymatching tourne et donne des taux plausibles."""

import csv

from redteam.baseline import BaselineConfig, per_round_error_rate, run_baseline, write_csv, write_plot


def test_le_csv_et_le_graphique_sont_ecrits_pour_chaque_point(tmp_path):
    config = BaselineConfig(distances=(3,), physical_errors=(0.005, 0.01), max_shots=1000, max_errors=50, workers=1)
    stats = run_baseline(config)

    write_csv(stats, tmp_path / "base" / "baseline.csv")
    write_plot(stats, tmp_path / "base" / "baseline.png")

    with (tmp_path / "base" / "baseline.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert [row["p"] for row in rows] == ["0.005", "0.01"]
    assert all(row["decoder"] == "pymatching" and row["d"] == "3" for row in rows)
    assert all(0.0 <= float(row["round_error_rate"]) <= float(row["shot_error_rate"]) for row in rows)
    assert (tmp_path / "base" / "baseline.png").stat().st_size > 0


def test_sous_le_seuil_le_taux_logique_de_d3_reste_faible():
    config = BaselineConfig(distances=(3,), physical_errors=(0.001,), max_shots=2000, max_errors=50, workers=1)
    stats = run_baseline(config)
    assert len(stats) == 1
    stat = stats[0]
    assert stat.shots >= 2000
    assert stat.errors / stat.shots < 0.05


def test_le_taux_par_round_est_borne_par_le_taux_par_shot():
    assert per_round_error_rate(shot_error_rate=0.0, rounds=5) == 0.0
    taux_shot = 0.10
    taux_round = per_round_error_rate(shot_error_rate=taux_shot, rounds=5)
    assert 0.0 < taux_round < taux_shot
