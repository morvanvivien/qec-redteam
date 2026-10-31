# Proposition de test pour PyMatching (prête, non envoyée)

À utiliser seulement si PyMatching répond oui à l'issue oscarhiggott/PyMatching#187, après lecture de ses règles de contribution.

- `robustness_test.py` : le fichier à ajouter dans leur dépôt, sous `tests/matching/`. Trois tests, moins d'une seconde, PyMatching 2.4.0 passe.
- `PR_DESCRIPTION.md` : le texte de la demande de fusion (titre en première ligne).

Vérifier : `.venv/bin/python -m pytest -q contrib/pymatching-pr/robustness_test.py`

Pour l'envoyer, il faudra une copie (fork) de PyMatching.
