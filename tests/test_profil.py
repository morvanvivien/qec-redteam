"""Le profil de robustesse attrape un décodeur qui plante et laisse passer un décodeur sain."""

import json
from dataclasses import asdict

import pytest

from redteam.profil import ECHOUEE, NON_MESURABLE, REUSSIE, Epreuve, Profil, badge, card, e1_tenue, e2_coherence, grade, profile


def test_pymatching_reussit_le_mode_rapide():
    profil = profile("pymatching", "rapide")
    assert [e.code for e in profil.epreuves] == ["E1", "E2"]
    assert all(e.verdict == REUSSIE for e in profil.epreuves)
    assert profil.tenue


def test_relay_bp_publie_echoue_a_la_tenue():
    pytest.importorskip("relay_bp")  # pas de roue Windows
    e1 = e1_tenue("relay-bp", shots=50)
    assert e1.verdict == ECHOUEE
    assert "TypeError" in e1.detail
    assert e2_coherence("relay-bp", shots=200).verdict == NON_MESURABLE


def test_notes_et_rendus():
    assert grade(1.2, (1.5, 2.5, 4.0)) == "A"
    assert grade(5.0, (1.5, 2.5, 4.0)) == "D"
    profil = Profil("x", "0.1", "rapide", [Epreuve("E1", "Tenue", REUSSIE), Epreuve("E2", "Cohérence", ECHOUEE, detail="pire")])
    assert not profil.tenue
    assert "| E2 Cohérence | échouée |" in card(profil)
    svg = badge(profil)
    assert svg.startswith("<svg") and "#C62828" in svg
    json.dumps(asdict(profil), ensure_ascii=False)


def test_mode_gross_non_applicable_aux_decodeurs_de_couplage():
    from redteam.profil import NON_APPLICABLE, profile

    profil = profile("pymatching", "gross")
    assert [e.verdict for e in profil.epreuves] == [NON_APPLICABLE, NON_APPLICABLE]
    assert profil.tenue


def test_saturated_sur_le_gross_code_cible_une_ancilla():
    from redteam.profil import GROSS, saturated
    from redteam.qldpc import data_and_ancillas

    scenario = saturated(GROSS)
    assert str(data_and_ancillas(GROSS.nominal())[1][0]) in scenario.description
