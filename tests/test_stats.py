"""Comparaison de deux taux mesurés sur des nombres de tirs différents."""

import math

import pytest

from redteam.stats import two_proportion_z


def test_deux_taux_identiques_donnent_un_z_nul():
    assert two_proportion_z(errors_a=50, shots_a=1000, errors_b=500, shots_b=10000) == 0.0


def test_le_signe_du_z_suit_le_sens_de_l_ecart():
    assert two_proportion_z(errors_a=80, shots_a=1000, errors_b=50, shots_b=1000) > 0
    assert two_proportion_z(errors_a=50, shots_a=1000, errors_b=80, shots_b=1000) < 0


def test_le_z_vaut_la_valeur_calculee_a_la_main():
    # taux 0,06 et 0,04, taux commun 0,05, écart type sqrt(0,05 * 0,95 * 2 / 1000)
    attendu = 0.02 / math.sqrt(0.05 * 0.95 * 2 / 1000)
    assert two_proportion_z(60, 1000, 40, 1000) == pytest.approx(attendu)


def test_aucune_erreur_des_deux_cotes_donne_un_z_nul():
    assert two_proportion_z(0, 1000, 0, 5000) == 0.0


def test_un_nombre_de_tirs_nul_est_refuse():
    with pytest.raises(ValueError):
        two_proportion_z(0, 0, 1, 10)


@pytest.mark.parametrize("errors_a,shots_a,errors_b,shots_b", [(11, 10, 1, 10), (1, 10, 11, 10), (-1, 10, 1, 10)])
def test_un_nombre_d_erreurs_incoherent_est_refuse(errors_a, shots_a, errors_b, shots_b):
    with pytest.raises(ValueError):
        two_proportion_z(errors_a, shots_a, errors_b, shots_b)
