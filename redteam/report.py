"""Tableau scénario × décodeur en Markdown à partir des CSV du banc et de la latence.

    python -m redteam.report out/mismatch/*.csv --latency out/latency/*.csv > tableau.md

Chaque case donne la pénalité de réglage (réglé / informé) avec son
intervalle à 95 %, et la dégradation (taux réglé sous bruit réel / taux du même
décodeur sous bruit nominal). Les plantages, exceptions et délais sont écrits
en toutes lettres.
"""

import argparse
import csv
from collections import defaultdict
from pathlib import Path


def load(paths: list[Path]) -> list[dict]:
    rows = []
    for path in paths:
        with path.open(encoding="utf-8") as f:
            rows.extend(csv.DictReader(f))
    return rows


def key(row: dict) -> tuple:
    return (row["distance"], row["rounds"], float(row["p"]), row["basis"])


def cell_text(row: dict, nominal_rate: float | None) -> str:
    if row["status"] != "ok":
        return f"**{row['status']}**"
    penalty, low, high = (float(row[k]) for k in ("penalty", "penalty_low", "penalty_high"))
    text = f"{penalty:.2f} [{low:.2f}; {high:.2f}]"
    if nominal_rate:
        text += f" / x{float(row['rate_tuned']) / nominal_rate:.1f}"
    return text


def table(rows: list[dict]) -> str:
    """Un tableau par (d, rounds, p, base) ; la dernière ligne lue gagne en cas de doublon."""
    groups: dict[tuple, dict[tuple[str, str], dict]] = defaultdict(dict)
    for row in rows:
        groups[key(row)][(row["scenario"], row["decoder"])] = row
    out = []
    for (d, r, p, basis), cells in sorted(groups.items()):
        decoders = sorted({dec for _, dec in cells}, key=lambda n: (n != "pymatching", n))
        scenarios = list(dict.fromkeys(s for s, _ in cells))
        nominal = {dec: float(row["rate_tuned"]) for (s, dec), row in cells.items() if s == "nominal" and row["status"] == "ok"}
        out.append(f"### d = {d}, {r} rounds, p = {p:g}, mémoire {basis.upper()}\n")
        out.append("| scénario | " + " | ".join(decoders) + " |")
        out.append("|---|" + "---|" * len(decoders))
        for scenario in scenarios:
            values = [cell_text(cells[(scenario, dec)], nominal.get(dec)) if (scenario, dec) in cells else "" for dec in decoders]
            out.append(f"| {scenario} | " + " | ".join(values) + " |")
        out.append("")
    return "\n".join(out)


def latency_table(rows: list[dict]) -> str:
    out = ["| décodeur | scénario | plancher µs | p50 µs | p99 µs | p99,9 µs | max µs | p50 / round | max / round |", "|---|---|---|---|---|---|---|---|---|"]
    for row in rows:
        rounds = int(row["rounds"])
        values = [float(row[k]) for k in ("floor_us", "p50_us", "p99_us", "p999_us", "max_us")]
        out.append(f"| {row['decoder']} | {row['scenario']} | " + " | ".join(f"{v:,.0f}".replace(",", " ") for v in values)
                   + f" | {values[1] / rounds:,.0f} | {values[4] / rounds:,.0f} |".replace(",", " "))
    return "\n".join(out)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Tableaux Markdown des résultats de la brique 2.")
    parser.add_argument("mismatch", type=Path, nargs="*")
    parser.add_argument("--latency", type=Path, nargs="*", default=[])
    args = parser.parse_args(argv)
    if args.mismatch:
        print(table(load(args.mismatch)))
    if args.latency:
        print(latency_table(load(args.latency)))


if __name__ == "__main__":
    main()
