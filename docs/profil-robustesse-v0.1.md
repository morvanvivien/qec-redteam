# Profil de robustesse QEC — version 0.1

<img src="logo/profil-robustesse.svg" alt="Logo : écusson avec une grille de qubits dont un est en défaut, mention QEC, profil de robustesse, v0.1" width="160">

Version du 30 septembre 2026. Code : `redteam/profil.py`. Registre des résultats : [registre.md](registre.md).

## En une phrase

Un décodeur quantique est réglé sur une « carte » des erreurs de la machine. Le profil mesure ce qu'il devient quand la vraie machine s'écarte de la carte (une pièce qui chauffe, une pièce qui décroche, deux pièces voisines qui se parasitent), et s'il tient debout quand on lui donne une carte exacte mais difficile.

## Pourquoi un profil et pas une homologation

Attester officiellement qu'un produit est conforme est une activité encadrée par le Code de la consommation : l'organisme qui le fait doit être accrédité (en France par le COFRAC, selon la norme ISO/IEC 17065), et employer le terme réservé sans cette accréditation serait une pratique commerciale trompeuse. D'où la règle du plan : ce terme n'est jamais employé avant un standard adopté. Le profil décrit ; il n'homologue pas.

Le chemin vers une attestation officielle existe et il suit le plan :

1. **Aujourd'hui :** un profil public, reproductible, que n'importe qui peut relancer.
2. **Brique 3 :** faire adopter la suite par une bibliothèque (PyMatching ou Fusion Blossom), dans ses tests automatiques. Le profil devient une référence de fait.
3. **Brique 4 :** siéger au comité miroir AFNOR de l'ISO/IEC JTC 3 (informatique quantique), où se préparent les normes d'évaluation.
4. **Plus tard :** quand une norme existe, se faire accréditer comme organisme évaluateur, ou s'adosser à un organisme accrédité.

Ce qui se vend dès maintenant : un audit indépendant avec rapport de profil, pour un fonds qui investit dans un constructeur ou pour un constructeur qui choisit un décodeur.

## Les cinq épreuves

Chaque épreuve fixe son code, son bruit, sa graine (20261001) et son nombre de tirs. Deux personnes qui lancent la même version du profil sur la même version du décodeur obtiennent les mêmes chiffres.

| Épreuve | Question posée | Comment | Résultat |
|---|---|---|---|
| **E1 Tenue** | Le décodeur fonctionne-t-il sur des entrées valides mais difficiles ? | Code de surface d = 3. Décoder sous bruit nominal ; décoder un modèle d'erreurs où une ancilla est complètement aléatoire pendant un round ; vérifier qu'un syndrome nul donne une prédiction nulle ; décoder deux fois les mêmes tirs. | réussie ou échouée |
| **E2 Cohérence** | Donner au décodeur la vraie carte l'aide-t-il, ou lui nuit-il ? | Même fuite, 4 000 tirs. Le décodeur informé de la fuite ne doit pas se tromper significativement plus que le décodeur qui l'ignore (borne basse de l'intervalle à 95 % du rapport informé / réglé ≤ 1). | réussie ou échouée |
| **E3 Désaccord** | Combien coûte une carte périmée ? | d = 5, p = 0,002. Pénalité réglé / informé sous trois bruits réels : ancilla chaude ×100, fuite d'ancilla tirée au sort, diaphonie ZZ à 3p. | note A à D sur la pire pénalité (A ≤ 1,5 ; B ≤ 2,5 ; C ≤ 4 ; D au-delà) |
| **E4 Classement** | Le décodeur garde-t-il son rang face à la référence ? | d = 5. Taux d'erreur rapporté à celui de PyMatching sur les mêmes 20 000 tirs, sous bruit nominal puis sous diaphonie ZZ. | note sur le glissement (A ≤ ×1,1 ; B ≤ ×1,5 ; C ≤ ×2,5 ; D au-delà) |
| **E5 Latence** | Le décodeur reste-t-il rapide quand le bruit empire ? | d = 5. Chaque tir chronométré seul : p50, p99, max, sous bruit nominal et sous « tout ×3 ». | note sur p99 perturbé / p99 nominal (A ≤ 2 ; B ≤ 5 ; C ≤ 20 ; D au-delà) |

**Mode rapide** : E1 et E2 seulement, quelques secondes par décodeur. C'est la partie destinée aux tests automatiques d'une bibliothèque : elle échoue si le décodeur plante ou si la vraie carte lui nuit.

**Mode complet** : les cinq épreuves, de quelques minutes (PyMatching) à plusieurs heures (tesseract, mwpf).

## Comment le lancer

```
.venv/bin/pip install -r requirements-decoders.txt
.venv/bin/python -m redteam.profil pymatching --mode rapide
.venv/bin/python -m redteam.profil tesseract --mode complet --out docs/profils
```

Chaque profil produit une fiche Markdown, un fichier JSON avec toutes les mesures, et un badge SVG vert (tenue réussie) ou rouge (tenue échouée).

## Ce que le profil ne dit pas

- Il ne dit pas qu'un décodeur est « bon » ou « mauvais » dans l'absolu : une note D en latence n'a pas d'importance pour un décodage hors ligne.
- Il ne couvre que le code de surface et les bruits listés ici. Les codes qLDPC (gross code d'IBM) viendront en v0.2.
- Il ne remplace pas la lecture de la documentation du décodeur : une réponse inhabituelle est d'abord une question posée à son auteur.
- Il ne vaut que pour la version testée, écrite dans le fichier JSON.

## Règles de publication d'un profil

1. Tout résultat publié est rejoué depuis zéro avec la graine du profil.
2. Un défaut trouvé est signalé au mainteneur avant toute publication, et entre au [registre](registre.md) avec sa preuve.
3. Les faux positifs et nos propres erreurs entrent aussi au registre.
4. Le logo n'est apposé que sur un profil complet, rejoué, publié avec ses données.
