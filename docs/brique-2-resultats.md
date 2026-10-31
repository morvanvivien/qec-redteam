# Brique 2 — résultats au fil de l'eau

1. **Ce qui casse :** relay-bp (IBM) casse deux fois devant un qubit devenu aléatoire (fuite, rafale). Son module stim/sinter lève une exception à chaque décodage (constat 003, rejoué sur 6 graines). Et son cœur de calcul, dès qu'une probabilité vaut exactement 1/2, rend des corrections qui ne respectent même pas le syndrome, après des milliers d'itérations. Les deux défauts sont présents sur PyPI 0.2.2 et sur la branche principale. Sur le code principal d'IBM (gross code), le second fait échouer 150 décodages informés sur 150, avec 49 % d'erreurs, contre 0 % en plafonnant les probabilités.
2. **Ce qui renverse le classement, confirmé :** sous diaphonie ZZ entre portes voisines (3p), tesseract passe de 0,62 fois les erreurs de PyMatching à 1,29 à 1,53 fois, et mwpf de 0,76 à 2,4 à 2,9 fois, sur 3 graines indépendantes et en duel apparié (même tirs). Même chose en miroir, XX en mémoire X. Répliqué le 13/10 sur une autre machine pour mwpf (0,65–0,76 → 2,5–3,0, 3 graines) ; absent à d = 3 (3 graines), plus fort à d = 7.
3. **Ce qui tient :** aucun décodeur ne s'effondre sous un mauvais réglage homogène, une dérive ou un coupleur chaud (pénalité ≤ 1,6). PyMatching tient aussi en latence (p99 < 61 µs partout) ; tesseract et mwpf, non : leur p99 monte à 0,4–0,65 s sous bruit perturbé, avec des tirs à près de 2 s pour tesseract.
4. **Ce qui coûte à tous :** un qubit chaud, une fuite ou une rafale non annoncés coûtent ×2 à ×3,7 à tous les décodeurs. C'est le prix d'une calibration périmée, pas un défaut d'un décodeur en particulier.
5. **Piste la plus prometteuse :** relay-bp, avec un correctif d'un caractère dans son cœur Rust, déjà compilé et vérifié (sorties identiques sur 300 problèmes sans probabilité 1/2), proposé depuis au mainteneur (trmue/relay#43). Ensuite, le renversement de classement sous diaphonie, cœur d'un « profil de robustesse ».

État : **partiel**, mis à jour le 12/10/2026. Rien n'est publié hors de ce dépôt.

## Protocole

- Code de surface tourné, mémoire Z, d = 5, 5 rounds, SI1000 à p = 0,002 (`redteam.mismatch`).
- **Réglé** : décodeur construit sur le DEM du circuit nominal. **Informé** : décodeur construit sur le DEM du vrai circuit de chaque tir ; pour un événement tiré au hasard (fuite, rafale), il sait où et quand l'événement a eu lieu.
- Mêmes tirs pour les deux, graine 20260929, arrêt à 200 erreurs (100 pour les décodeurs lents) ou au plafond de tirs.
- **Pénalité** = taux réglé / taux informé, intervalle à 95 % par bootstrap apparié sur les quatre cases (réglé juste ou faux × informé juste ou faux).
- **Dégradation** = taux réglé sous bruit réel / taux du même décodeur sous bruit nominal (ligne « nominal »).
- Événements (fuite, rafale) : taux **conditionnel** à l'événement. Fuite approchée : le qubit est poussé au mélange complet pendant 1 ou 2 rounds (dépolarisation 3/4, 15/16 sur ses portes, mesure au hasard).
- Chaque cellule tourne dans son propre processus : un plantage donne une ligne, pas un banc mort.

Versions : stim 1.16.0, PyMatching 2.4.0, fusion-blossom 0.2.13, ldpc 2.4.1, stimbposd 0.2.0, beliefmatching 0.2.0, relay-bp 0.2.2, tesseract-decoder 0.1.1.dev20260822020007, mwpf 0.2.12 (Linux, Python 3.11.15, 4 cœurs).

