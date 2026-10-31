"""La reproduction de decoder-bench mesure deux taux sur les mêmes tirs : brut et dédoublonné."""

import csv

import pytest

from redteam.reproduce import (
    MeasuredPoint,
    PublishedPoint,
    load_published,
    measure_point,
    published_error_count,
    verdict,
    write_csv,
    write_report,
)

HEADER = "filename,decoder,logical_error_rate,shots,time_per_shot,total_time\n"


def measured(raw_errors, unique_errors):
    return MeasuredPoint(
        published=PublishedPoint(distance=7, p=0.001, basis="z", shots=5_000_000, errors=632),
        raw_shots=6_000_000,
        raw_errors=raw_errors,
        unique_records=5_000_000,
        unique_errors=unique_errors,
        reached_target=True,
        seconds=30.0,
    )


def test_un_taux_publie_qui_ne_tombe_pas_sur_un_entier_est_refuse():
    assert published_error_count(0.0001264, 5_000_000, "trace") == 632
    with pytest.raises(ValueError):
        published_error_count(0.00012645, 5_000_000, "trace")


def test_deux_lignes_publiees_pour_le_meme_point_sont_refusees(tmp_path):
    path = tmp_path / "resultats.csv"
    ligne = "surface_circuit_7_0.001_z.h5,pymatching,0.0001264,5000000,4.7e-06,23.6\n"
    path.write_text(HEADER + ligne + ligne, encoding="utf-8")
    with pytest.raises(ValueError):
        load_published("pymatching", "surface", "circuit", 7, "z", path=path)


def test_le_verdict_bascule_a_trois_ecarts_types():
    assert verdict(2.9) == "conforme"
    assert verdict(-2.9) == "conforme"
    assert verdict(3.0) == "ÉCART"
    assert verdict(-4.2) == "ÉCART"


def test_le_taux_brut_inferieur_au_publie_donne_un_z_negatif_et_le_taux_dedoublonne_reste_conforme():
    point = measured(raw_errors=598, unique_errors=586)
    assert point.z_raw < -3
    assert abs(point.z_unique) < 3


def test_le_csv_ecrit_une_ligne_par_point_avec_les_deux_taux(tmp_path):
    path = tmp_path / "sortie" / "reproduction.csv"
    write_csv([measured(raw_errors=598, unique_errors=586)], path)
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["published_errors"] == "632"
    assert rows[0]["raw_errors"] == "598"
    assert rows[0]["unique_errors"] == "586"
    assert float(rows[0]["raw_rate"]) == pytest.approx(598 / 6_000_000, rel=1e-5)
    assert float(rows[0]["unique_rate"]) == pytest.approx(586 / 5_000_000, rel=1e-5)


def test_le_rapport_nomme_l_ecart_et_la_conformite(tmp_path):
    path = tmp_path / "reproduction.md"
    write_report([measured(raw_errors=598, unique_errors=586)], path)
    texte = path.read_text(encoding="utf-8")
    assert "| 7 | 0.001 |" in texte
    assert "ÉCART" in texte
    assert "conforme" in texte
    assert "6 000 000" in texte


def test_les_chiffres_publies_de_pymatching_sur_d7_sont_lus_dans_le_csv():
    points = load_published(decoder="pymatching", code="surface", noise="circuit", distance=7, basis="z")
    by_p = {point.p: point for point in points}
    assert sorted(by_p) == [0.0005, 0.001, 0.003, 0.005]
    assert by_p[0.005].shots == 5_000_000
    assert by_p[0.005].errors == 249_797
    assert by_p[0.001].errors == 632


def test_un_point_mesure_donne_un_taux_brut_et_un_taux_dedoublonne_sur_les_memes_tirs():
    published = PublishedPoint(distance=3, p=0.005, basis="z", shots=2000, errors=1)
    result = measure_point(published, target_records=2000, batch_shots=1000, max_batches=50)
    assert result.unique_records == 2000
    assert result.raw_shots >= result.unique_records
    assert 0 <= result.unique_errors <= result.raw_errors
    assert result.raw_shots % 1000 == 0


def test_la_collecte_s_arrete_au_plafond_de_lots_si_la_cible_est_hors_de_portee():
    published = PublishedPoint(distance=3, p=0.0005, basis="z", shots=2000, errors=1)
    result = measure_point(published, target_records=10**9, batch_shots=1000, max_batches=2)
    assert result.raw_shots == 2000
    assert result.unique_records < 10**9
    assert result.reached_target is False
