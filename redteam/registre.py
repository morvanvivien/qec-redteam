"""Registre de tout ce que la red team a trouvé, écarté ou laissé ouvert.

Source unique : docs/registre.json. Ce module le vérifie (champs, catégories,
identifiants uniques, preuves présentes dans le dépôt) et en tire
docs/registre.md. Les faux positifs et nos propres erreurs de méthode y sont
au même titre que les défauts : c'est ce qui rend le reste crédible.

    python -m redteam.registre            # vérifie et réécrit docs/registre.md
    python -m redteam.registre --check    # vérifie seulement
"""

import argparse
import json
import re
import subprocess
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "registre.json"
PAGE = ROOT / "docs" / "registre.md"
REQUIRED = ("id", "date", "cible", "version", "categorie", "titre", "constat", "preuves", "rejeu", "signalement")
ID_PATTERN = re.compile(r"^QEC-\d{4}-\d{3}$")
ORDER = ("defaut_confirme", "defaut_connu_cause_trouvee", "choix_documente", "profil", "tient", "piste_ouverte", "faux_positif", "erreur_de_methode")
LABELS = {
    "defaut_confirme": "Défauts confirmés",
    "defaut_connu_cause_trouvee": "Défauts connus, cause trouvée par nous",
    "choix_documente": "Choix documentés par l'auteur",
    "profil": "Profils mesurés (pas des défauts)",
    "tient": "Ce qui tient",
    "piste_ouverte": "Pistes ouvertes",
    "faux_positif": "Faux positifs et pistes écartées",
    "erreur_de_methode": "Nos erreurs de méthode, corrigées avant publication",
}


def load(path: Path = SOURCE) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def ignored_by_git(paths: list[str], root: Path = ROOT) -> set[str]:
    """Preuves que git ignorerait : présentes sur le disque, absentes du dépôt.

    Leçon du 12/10 (QEC-2026-021) : six journaux `.log` cités comme preuves
    existaient sur le conteneur de calcul, mais `*.log` est ignoré, et ils
    n'ont jamais été commités. Sans git, rien n'est signalé.
    """
    if not paths:
        return set()
    # Mode binaire et séparateur NUL : en mode texte, Windows réécrit les fins de ligne et git cite les chemins.
    try:
        done = subprocess.run(["git", "check-ignore", "--stdin", "-z"], cwd=root, input="\0".join(paths).encode("utf-8"), capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return set()
    return {part.decode("utf-8") for part in done.stdout.split(b"\0") if part}


def validate(registre: dict, root: Path = ROOT) -> list[str]:
    """Liste des problèmes ; vide si le registre est cohérent."""
    problems = []
    ignored = ignored_by_git(sorted({p for e in registre.get("entrees", []) for p in e.get("preuves", [])}), root)
    categories = registre.get("categories", {})
    if set(categories) != set(ORDER):
        problems.append(f"catégories attendues {sorted(ORDER)}, trouvées {sorted(categories)}")
    seen = set()
    for entry in registre.get("entrees", []):
        ident = entry.get("id", "?")
        for key in REQUIRED:
            if key not in entry:
                problems.append(f"{ident} : champ {key} manquant")
        if not ID_PATTERN.match(ident):
            problems.append(f"{ident} : identifiant mal formé")
        if ident in seen:
            problems.append(f"{ident} : identifiant en double")
        seen.add(ident)
        if entry.get("categorie") not in categories:
            problems.append(f"{ident} : catégorie inconnue {entry.get('categorie')!r}")
        try:
            date.fromisoformat(entry.get("date", ""))
        except ValueError:
            problems.append(f"{ident} : date non ISO {entry.get('date')!r}")
        if not entry.get("preuves"):
            problems.append(f"{ident} : aucune preuve")
        for proof in entry.get("preuves", []):
            if not (root / proof).exists():
                problems.append(f"{ident} : preuve absente du dépôt, {proof}")
            elif proof in ignored:
                problems.append(f"{ident} : preuve ignorée par git, elle ne sera jamais versionnée, {proof}")
        report = entry.get("signalement")
        if report is not None and not report.get("lien", "").startswith("https://"):
            problems.append(f"{ident} : signalement sans lien")
        if entry.get("categorie") == "defaut_confirme" and not entry.get("rejeu"):
            problems.append(f"{ident} : un défaut confirmé doit avoir une commande de rejeu")
    return problems


def render(registre: dict) -> str:
    entries = registre["entrees"]
    counts = {key: sum(1 for e in entries if e["categorie"] == key) for key in ORDER}
    out = [
        "# Registre de la red team QEC",
        "",
        f"Mis à jour le {registre['mis_a_jour']}. Généré par `python -m redteam.registre` depuis [registre.json](registre.json) ; ne pas éditer à la main.",
        "",
        "Tout ce que nous avons examiné y figure, y compris ce qui s'est révélé faux et nos propres erreurs. Chaque entrée renvoie à ses preuves dans ce dépôt et, quand c'est possible, à la commande qui la rejoue.",
        "",
        "| Catégorie | Nombre | Définition |",
        "|---|---|---|",
    ]
    out += [f"| {LABELS[key]} | {counts[key]} | {registre['categories'][key]} |" for key in ORDER]
    out.append("")
    for key in ORDER:
        group = [e for e in entries if e["categorie"] == key]
        if not group:
            continue
        out += [f"## {LABELS[key]}", ""]
        for e in group:
            out.append(f"### {e['id']} — {e['titre']}")
            out.append("")
            out.append(f"- **Cible :** {e['cible']} ({e['version']})")
            out.append(f"- **Date :** {e['date']}")
            out.append(f"- **Constat :** {e['constat']}")
            out.append("- **Preuves :** " + ", ".join(f"[{Path(p).name}]({Path(p).relative_to('docs').as_posix() if p.startswith('docs/') else '../' + p})" for p in e["preuves"]))
            if e["rejeu"]:
                out.append(f"- **Rejouer :** `{e['rejeu']}`")
            report = e["signalement"]
            if report:
                out.append(f"- **Signalé :** {report['date'] or 'non'} — {report['lien']} — {report['statut']}")
            out.append("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Vérifie le registre et réécrit sa page.")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    registre = load()
    problems = validate(registre)
    for problem in problems:
        print(f"PROBLÈME {problem}")
    if problems:
        raise SystemExit(1)
    if not args.check:
        PAGE.write_text(render(registre) + "\n", encoding="utf-8")
    print(f"registre cohérent : {len(registre['entrees'])} entrées")


if __name__ == "__main__":
    main()