Réglages : ceux de decoder-bench quand il teste la bibliothèque (ldpc : min-sum, 100 itérations ; relay-bp : gamma0 0,1, 80 pré-itérations, 60 jeux de 60 ; mwpf : limite de cluster 50), sinon les défauts de l'auteur. BP+OSD : osd_cs d'ordre 10, refusé si l'ordre n'est pas strictement inférieur à k ; BP+LSD : lsd_0, ordre 0 (constat 002, ldpc #105). stimbposd : défauts de l'auteur (osd_cs d'ordre 60, avec le même garde-fou).

## Pénalité de réglage [IC 95 %] / dégradation

Lecture : « 2.61 [2.17; 3.22] / x27.9 » = le décodeur réglé sur le nominal se trompe 2,61 fois plus que le même décodeur informé, et 27,9 fois plus que sous bruit nominal.

### d = 5, 5 rounds, p = 0.002, mémoire Z

| scénario | pymatching | beliefmatching | bplsd | bposd | fusion-blossom | mwpf | relay-bp | stimbposd | tesseract |
|---|---|---|---|---|---|---|---|---|---|
| nominal | 1.00 [1.00; 1.00] / x1.0 | 1.00 [1.00; 1.00] / x1.0 | 1.00 [1.00; 1.00] / x1.0 | 1.00 [1.00; 1.00] / x1.0 | 1.00 [1.00; 1.00] / x1.0 | 1.00 [1.00; 1.00] / x1.0 | 1.00 [1.00; 1.00] / x1.0 | 1.00 [1.00; 1.00] / x1.0 | 1.00 [1.00; 1.00] / x1.0 |
| tout x3 | 0.98 [0.95; 1.02] / x20.9 | 1.00 [0.94; 1.06] / x21.5 | 1.24 [1.09; 1.41] / x14.0 | 1.04 [0.96; 1.14] / x19.7 | 1.01 [0.98; 1.05] / x21.5 | 1.03 [0.92; 1.14] / x23.6 | 1.05 [0.98; 1.12] / x18.4 | 1.02 [0.92; 1.13] / x21.3 | 1.01 [0.93; 1.10] / x21.8 |
| donnée chaude x100 | 1.78 [1.50; 2.12] / x12.4 | 2.22 [1.92; 2.61] / x16.3 | 3.00 [2.43; 3.83] / x15.1 | 2.50 [2.10; 3.06] / x15.9 | 1.78 [1.51; 2.13] / x12.1 | 1.48 [1.28; 1.73] / x13.4 | 1.78 [1.51; 2.12] / x11.0 | 2.19 [1.82; 2.69] / x16.3 | 2.00 [1.64; 2.49] / x13.6 |
| ancilla chaude x100 | 2.61 [2.17; 3.22] / x27.9 | 3.10 [2.51; 3.96] / x32.1 | 3.03 [2.52; 3.72] / x20.3 | 3.72 [3.01; 4.77] / x30.5 | 2.03 [1.72; 2.43] / x26.8 | 2.01 [1.66; 2.49] / x25.3 | 2.25 [1.88; 2.74] / x22.8 | 3.27 [2.61; 4.25] / x33.5 | 2.77 [2.21; 3.60] / x29.5 |
| coupleur chaud x100 | 1.51 [1.33; 1.73] / x3.1 | 1.63 [1.44; 1.87] / x3.2 | 1.92 [1.60; 2.32] / x2.9 | 1.93 [1.65; 2.28] / x3.2 | 1.29 [1.16; 1.45] / x2.9 | 1.22 [1.03; 1.44] / x2.8 | 1.49 [1.30; 1.72] / x2.7 | 1.58 [1.32; 1.94] / x2.7 | 1.40 [1.21; 1.63] / x2.6 |
| diaphonie ZZ 3p | 1.00 [1.00; 1.00] / x1.2 | 1.38 [1.24; 1.56] / x1.9 | 1.85 [1.56; 2.21] / x3.0 | 1.99 [1.68; 2.40] / x2.8 | 1.00 [1.00; 1.00] / x1.3 | 1.94 [1.58; 2.48] / x5.3 | 1.02 [0.93; 1.13] / x1.1 | 1.88 [1.53; 2.38] / x2.6 | 1.96 [1.58; 2.53] / x2.6 |
| fuite ancilla 1r | 3.21 [2.60; 4.09] / x8.4 | 2.86 [2.33; 3.62] / x7.8 | 2.43 [2.04; 2.94] / x6.0 | 3.53 [2.83; 4.58] / x8.7 | 3.11 [2.54; 3.94] / x8.8 | 2.83 [2.11; 4.04] / x7.9 | **exception** | 3.58 [2.70; 5.09] / x9.7 | 3.29 [2.48; 4.70] / x9.8 |
| rafale 0.5 | 2.84 [2.42; 3.39] / x18.3 | 2.56 [2.18; 3.06] / x20.1 | 3.05 [2.47; 3.87] / x14.4 | 2.99 [2.54; 3.59] / x19.9 | 2.35 [2.04; 2.74] / x18.7 | 2.21 [1.73; 2.92] / x16.5 | **exception** | 3.11 [2.45; 4.16] / x23.1 | 2.84 [2.23; 3.79] / x21.3 |
| mesure x6 | 1.17 [1.08; 1.27] / x17.0 | 1.27 [1.17; 1.39] / x23.3 | 1.56 [1.36; 1.81] / x12.8 | 1.32 [1.21; 1.45] / x18.7 | 0.95 [0.88; 1.03] / x15.4 |  | 1.23 [1.12; 1.35] / x14.7 |  |  |
| attente x10 | 1.18 [1.06; 1.32] / x27.1 | 1.29 [1.19; 1.40] / x32.1 | 1.36 [1.20; 1.55] / x18.7 | 1.35 [1.18; 1.54] / x26.7 | 1.22 [1.10; 1.37] / x30.3 |  | 1.23 [1.10; 1.38] / x24.0 |  |  |
| donnée chaude x10 | 1.17 [1.07; 1.29] / x2.2 | 1.24 [1.12; 1.38] / x2.3 | 1.36 [1.16; 1.59] / x2.2 | 1.14 [1.00; 1.29] / x2.0 | 1.20 [1.11; 1.31] / x2.3 |  | 1.30 [1.16; 1.46] / x2.1 |  |  |
| ancilla chaude x10 | 1.24 [1.12; 1.39] / x2.5 | 1.44 [1.28; 1.63] / x2.6 | 1.24 [1.06; 1.45] / x2.1 | 1.20 [1.04; 1.38] / x2.2 | 1.09 [0.99; 1.22] / x2.4 |  | 1.12 [0.99; 1.28] / x2.1 |  |  |
| coupleur chaud x10 | 1.02 [0.97; 1.07] / x1.1 | 0.99 [0.93; 1.04] / x1.1 | 1.00 [0.90; 1.13] / x1.2 | 1.00 [0.90; 1.10] / x1.0 | 1.00 [0.95; 1.06] / x1.0 |  | 1.06 [0.97; 1.16] / x0.9 |  |  |
| donnée chaude x30 | 1.71 [1.48; 2.01] / x5.8 | 1.81 [1.56; 2.14] / x6.4 | 2.48 [2.09; 3.02] / x5.7 | 1.87 [1.59; 2.21] / x6.6 | 1.53 [1.35; 1.77] / x5.9 |  | 1.53 [1.33; 1.78] / x5.0 |  |  |
| ancilla chaude x30 | 2.14 [1.86; 2.50] / x11.2 | 2.36 [2.02; 2.81] / x13.1 | 2.14 [1.81; 2.58] / x8.1 | 2.17 [1.86; 2.57] / x10.4 | 1.94 [1.70; 2.25] / x11.0 |  | 1.94 [1.63; 2.36] / x9.5 |  |  |
| coupleur chaud x30 | 1.11 [1.02; 1.21] / x1.7 | 1.27 [1.16; 1.41] / x1.7 | 1.25 [1.07; 1.45] / x1.6 | 1.16 [1.04; 1.31] / x1.5 | 1.05 [0.97; 1.13] / x1.7 |  | 1.06 [0.95; 1.18] / x1.5 |  |  |
| diaphonie ZZ 1p | 1.00 [1.00; 1.00] / x1.0 | 1.04 [0.96; 1.13] / x1.1 | 1.13 [0.96; 1.32] / x1.4 | 1.37 [1.18; 1.60] / x1.5 | 1.00 [1.00; 1.00] / x1.1 |  | 1.02 [0.94; 1.12] / x0.9 |  |  |
| diaphonie XX 1p | 1.36 [1.24; 1.49] / x20.5 | 1.44 [1.30; 1.60] / x26.1 | 1.20 [1.08; 1.34] / x12.0 | 1.37 [1.23; 1.53] / x20.1 | 1.16 [1.05; 1.28] / x19.8 |  | 1.22 [1.11; 1.35] / x16.7 |  |  |
| diaphonie XX 3p | 1.20 [1.11; 1.29] / x65.4 | 1.32 [1.22; 1.43] / x91.0 | 1.10 [1.01; 1.19] / x37.3 | 1.22 [1.12; 1.32] / x68.1 | 0.98 [0.90; 1.06] / x66.6 |  | 1.18 [1.10; 1.27] / x55.7 |  |  |
| fuite donnée 1r | 2.09 [1.79; 2.47] / x3.6 | 2.04 [1.73; 2.44] / x3.9 | 2.06 [1.71; 2.52] / x3.4 | 2.50 [2.07; 3.09] / x4.1 | 1.92 [1.65; 2.27] / x3.5 |  | **exception** |  |  |
| fuite donnée 2r | 2.35 [1.96; 2.88] / x4.6 | 2.18 [1.84; 2.60] / x5.1 | 2.45 [2.04; 3.01] / x5.1 | 2.97 [2.42; 3.75] / x5.2 | 2.15 [1.83; 2.56] / x4.7 |  | **exception** |  |  |
| fuite ancilla 2r | 3.44 [2.82; 4.30] / x10.5 | 2.81 [2.36; 3.43] / x10.3 | 2.93 [2.42; 3.62] / x8.9 | 3.64 [2.95; 4.62] / x10.7 | 2.82 [2.36; 3.44] / x10.6 |  | **exception** |  |  |
| fuite donnée centrale | 2.16 [1.82; 2.62] / x5.8 | 2.88 [2.36; 3.62] / x6.8 | 2.95 [2.38; 3.75] / x7.4 | 2.89 [2.38; 3.58] / x7.5 | 2.11 [1.78; 2.57] / x6.0 |  | **exception** |  |  |
| dérive x3 | 1.00 [0.96; 1.03] / x10.2 | 1.04 [0.98; 1.10] / x11.4 | 1.04 [0.93; 1.15] / x7.3 | 1.02 [0.94; 1.10] / x10.5 | 0.99 [0.94; 1.03] / x10.5 |  | 1.01 [0.94; 1.09] / x9.0 |  |  |
| dérive x10 | 0.99 [0.95; 1.04] / x75.1 | 1.03 [0.98; 1.08] / x100.9 | 1.01 [0.95; 1.08] / x45.7 | 1.01 [0.95; 1.07] / x81.3 | 0.94 [0.91; 0.98] / x78.4 |  | 1.03 [0.98; 1.09] / x65.6 |  |  |
| rafale 0.1 | 1.60 [1.41; 1.84] / x4.8 | 1.58 [1.40; 1.79] / x5.1 | 1.61 [1.39; 1.88] / x3.9 | 1.88 [1.60; 2.24] / x4.9 | 1.39 [1.25; 1.55] / x5.0 |  | 1.46 [1.28; 1.68] / x4.0 |  |  |


Données : [docs/brique-2/](brique-2/). Décodeurs lents (stimbposd, mwpf, tesseract) : 8 scénarios, arrêt à 100 erreurs. Case vide = non mesuré.

## Duels appariés : renversement de classement sous diaphonie

`redteam.duel` : tous les décodeurs réglés sur le nominal décodent **les mêmes** 40 000 tirs ; rapport des taux d'erreur au taux de PyMatching, intervalle apparié à 95 %, test de McNemar. d = 5, p = 0,002.

| Bruit réel | Mémoire | Graine | tesseract / PyMatching | mwpf / PyMatching | BP+OSD / PyMatching | stimbposd / PyMatching |
|---|---|---|---|---|---|---|
| nominal | Z | 31 | **0,70** [0,60; 0,81] | 0,76 [0,66; 0,88] | 1,07 [0,93; 1,23] | 0,75 [0,65; 0,87] |
| nominal | Z | 32 | **0,62** [0,52; 0,72] | 0,76 [0,64; 0,88] | 1,03 [0,88; 1,20] | 0,68 [0,58; 0,79] |
| nominal | X | 33 | **0,62** [0,54; 0,71] | 0,69 [0,60; 0,78] | 0,91 [0,79; 1,05] | 0,64 [0,55; 0,73] |
| diaphonie ZZ 1p | Z | 31 | 0,91 [0,79; 1,04] | 1,30 [1,13; 1,49] | 1,24 [1,08; 1,43] | 0,98 [0,86; 1,12] |
| diaphonie ZZ 3p | Z | 31 | **1,29** [1,13; 1,48] | 2,42 [2,11; 2,81] | 2,21 [1,94; 2,55] | 1,45 [1,27; 1,66] |
| diaphonie ZZ 3p | Z | 32 | **1,53** [1,34; 1,76] | 2,90 [2,52; 3,36] | 2,26 [1,97; 2,63] | 1,65 [1,44; 1,90] |
| diaphonie XX 3p | X | 33 | **1,45** [1,26; 1,68] | 2,67 [2,31; 3,10] | 2,47 [2,14; 2,87] | 1,60 [1,39; 1,86] |

À ZZ 3p, graine 31, les autres : beliefmatching 1,13 [1,00; 1,28], relay-bp 1,11 [1,02; 1,21], fusion-blossom 0,99 [0,92; 1,07].

Effet de la distance (duels, mémoire Z) :

| d | p | Graine | Tirs | tesseract / PyMatching, nominal | tesseract / PyMatching, ZZ 3p | mwpf / PyMatching, nominal | mwpf / PyMatching, ZZ 3p |
|---|---|---|---|---|---|---|---|
| 3 | 0,002 | 41 (42, 43 sans tesseract) | 60 000 | 0,85 [0,80; 0,89] | 1,01 [0,95; 1,07] | 0,81 à 0,85 | 1,00 à 1,05 |
| 5 | 0,002 | 31, 32 (33 sans tesseract) | 40 000 | 0,62 à 0,70 | **1,29 à 1,53** | 0,65 à 0,76 | **2,42 à 3,02** |
| 7 | 0,003 | 42 | 10 000 (nominal), 3 000 (diaphonie) | 0,35 [0,23; 0,48] | **2,00** [1,40; 3,04] | non mesuré | non mesuré |

L'avantage de tesseract sous bruit nominal grandit avec la distance (0,85 à d = 3, 0,35 à d = 7), et la diaphonie ZZ le renverse d'autant plus fort : effacé à d = 3, ×1,3 à 1,5 à d = 5, ×2,0 à d = 7.

Série d = 3 fermée le 12/10 sur trois graines (41, 42, 43), 60 000 tirs appariés chacune, p = 0,002, mémoire Z, sept décodeurs sur le poste Windows (tesseract et relay-bp n'y sont pas installables : voir les fichiers `-linux` pour tesseract). Rapport au taux de PyMatching [IC 95 %] ; fichiers `research/duel-d3/results-d3-s4*-windows.txt`.

| Graine | Bruit réel | PyMatching (erreurs) | mwpf | BP+OSD | stimbposd | BP+LSD | beliefmatching | fusion-blossom |
|---|---|---|---|---|---|---|---|---|
| 41 | nominal | 648 | 0,85 [0,80 ; 0,90] | 1,01 [0,96 ; 1,07] | 0,90 [0,86 ; 0,94] | 1,32 [1,25 ; 1,41] | 0,92 [0,88 ; 0,96] | 1,00 [0,97 ; 1,04] |
| 41 | ZZ 3p | 661 | 1,01 [0,95 ; 1,06] | 1,20 [1,14 ; 1,27] | 1,04 [0,98 ; 1,09] | 1,68 [1,58 ; 1,79] | 0,99 [0,95 ; 1,04] | 0,97 [0,94 ; 1,01] |
| 42 | nominal | 669 | 0,81 [0,76 ; 0,85] | 1,00 [0,94 ; 1,06] | 0,87 [0,83 ; 0,92] | 1,31 [1,23 ; 1,39] | 0,92 [0,88 ; 0,97] | 0,98 [0,95 ; 1,02] |
| 42 | ZZ 3p | 653 | 1,00 [0,95 ; 1,06] | 1,24 [1,17 ; 1,31] | 1,02 [0,97 ; 1,08] | 1,68 [1,58 ; 1,80] | 0,99 [0,94 ; 1,03] | 0,98 [0,94 ; 1,01] |
| 43 | nominal | 598 | 0,85 [0,80 ; 0,90] | 1,05 [0,99 ; 1,11] | 0,89 [0,84 ; 0,94] | 1,44 [1,35 ; 1,54] | 0,92 [0,88 ; 0,97] | 0,99 [0,96 ; 1,03] |
| 43 | ZZ 3p | 645 | 1,05 [0,99 ; 1,11] | 1,22 [1,15 ; 1,29] | 1,06 [1,00 ; 1,12] | 1,72 [1,61 ; 1,83] | 0,98 [0,94 ; 1,03] | 1,00 [0,97 ; 1,04] |

Lecture à d = 3 : mwpf perd son avantage de 15 à 19 % (McNemar p ≤ 3e−8 au nominal) et revient à égalité avec PyMatching sous diaphonie (p ≥ 0,1 sur les trois graines) ; stimbposd de même ; BP+OSD passe de l'égalité à +20 à +24 % (p ≤ 7e−11) ; BP+LSD, déjà 31 à 44 % derrière PyMatching au nominal (ordre 0, constat 002), tombe à +68 à +72 %. beliefmatching et fusion-blossom ne bougent pas. Sous diaphonie ZZ, le taux de PyMatching lui-même ne change pas (648 → 661, 669 → 653, 598 → 645 erreurs) : il ne voit pas le secteur X. Cohérent avec la mesure Linux de septembre sur la graine 41 (mwpf 0,84 → 1,02) : le renversement est absent à d = 3, net à d = 5, plus fort à d = 7.

Rejeu des duels d = 5 (13/10), les journaux de septembre étant perdus (QEC-2026-021) : mêmes réglages (`redteam.duel`, d = 5, p = 0,002, mémoire Z, 40 000 tirs appariés par graine), graines 31, 32 et 33, poste Windows, PyMatching, mwpf et BP+OSD (tesseract : Linux requis). Fichiers `research/duel-d5/results-d5-s3*-windows.txt`.

| Graine | PyMatching, erreurs (nominal → ZZ 3p) | mwpf / PyMatching, nominal | mwpf / PyMatching, ZZ 3p | BP+OSD / PyMatching, nominal | BP+OSD / PyMatching, ZZ 3p |
|---|---|---|---|---|---|
| 31 | 219 → 177 | 0,69 [0,60 ; 0,78] | **2,82** [2,45 ; 3,29] | 0,87 [0,77 ; 0,99] | **2,33** [2,02 ; 2,71] |
| 32 | 214 → 184 | 0,65 [0,57 ; 0,75] | **2,53** [2,21 ; 2,94] | 0,81 [0,71 ; 0,92] | **2,45** [2,14 ; 2,82] |
| 33 | 157 → 150 | 0,76 [0,66 ; 0,88] | **3,02** [2,60 ; 3,56] | 0,96 [0,83 ; 1,11] | **2,71** [2,34 ; 3,19] |
| septembre, Linux (31, 32) | | 0,76 | 2,42 à 2,90 | 1,03 à 1,07 | 2,21 à 2,26 |

Le renversement de classement de mwpf à d = 5 est répliqué sur une autre machine et trois graines : de 0,65–0,76 fois les erreurs de PyMatching au nominal à 2,5–3,0 fois sous diaphonie ZZ (McNemar p ≤ 3e−43 aux trois graines). Même chose pour BP+OSD (2,3 à 2,7). Série d = 3, 5, 7 pour mwpf : 0,81–0,85 → 1,00–1,05 (d = 3), 0,65–0,76 → 2,5–3,0 (d = 5). Une différence non expliquée : au nominal, BP+OSD fait 0,81 à 0,96 fois PyMatching sous Windows contre 1,03 à 1,07 sous Linux en septembre ; les intervalles se touchent à peine, les comptes Linux sont perdus, piste ouverte QEC-2026-023.

Rejeu et plateformes : une graine stim n'est reproductible qu'à machine et version identiques (documentation de `compile_detector_sampler`) ; la même graine donne d'autres tirs sur une autre machine. Un duel reste apparié parce que tous ses décodeurs voient les mêmes tirs sur la machine qui l'exécute ; les séries `-windows` et `-linux` sont donc des réplications indépendantes l'une de l'autre, pas des rejeux au tir près.

Explication proposée : en mémoire Z, une erreur ZZ ne touche que des détecteurs de type X, sans effet sur l'observable. PyMatching sépare les deux secteurs et ne voit pas la différence (pénalité de réglage exactement 1,00). Les décodeurs qui voient le DEM entier expliquent ces détections imprévues par des erreurs Y, qui ont aussi un effet dans le secteur Z : ils se trompent là où ça compte. Informé de la diaphonie, tesseract repasse devant PyMatching (3,8e-3 contre 5,0e-3) : c'est une sensibilité à un défaut de calibration, pas un défaut de code. Journaux bruts : [docs/brique-2/](brique-2/).

## relay-bp : défaut du cœur de calcul, probabilité 1/2

Dans `crates/relay_bp/src/bp/min_sum.rs`, la décision dure est `posterior <= 0`. Un a priori d'exactement 1/2 donne un logarithme de rapport nul ; à égalité, le bit est décidé « erreur ». Reproduction minimale (`research/relay-bp-priors/repro_half_prior.py`, numpy, scipy et relay-bp seulement) : un contrôle, trois colonnes à 1/2, syndrome nul.

| Build | A priori | Correction rendue | Respecte le syndrome | Succès | Itérations (Relay) |
|---|---|---|---|---|---|
| PyPI 0.2.2 | 1/2, 1/2, 1/2 | [1, 1, 1] | **non** | non | 3 680 |
| branche principale d185194 | 1/2, 1/2, 1/2 | [1, 1, 1] | **non** | non | 3 680 |
| principale + `<` au lieu de `<=` | 1/2, 1/2, 1/2 | [0, 0, 0] | oui | oui | 3 |
| PyPI 0.2.2 | 0,49999 x3 | [0, 0, 0] | oui | oui | 3 |

Régression du correctif : 300 problèmes aléatoires sans probabilité 1/2, empreinte SHA-256 des sorties identique avant et après (`a3b3349e…`).

Sur le vrai DEM d'une fuite d'ancilla (d = 5), le syndrome nul est décodé en une correction de poids 14 (les 14 colonnes à 1/2) qui ne respecte pas le syndrome. En plafonnant les a priori à 0,49999, relay-bp informé passe de 749 à 83 erreurs sur 6 000 tirs (graine 101). **Mais le seul correctif `<` ne suffit pas** : avec lui, les taux sur ce scénario restent inchangés (1 301 et 1 303 erreurs sur 10 000, graines 101 et 102, contre 1 302 et 1 298 avant).

**Seconde cause, localisée le 12/10** (détail dans le [constat 003](constat-003-relay-bp-probabilites-additionnees.md), section 4) : un a priori de 1/2 est un effacement (rapport logarithmique exactement 0), et sur le vrai DEM d'une fuite les colonnes à 1/2 forment un *ensemble bloquant* du graphe de Tanner (chaque détecteur qu'elles touchent l'est au moins deux fois : 14 colonnes, 10 détecteurs à d = 5). Dans `compute_check_to_variable`, un message entrant de magnitude 0 met à 0 tous les messages sortants du contrôle vers les autres colonnes ; dans l'ensemble bloquant, tous les messages entrants restent donc exactement 0 à chaque itération, les a posteriori aussi (la mémoire de Mem-BP et les gammas de Relay multiplient un 0), et `posterior <= 0` tranche les 14 colonnes en bloc sans regarder le syndrome ; `<` choisit l'autre bloc. Aucun jeu de Relay ne converge et le décodeur rend sa décision de pré-itération. Réplique numpy des règles de `min_sum.rs` sur 200 tirs (`research/relay-bp-priors/stopping_set.py`) : a priori tels quels, messages et a posteriori de l'ensemble exactement 0 à chaque itération, syndrome satisfait 2/200 (fuite d'ancilla) et 0/200 (fuite de donnée) après 80 itérations ; plafonnés à 1/2 − 1e−5, 67/200 et 59/200. Le plafond répare parce qu'un rapport de 4e−5 garde un signe : les parités du syndrome circulent et min-sum se comporte, sur l'ensemble, comme un décodeur à signes seuls.

**Correctif du cœur, compilé et mesuré le 12/10** (`research/relay-bp-priors/fix-zero-llr-core.patch` : rapport logarithmique |LLR| < 4e−5 remplacé par +4e−5 dans `MinSumBPDecoder::new`, décision dure stricte ; compilé sous Windows avec rustup GNU et maturin, 13 tests amont ok, empreinte de régression inchangée) : avec le cœur corrigé et sans plafond Python, relay-bp informé passe de 12,84 % à **1,24 %** [1,12 ; 1,38] sur la fuite d'ancilla et de 5,60 % à **1,26 %** [1,14 ; 1,40] sur la fuite de donnée (d = 5, graines 101 à 103, 30 000 tirs chacune), au niveau du plafond Python (1,25 % et 1,18 % avec le même cœur) et de la mesure Linux du 30/09 (1,22 % et 1,19 %) ; PyMatching informé 0,87 % et 1,01 %. Fichiers `results-*-core-fix.txt` et `environnement-core-fix-windows.txt`.

## Biais Z, mémoire X

d = 5, 5 rounds, p = 0,002, mémoire X (sensible aux erreurs Z), dépolarisation remplacée par un canal biaisé vers Z à probabilité totale égale (η = pZ / (pX + pY) à un qubit), graine 20260929, même protocole que le tableau principal (arrêt à 200 erreurs, 100 pour les décodeurs lents). Les neuf décodeurs, complétés le 12/10 par BP+LSD (poste Windows ; les huit autres viennent de la session Linux de septembre, données `d5_r5_p0.002_x_biais_s20260929_biais*.csv` et `_bplsd_windows.csv`) :

| scénario | pymatching | fusion-blossom | beliefmatching | bplsd | bposd | stimbposd | mwpf | tesseract | relay-bp |
|---|---|---|---|---|---|---|---|---|---|
| nominal | 1.00 / x1.0 | 1.00 / x1.0 | 1.00 / x1.0 | 1.00 / x1.0 | 1.00 / x1.0 | 1.00 / x1.0 | 1.00 / x1.0 | 1.00 / x1.0 | 1.00 / x1.0 |
| biais Z eta=10 | 1.04 [0.99; 1.08] / x1.9 | 1.04 [0.96; 1.12] / x1.9 | 1.07 [0.98; 1.16] / x2.4 | 0.98 [0.88; 1.09] / x1.2 | 1.05 [0.96; 1.15] / x2.0 | 1.12 [0.97; 1.29] / x2.4 | 1.16 [1.01; 1.34] / x2.7 | 1.11 [0.96; 1.27] / x2.6 | 0.94 [0.86; 1.01] / x1.8 |
| biais Z eta=100 | 0.98 [0.94; 1.01] / x1.8 | 0.89 [0.81; 0.98] / x1.9 | 1.05 [0.98; 1.13] / x2.5 | 1.05 [0.96; 1.15] / x1.3 | 1.13 [1.03; 1.23] / x2.1 | 1.13 [1.02; 1.27] / x2.5 | 1.12 [1.01; 1.26] / x2.7 | 1.10 [0.99; 1.23] / x2.7 | 1.02 [0.94; 1.11] / x1.9 |
| biais Z eta=1000 | 1.00 [0.96; 1.04] / x1.9 | **0.77** [0.69; 0.86] / x1.9 | 1.05 [0.97; 1.13] / x2.7 | 1.11 [1.01; 1.21] / x1.4 | 1.12 [1.03; 1.22] / x2.1 | 1.08 [0.98; 1.21] / x2.6 | 1.17 [1.04; 1.33] / x3.1 | 1.11 [0.99; 1.25] / x2.9 | 1.02 [0.94; 1.11] / x1.9 |

Taux sous bruit nominal (mémoire X) : PyMatching 4,1e−3, fusion-blossom 4,2e−3, BP+OSD 4,0e−3, relay-bp 4,3e−3, beliefmatching 3,2e−3, stimbposd 3,1e−3, mwpf 2,9e−3, tesseract 2,9e−3, BP+LSD 7,7e−3 (ordre 0, constat 002 : déjà ×1,9 derrière PyMatching sans biais).

Lecture : **rien ne casse sous biais Z en mémoire X.** Pénalités de réglage entre 0,94 et 1,17 ; les décodeurs à hypergraphe (mwpf, stimbposd, tesseract, BP+OSD) paient 8 à 17 % de ne pas connaître le biais à η = 1000, PyMatching et relay-bp rien. La dégradation est de ×1,8 à ×3,1 pour tous, parce que concentrer la même probabilité sur Z double à peu près le taux d'erreurs Z vues par la mémoire X. La seule anomalie, fusion-blossom **informé** moins bon que réglé (0,77 à η = 1000), a été expliquée le 30/09 : l'adaptateur sinter ne fusionne pas les arêtes parallèles ([constat 004](constat-004-sinter-fusion-blossom-aretes-paralleles.md), Stim #1116). BP+LSD seul a une pénalité nettement > 1 à η = 1000 avec un taux nominal déjà double : c'est l'ordre 0 de LSD (QEC-2026-020), pas le biais.

## Biais Z, mémoire Z (miroir, 13/10)

Même banc, même graine (20260929), mémoire Z : l'observable y est retournée par les erreurs X, que le biais raréfie. Huit décodeurs sur le poste Windows (relay-bp compilé depuis sa sdist, voir plus haut ; tesseract absent, voir « Ce qui reste à faire »). Arrêt à 200 erreurs ; jusqu'à 558 000 tirs par cellule. Pénalité de réglage [IC 95 %] ; données `d5_r5_p0.002_z_biais_s20260929_windows.csv` et `_relay_windows.csv`, journaux `biais_z_memoire_z_*windows.txt`.

| scénario | pymatching | fusion-blossom | beliefmatching | bplsd | bposd | stimbposd | mwpf | relay-bp |
|---|---|---|---|---|---|---|---|---|
| nominal, taux | 4,41e−3 | 4,68e−3 | 3,16e−3 | 7,92e−3 | 4,06e−3 | 2,97e−3 | 3,45e−3 | 5,05e−3 |
| biais Z eta=10 | 1.17 [1.09; 1.26] | 1.04 [0.98; 1.09] | 1.21 [1.11; 1.32] | 1.58 [1.36; 1.85] | 1.17 [1.08; 1.27] | 1.09 [1.02; 1.16] | 1.26 [1.16; 1.37] | 1.23 [1.13; 1.34] |
| biais Z eta=100 | 1.19 [1.11; 1.28] | **0.61** [0.53; 0.69] | 1.29 [1.20; 1.41] | 1.69 [1.50; 1.93] | 1.23 [1.15; 1.33] | 1.16 [1.08; 1.24] | 1.33 [1.23; 1.46] | 1.29 [1.19; 1.41] |
| biais Z eta=1000 | 1.23 [1.16; 1.32] | **0.65** [0.57; 0.72] | 1.32 [1.23; 1.44] | 1.70 [1.51; 1.93] | 1.22 [1.14; 1.32] | 1.21 [1.14; 1.30] | 1.35 [1.25; 1.47] | 1.39 [1.27; 1.53] |
| eta=1000, taux réglé / informé | 3,64 / 2,95e−4 | 3,32 / 5,13e−4 | 3,83 / 2,89e−4 | 5,34 / 3,15e−4 | 3,72 / 3,05e−4 | 3,58 / 2,96e−4 | 3,91 / 2,89e−4 | 4,20 / 3,03e−4 |

Lecture, point par point :

- **Le biais aide la mémoire Z** : le taux d'erreur de PyMatching est divisé par 12 à η = 1000 (4,4e−3 → 3,6e−4), puisque les erreurs X deviennent rares. Rien ne casse, aucune exception (relay-bp compris).
- **Contrairement à la mémoire X, tous les décodeurs réglés paient** 9 à 39 % de ne pas connaître le biais, PyMatching compris (1,17 à 1,23). Rejoué avec d'autres graines (11 à 13, 900 000 tirs, `research/biais-memoire-z/results-hybride.txt`) : 1,16 à 1,27. Le mécanisme n'est **pas établi** : en mémoire Z, le biais déforme le graphe de couplage de façon très inégale (arêtes temporelles ×0,89, la plupart des arêtes spatiales et diagonales ×0,001 à η = 1000, mais certaines arêtes des rounds de bord gardent ×0,86 ; en mémoire X tout bouge de ×1,02 à ×1,3, `results-aretes.txt`). L'explication simple « c'est le rapport entre classes d'arêtes » est **réfutée** sous sa forme directe : un PyMatching hybride, graphe nominal multiplié par le facteur médian de chaque classe, fait pire que le réglé (1,85 à 1,91 fois l'informé, contre 1,16 à 1,27). Piste ouverte QEC-2026-022.
- **fusion-blossom informé moins bon que réglé (0,61 et 0,65) : c'est bien le constat 004, vérifié et non supposé.** Mêmes tirs, d = 5, mémoire Z (`research/sinter-fusion-blossom/parallel_edges.py --basis z`, graines 11 à 13, 600 000 tirs) : l'adaptateur de sinter fait 5,62e−4 à η = 1000, fusion-blossom avec arêtes parallèles fusionnées 3,05e−4, PyMatching 3,05e−4 (183 erreurs pour les deux, au tir près) : ×1,84, McNemar p = 3e−45 ; à η = 100, ×1,78, p = 5e−41. À η = 10, rien (pénalité 1,04). Le défaut coûte plus en mémoire Z qu'en mémoire X (×1,26 à d = 5, η = 1000).
- **BP+LSD est le plus sensible au réglage** (1,58 à 1,70), mais informé il rejoint PyMatching (3,15e−4 contre 2,95e−4) ; son retard au nominal (×1,8 sur PyMatching) est le même qu'en mémoire X : l'ordre 0 de LSD (QEC-2026-020), pas le biais.
- **relay-bp** se range avec les autres (1,23 à 1,39), sans exception : un bruit biaisé ne sature aucun qubit, le constat 003 ne s'y déclenche pas.

Réponse à la question posée (« les écarts de la mémoire X tiennent-ils dans l'autre base ? ») : le constat 004 tient et s'aggrave ; l'écart de BP+LSD au nominal tient, son écart sous biais disparaît quand il est informé ; tesseract reste à mesurer (Linux requis).

## Plantages et délais

| Décodeur | Scénarios | Symptôme | Cause |
|---|---|---|---|
| relay-bp 0.2.2 | les 6 scénarios de fuite et de rafale, côté informé | `TypeError: argument 'detectors': 'matrix' object is not an instance of 'ndarray'` | voir ci-dessous |

### relay-bp : le branchement sinter additionne les probabilités

Lu dans `relay_bp/stim/sinter/check_matrices.py`, puis vérifié par exécution :

1. Sur un DEM décomposé, la probabilité de chaque arête est `hyperedge_to_edge_matrix @ priors` : une **somme** des probabilités des mécanismes qui la contiennent. Des mécanismes indépendants se combinent en 1/2 (1 − Π(1 − 2 pᵢ)), qui ne dépasse jamais 1/2. La somme, elle, dépasse 1/2 et même 1.
2. Toute arête dont la somme atteint 1 est traitée comme une erreur certaine (`prune_decided_errors`). Le biais de syndrome qui en résulte est une `np.matrix` (somme d'une matrice creuse scipy), que le cœur Rust refuse : exception à chaque décodage.
3. En 0.2.2, le biais des observables est calculé sur la matrice de contrôle au lieu de celle des observables (forme (1, 24) au lieu de (1, 1) à d = 3). Déjà corrigé sur la branche principale (commit d185194, « Fix syndrome pruning (#42) », 21/07/2026, non publié sur PyPI). Les points 1 et 2 y sont toujours : la même exception se produit avec le fichier de la branche principale.

Mesures à d = 3, p = 0,002 :

| Vrai bruit | Probabilité max du DEM | Somme max par arête | Arêtes > 1/2 | Arêtes ≥ 1 | Résultat |
|---|---|---|---|---|---|
| nominal | 0,027 | 0,030 | 0 | 0 | ok |
| ancilla centrale x30 | 0,362 | 0,386 | 0 | 0 | ok |
| ancilla centrale x100 | 0,500 | 0,630 | 3 | 0 | pas d'exception, 3 arêtes pondérées comme « erreur probable » |
| fuite de l'ancilla centrale, 1 round | 0,500 | 4,500 | 12 | 12 | exception |
| fuite d'un qubit de données, 1 round | 0,500 | 3,001 | 14 | 14 | exception |

Documentation lue : le README de relay-bp (PyPI 0.2.2) et la docstring de `from_dem` ne parlent ni de la somme ni d'une limite sur les probabilités. Aucune issue ouverte ou fermée du dépôt `trmue/relay` ne traite de ce point (lu le 29/09).

Effet sur le taux d'erreur, d = 5, p = 0,002, trois graines (101, 102, 103) de 10 000 tirs, tous les décodeurs construits sur le DEM **réel** (`research/relay-bp-priors/measure_effect.py`) :

| Vrai bruit | relay-bp publié | exception seule corrigée | probabilités combinées (correctif proposé) | PyMatching |
|---|---|---|---|---|
| ancilla centrale x100 | 4,85e-2 [4,62; 5,10] | identique | 4,81e-2 [4,58; 5,06] | 4,34e-2 |
| donnée centrale x100 | 3,22e-2 [3,03; 3,43] | identique | 3,36e-2 [3,16; 3,57] | 3,00e-2 |
| fuite de la donnée centrale, 1 round | **exception** aux 3 graines | 1,137e-1 [1,102; 1,174] | 5,60e-2 [5,35; 5,87] | 9,8e-3 [8,7; 11,0] |

Lecture : tant qu'aucune arête n'atteint 1, la somme ne coûte rien de mesurable. Dès qu'une arête l'atteint, la version publiée plante, et la correction naïve (convertir le biais en tableau) rend un décodeur qui se trompe 11,6 fois plus que PyMatching. Même avec les probabilités combinées, relay-bp informé d'un qubit saturé reste 5,7 fois moins bon que PyMatching : des a priori à 1/2 (rapport de vraisemblance nul) semblent mal lui convenir. Ce dernier point n'est pas un défaut établi.

Portée honnête : le défaut ne touche que les DEM contenant des canaux proches de la saturation, c'est-à-dire un qubit mort, en fuite ou frappé par une rafale, **tel qu'un DEM calibré sur une vraie puce peut en contenir**. Avec le bruit nominal SI1000, rien ne se passe. 

## Latence de décodage par tir, sous bruit perturbé

`redteam.latency` : chaque tir est décodé seul, par le décodeur réglé sur le nominal, chronométré en nanosecondes ; d = 5, 5 rounds, p = 0,002, graine 20260929 ; 5 000 tirs pour les décodeurs rapides, 1 000 pour tesseract, stimbposd et mwpf (le p99,9 et le max de ces trois-là reposent donc sur 1 à 10 tirs). « Plancher » : un syndrome nul, soit le coût fixe de l'appel Python. Un cœur, machine par ailleurs chargée d'un autre calcul sur un second cœur (sur 4). Colonnes « / round » : divisé par 5.

| décodeur | scénario | plancher µs | p50 µs | p99 µs | p99,9 µs | max µs | p50 / round | max / round |
|---|---|---|---|---|---|---|---|---|
| pymatching | nominal | 7 | 9 | 41 | 145 | 503 | 2 | 101 |
| pymatching | tout x3 | 7 | 15 | 61 | 166 | 1 062 | 3 | 212 |
| pymatching | ancilla chaude x100 | 7 | 17 | 57 | 80 | 621 | 3 | 124 |
| pymatching | fuite ancilla 1r | 7 | 11 | 46 | 102 | 959 | 2 | 192 |
| pymatching | rafale 0.5 | 7 | 13 | 48 | 79 | 143 | 3 | 29 |
| pymatching | diaphonie ZZ 3p | 7 | 13 | 43 | 60 | 78 | 3 | 16 |
| fusion-blossom | nominal | 18 | 79 | 352 | 556 | 1 132 | 16 | 226 |
| fusion-blossom | tout x3 | 18 | 304 | 1 085 | 1 901 | 2 707 | 61 | 541 |
| fusion-blossom | ancilla chaude x100 | 18 | 375 | 1 141 | 1 734 | 2 632 | 75 | 526 |
| fusion-blossom | fuite ancilla 1r | 18 | 159 | 657 | 936 | 1 414 | 32 | 283 |
| fusion-blossom | rafale 0.5 | 18 | 220 | 837 | 1 272 | 1 898 | 44 | 380 |
| fusion-blossom | diaphonie ZZ 3p | 18 | 234 | 746 | 1 442 | 3 256 | 47 | 651 |
| beliefmatching | nominal | 19 | 860 | 9 267 | 12 519 | 14 152 | 172 | 2 830 |
| beliefmatching | tout x3 | 19 | 7 761 | 12 309 | 15 750 | 18 344 | 1 552 | 3 669 |
| beliefmatching | ancilla chaude x100 | 19 | 8 021 | 13 378 | 17 956 | 24 189 | 1 604 | 4 838 |
| beliefmatching | fuite ancilla 1r | 19 | 7 673 | 11 490 | 13 927 | 16 405 | 1 535 | 3 281 |
| beliefmatching | rafale 0.5 | 22 | 7 852 | 12 176 | 14 859 | 24 550 | 1 570 | 4 910 |
| beliefmatching | diaphonie ZZ 3p | 19 | 7 750 | 12 930 | 16 191 | 24 695 | 1 550 | 4 939 |
| bplsd | nominal | 208 | 293 | 5 880 | 7 912 | 11 245 | 59 | 2 249 |
| bplsd | tout x3 | 201 | 4 312 | 11 141 | 20 473 | 32 916 | 862 | 6 583 |
| bplsd | ancilla chaude x100 | 194 | 4 700 | 14 273 | 24 228 | 40 135 | 940 | 8 027 |
| bplsd | fuite ancilla 1r | 199 | 1 499 | 7 994 | 11 746 | 23 819 | 300 | 4 764 |
| bplsd | rafale 0.5 | 197 | 4 373 | 9 905 | 13 755 | 17 113 | 875 | 3 423 |
| bplsd | diaphonie ZZ 3p | 202 | 738 | 9 446 | 17 171 | 23 757 | 148 | 4 751 |
| bposd | nominal | 19 | 288 | 14 430 | 20 342 | 22 793 | 58 | 4 559 |
| bposd | tout x3 | 19 | 12 264 | 18 453 | 22 143 | 32 057 | 2 453 | 6 411 |
| bposd | ancilla chaude x100 | 19 | 12 730 | 20 127 | 22 985 | 26 573 | 2 546 | 5 315 |
| bposd | fuite ancilla 1r | 19 | 1 478 | 18 265 | 24 974 | 28 197 | 296 | 5 639 |
| bposd | rafale 0.5 | 19 | 12 152 | 18 815 | 21 257 | 49 035 | 2 430 | 9 807 |
| bposd | diaphonie ZZ 3p | 19 | 730 | 17 962 | 25 028 | 35 829 | 146 | 7 166 |
| relay-bp | nominal | 110 | 184 | 3 214 | 7 524 | 15 019 | 37 | 3 004 |
| relay-bp | tout x3 | 87 | 560 | 9 662 | 26 626 | 77 714 | 112 | 15 543 |
| relay-bp | ancilla chaude x100 | 89 | 1 656 | 30 882 | 75 577 | 78 089 | 331 | 15 618 |
| relay-bp | fuite ancilla 1r | 98 | 352 | 11 362 | 37 668 | 74 693 | 70 | 14 939 |
| relay-bp | rafale 0.5 | 87 | 557 | 16 002 | 72 406 | 87 265 | 111 | 17 453 |
| relay-bp | diaphonie ZZ 3p | 98 | 463 | 5 651 | 13 164 | 31 432 | 93 | 6 286 |
| tesseract | nominal | 33 | 2 616 | 16 706 | 66 809 | 83 370 | 523 | 16 674 |
| tesseract | tout x3 | 33 | 12 442 | 381 695 | 871 472 | 1 784 658 | 2 488 | 356 932 |
| tesseract | ancilla chaude x100 | 33 | 24 525 | 467 076 | 605 217 | 738 783 | 4 905 | 147 757 |
| tesseract | fuite ancilla 1r | 34 | 5 756 | 69 109 | 237 637 | 403 623 | 1 151 | 80 725 |
| tesseract | rafale 0.5 | 33 | 8 726 | 219 340 | 461 628 | 497 084 | 1 745 | 99 417 |
| tesseract | diaphonie ZZ 3p | 34 | 12 661 | 191 978 | 530 413 | 1 574 547 | 2 532 | 314 909 |
| stimbposd | nominal | 19 | 875 | 29 503 | 44 605 | 46 046 | 175 | 9 209 |
| stimbposd | tout x3 | 19 | 25 991 | 31 498 | 42 135 | 45 714 | 5 198 | 9 143 |
| stimbposd | ancilla chaude x100 | 19 | 26 585 | 39 422 | 44 436 | 51 581 | 5 317 | 10 316 |
| stimbposd | fuite ancilla 1r | 37 | 25 505 | 38 060 | 42 671 | 43 246 | 5 101 | 8 649 |
| stimbposd | rafale 0.5 | 19 | 26 122 | 39 638 | 43 583 | 44 514 | 5 224 | 8 903 |
| stimbposd | diaphonie ZZ 3p | 19 | 26 081 | 38 586 | 42 947 | 45 034 | 5 216 | 9 007 |
| mwpf | nominal | 118 | 426 | 157 295 | 414 566 | 460 641 | 85 | 92 128 |
| mwpf | tout x3 | 122 | 8 822 | 503 892 | 639 178 | 679 575 | 1 764 | 135 915 |
| mwpf | ancilla chaude x100 | 118 | 68 897 | 651 847 | 799 106 | 844 589 | 13 779 | 168 918 |
| mwpf | fuite ancilla 1r | 140 | 3 986 | 612 976 | 759 709 | 767 743 | 797 | 153 549 |
| mwpf | rafale 0.5 | 117 | 23 354 | 580 558 | 802 377 | 912 256 | 4 671 | 182 451 |
| mwpf | diaphonie ZZ 3p | 119 | 5 799 | 670 317 | 854 676 | 882 767 | 1 160 | 176 553 |


Rejeu, graine indépendante 777, 1 000 tirs ([rejeu_s777.csv](brique-2/latence/rejeu_s777.csv)) :

| Décodeur | Scénario | p50 µs | p99 µs | p99,9 µs | max µs |
|---|---|---|---|---|---|
| tesseract | nominal | 2 733 | 21 293 | 45 557 | 86 940 |
| tesseract | tout x3 | 12 668 | **398 546** | 1 622 817 | **1 932 213** |
| tesseract | diaphonie ZZ 3p | 12 682 | 150 372 | 695 841 | 720 270 |
| mwpf | nominal | 411 | 287 346 | 445 588 | 517 496 |
| mwpf | tout x3 | 11 271 | 528 023 | 599 994 | 625 944 |
| mwpf | diaphonie ZZ 3p | 5 783 | 638 566 | 827 139 | 829 476 |

Lecture :
- **PyMatching** reste sous 61 µs au p99 et sous 1,1 ms au max partout, plancher Python compris.
- **tesseract** : sa queue s'allonge d'un facteur 19 au p99 sous bruit perturbé (21 → 399 ms), avec des tirs à près de 2 s. Sous diaphonie ZZ, où PyMatching ne change presque pas, son p99 est multiplié par 7 à 11. C'est inhérent à sa recherche A* (sa documentation présente le faisceau comme un compromis vitesse-précision), pas un défaut, mais c'est rédhibitoire pour un décodage temps réel sans borne de temps.
- **mwpf** : queue lourde dès le nominal (p99 157 à 287 ms, p50 0,4 ms), 0,5 à 0,65 s perturbé. decoder-bench lui impose un délai de 3 s ; l'intégration sinter utilisée ici n'en a pas.
- **stimbposd, BP+OSD, BP+LSD, beliefmatching** : le p50 grimpe d'un facteur 10 à 30 sous bruit perturbé (BP ne converge plus, OSD prend le relais), mais la queue reste bornée par le coût d'OSD : max ≤ 52 ms.
- **relay-bp** : p50 ×2 à ×9, max ≤ 87 ms.

Données brutes : [docs/brique-2/latence/](brique-2/latence/).

## Ce qui reste à faire

État au 13/10 :

- **Diaphonie, effet de la distance** : fait pour mwpf, BP+OSD, stimbposd, BP+LSD, beliefmatching et fusion-blossom à d = 3 (3 graines) et pour mwpf et BP+OSD à d = 5 (rejeu Windows, 3 graines). **Bloqué, Linux requis** : tesseract à d = 3 sur 3 graines (41 à 43) et le rejeu de ses duels d = 5 (31 à 33), dont les journaux de septembre sont perdus (QEC-2026-021). tesseract-decoder n'a ni roue Windows ni sdist sur PyPI ; un essai borné de compilation depuis les sources (commit 6a260b0, celui de la version utilisée, CMake + zig c++ + pybind11 3.0.1 pour Python 3.14) a échoué le 13/10 : `src/visualization.cc` ne compile pas avec la libc++ de zig (ligne 15 : « no matching function for call to 'min' »), et le disque C: du poste s'est rempli pendant la compilation de stim (voir le journal du PLAN). Commandes à lancer sous Linux, Python 3.11 à 3.13 : `python -m redteam.duel --distance 3 --p 0.002 --scenario nominal "diaphonie ZZ 3p" --decoders pymatching tesseract mwpf --shots 60000 --seed 41` (puis 42, 43), et de même `--distance 5 --shots 40000 --seed 31` (puis 32, 33).
- **relay-bp** : fait. Seconde cause localisée (ensemble bloquant, 12/10), correctif du cœur compilé et mesuré sous Windows (e49f8af) : 12,84 % → 1,24 % et 5,60 % → 1,26 %. Reste, facultatif : le même rejeu sous Linux, et un test apparié `corrected` contre `clamped` sur la fuite de donnée (379 contre 353 erreurs sur 30 000, non significatif en l'état).
- **Biais Z** : fait en mémoire X (9 décodeurs) et en mémoire Z (8 décodeurs). **Bloqué, Linux requis** : tesseract en mémoire Z. Ouvert : le mécanisme de la pénalité en mémoire Z (QEC-2026-022).
