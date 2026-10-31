"""Le registre du dépôt est cohérent et sa page est à jour."""

import copy
import re

from redteam.registre import PAGE, load, render, validate


def test_le_registre_du_depot_est_coherent():
    assert validate(load()) == []


def test_la_page_publiee_correspond_au_registre():
    assert PAGE.read_text(encoding="utf-8") == render(load()) + "\n"


def test_les_liens_de_la_page_marchent_sur_tous_les_systemes():
    registre = load()
    assert any(p.startswith("docs/") and p.count("/") > 1 for e in registre["entrees"] for p in e["preuves"]), "il faut une preuve dans un sous-dossier de docs/"
    liens = re.findall(r"\]\(([^)]+)\)", render(registre))
    assert liens and not [lien for lien in liens if "\\" in lien]


def test_les_problemes_sont_detectes():
    registre = copy.deepcopy(load())
    bad = registre["entrees"][0]
    bad["categorie"] = "inconnue"
    bad["preuves"] = ["docs/absent.md"]
    registre["entrees"].append(copy.deepcopy(registre["entrees"][1]))
    problems = validate(registre)
    assert any("catégorie inconnue" in p for p in problems)
    assert any("preuve absente" in p for p in problems)
    assert any("en double" in p for p in problems)


def test_une_preuve_ignoree_par_git_est_refusee():
    from redteam.registre import ROOT

    ignored = ROOT / "out" / "preuve-fantome.log"  # out/ et *.log sont ignorés par git
    ignored.parent.mkdir(exist_ok=True)
    ignored.write_text("", encoding="utf-8")
    try:
        registre = copy.deepcopy(load())
        registre["entrees"][0]["preuves"] = ["out/preuve-fantome.log"]
        assert any("ignorée par git" in p for p in validate(registre))
    finally:
        ignored.unlink()


def test_un_defaut_confirme_sans_rejeu_est_refuse():
    registre = copy.deepcopy(load())
    entry = next(e for e in registre["entrees"] if e["categorie"] == "defaut_confirme")
    entry["rejeu"] = None
    assert any("rejeu" in p for p in validate(registre))


def test_la_page_montre_aussi_les_faux_positifs():
    text = render(load())
    assert "## Faux positifs et pistes écartées" in text
    assert "## Nos erreurs de méthode" in text
