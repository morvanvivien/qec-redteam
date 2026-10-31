"""Le duel décode les mêmes tirs pour tous les décodeurs."""

from redteam.duel import duel
from redteam.mismatch import Setup


def test_deux_fois_le_meme_decodeur_donne_un_rapport_de_1():
    result = duel(Setup(3, 3, 0.002), "ancilla chaude x100", ["pymatching", "fusion-blossom"], shots=3000, seed=4)
    assert result.shots == 3000 == len(result.wrong["pymatching"])
    assert result.errors("pymatching") > 0
    ratio, low, high, p = result.versus("pymatching", "pymatching")
    assert (ratio, low, high, p) == (1.0, 1.0, 1.0, 1.0)
    ratio, low, high, _ = result.versus("fusion-blossom", "pymatching")
    assert low <= ratio <= high


def test_le_duel_est_reproductible():
    a = duel(Setup(3, 3, 0.002), "diaphonie ZZ 3p", ["pymatching"], shots=2000, seed=9)
    b = duel(Setup(3, 3, 0.002), "diaphonie ZZ 3p", ["pymatching"], shots=2000, seed=9)
    assert (a.wrong["pymatching"] == b.wrong["pymatching"]).all()
