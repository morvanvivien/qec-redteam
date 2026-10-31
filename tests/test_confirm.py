"""La confirmation rejoue une cellule et vérifie son déterminisme."""

from redteam.confirm import confirm, describe, pool
from redteam.mismatch import Cell, Setup


def test_une_cellule_rejouee_est_deterministe_et_les_repliques_se_cumulent():
    setup = Setup(distance=3, rounds=3, p=0.002)
    verdict = confirm(setup, "ancilla chaude x100", "pymatching", seeds=[1, 2], target=20, max_shots=4_000, timeout=120)
    assert verdict.deterministic and verdict.all_ok
    assert len(verdict.replicas) == 2
    assert verdict.pooled.shots == sum(c.shots for c in verdict.replicas)
    assert "pénalité" in describe(verdict.pooled)


def test_describe_rend_le_statut_d_une_cellule_en_echec():
    cell = Cell("s", "f", "d", 3, 3, 0.002, "z", 1, status="plantage", detail="code de sortie -11")
    assert describe(cell) == "plantage code de sortie -11"
    assert pool([cell]).shots == 0
