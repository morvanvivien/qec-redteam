# Profil de robustesse sur le gross code d'IBM (mode « gross », ajouté au profil v0.1)

En bref :
1. Sur le code qu'IBM veut utiliser, seuls deux décodeurs publics vont au bout des épreuves en temps raisonnable : relay-bp (IBM) et BP+LSD (ldpc).
2. BP+LSD réussit les deux épreuves.
3. relay-bp tient (pas de plantage) mais échoue à la cohérence : avec la vraie carte d'une ancilla devenue aléatoire, il se trompe 14 fois sur 60, contre 0 sans cette carte. C'est le défaut des probabilités de 1/2 déjà signalé à IBM (#43).
4. Les autres sont bien trop lents pour ce code : de 20 secondes à plus de 20 minutes par décodage, quand une machine en demande moins d'une milliseconde.
5. Les décodeurs de couplage (PyMatching, fusion-blossom, beliefmatching) ne s'appliquent pas : le modèle d'erreurs de ce code n'est pas un graphe.

Gross code [[144, 12, 12]], circuit d'IBM (third_party/relay_bp), mémoire Z, 12 rounds, bruit uniforme p = 0,003 ; épreuve saturée : la première ancilla rendue complètement aléatoire au round 6. E1 sur 20 tirs, E2 sur 60 tirs, graine 20261001.

| Décodeur | E1 Tenue | E2 Cohérence | Temps par décodage | Détail |
|---|---|---|---|---|
| relay-bp 0.2.2 | réussie | **échouée** | ~1 s (11 s avec la vraie carte) | informé 14 erreurs / 60, réglé 0 |
| BP+LSD (ldpc 2.4.1, lsd_0) | réussie | réussie | quelques secondes | informé 1 / 60, réglé 2 / 60 |
| BP+OSD (ldpc 2.4.1, OSD-CS ordre 10) | délai | délai | E1 non terminée en 40 min | ordre 10 trop coûteux sur 8 000 colonnes |
| stimbposd 0.2.0 | délai | délai | 27 s par tir (nominal) | |
| tesseract 0.1.1.dev | délai | délai | 20 à 100 s par tir | |
| mwpf 0.2.12 | délai | délai | 3 tirs non terminés en 20 min | |
| PyMatching, fusion-blossom, beliefmatching | non applicable | non applicable | — | modèle non décomposable en graphe |

« Délai » veut dire : épreuve non terminée dans le temps imparti, ce qui est en soi une information sur ce code, pas un défaut.

Rejouer : `.venv/bin/python -m redteam.profil relay-bp bplsd --mode gross --out research/profil-gross` ; temps : `research/profil-gross/latence_gross.py <décodeur>`.
