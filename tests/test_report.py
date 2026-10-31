"""Le rapport met chaque cellule à sa place et écrit les plantages en clair."""

from redteam.mismatch import Cell, write_csv
from redteam.report import latency_table, load, table


def test_tableau_avec_penalite_degradation_et_plantage(tmp_path):
    nominal = Cell("nominal", "référence", "pymatching", 5, 5, 0.002, "z", 1, shots=1000, errors_tuned=10, errors_informed=10, both=10)
    hot = Cell("ancilla chaude x100", "local", "pymatching", 5, 5, 0.002, "z", 1, shots=1000, errors_tuned=100, errors_informed=40, both=40)
    crash = Cell("ancilla chaude x100", "local", "relay-bp", 5, 5, 0.002, "z", 1, status="exception", detail="TypeError")
    write_csv([nominal, hot, crash], tmp_path / "a.csv")
    text = table(load([tmp_path / "a.csv"]))
    assert "| scénario | pymatching | relay-bp |" in text
    assert "2.50 [" in text and "/ x10.0" in text
    assert "**exception**" in text


def test_tableau_de_latence(tmp_path):
    path = tmp_path / "l.csv"
    path.write_text("scenario,decoder,rounds,floor_us,p50_us,p99_us,p999_us,max_us\nnominal,pymatching,5,1,10,50,90,1000\n", encoding="utf-8")
    text = latency_table(load([path]))
    assert "| pymatching | nominal | 1 | 10 | 50 | 90 | 1 000 | 2 | 200 |" in text
