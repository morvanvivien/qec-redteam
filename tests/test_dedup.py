"""Le dédoublonnage garde la première occurrence de chaque syndrome, comme decoder-bench."""

import numpy as np
import pytest

from redteam.dedup import empty_seen, first_occurrences

A = [1, 0, 0]
B = [0, 1, 0]
C = [0, 0, 1]
WIDTH = 3


def rows(*values):
    return np.array(values, dtype=np.uint8)


def test_seule_la_premiere_occurrence_de_chaque_ligne_est_gardee():
    mask, seen, stopped_at = first_occurrences(rows(A, B, A, C, B), seen=empty_seen(WIDTH), remaining=100)
    assert mask.tolist() == [True, True, False, True, False]
    assert len(seen) == 3
    assert stopped_at is None


def test_les_lignes_deja_vues_dans_un_lot_precedent_sont_ecartees():
    _, seen, _ = first_occurrences(rows(A, B), seen=empty_seen(WIDTH), remaining=100)
    mask, seen, _ = first_occurrences(rows(B, C, A), seen=seen, remaining=100)
    assert mask.tolist() == [False, True, False]
    assert len(seen) == 3


def test_la_collecte_s_arrete_a_la_ligne_qui_atteint_la_cible():
    mask, seen, stopped_at = first_occurrences(rows(A, A, B, C, C), seen=empty_seen(WIDTH), remaining=2)
    assert mask.tolist() == [True, False, True, False, False]
    assert stopped_at == 2
    assert len(seen) == 2


def test_le_tableau_recu_n_est_pas_modifie():
    _, seen, _ = first_occurrences(rows(A, B), seen=empty_seen(WIDTH), remaining=100)
    avant = seen.copy()
    first_occurrences(rows(C), seen=seen, remaining=100)
    assert len(seen) == 2
    assert np.array_equal(seen, avant)


def test_deux_lignes_qui_ne_different_que_par_un_octet_nul_final_restent_distinctes():
    mask, seen, _ = first_occurrences(rows([1, 0, 0], [1, 2, 0], [1, 2, 0]), seen=empty_seen(WIDTH), remaining=100)
    assert mask.tolist() == [True, True, False]
    assert len(seen) == 2


@pytest.mark.parametrize("remaining", [0, -1])
def test_une_cible_deja_atteinte_est_refusee(remaining):
    with pytest.raises(ValueError):
        first_occurrences(rows(A), seen=empty_seen(WIDTH), remaining=remaining)


def test_une_largeur_nulle_est_refusee():
    with pytest.raises(ValueError):
        empty_seen(0)
