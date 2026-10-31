# Le code XZZX, celui des qubits de chat : que valent les décodeurs ?

En bref :
1. Le code XZZX est fait pour les qubits dont les erreurs penchent d'un seul côté (qubits de chat d'Alice & Bob). Avec un bon décodeur, il divise les erreurs par 4 à 5.
2. Les décodeurs qui voient les erreurs corrélées (tesseract, stimbposd, mwpf, BP+OSD) font environ 15 % d'erreurs en moins que PyMatching sur ce code ; sur le code ordinaire, tous sont à égalité.
3. fusion-blossom branché par sinter (Google) perd la moitié du gain : c'est le défaut déjà signalé (Stim #1116).
4. BP+LSD fait 15 % de plus que PyMatching : il se comporte comme BP+OSD le plus simple (ordre 0) ; c'est la recherche plus poussée de BP+OSD (ordre 10) qui fait la différence sur ce code. Fausse piste vérifiée, pas un défaut.
5. Ce sont des profils, pas des défauts, sauf le point 3.

Code de surface tourné d = 5, 5 rounds, mémoire X, SI1000 à p = 0,002 dont la dépolarisation est remplacée par un canal biaisé vers Z (η = 1000) ; chaque décodeur est construit sur le vrai modèle d'erreurs ; 300 000 tirs par décodeur et par code (graines 21, 22, 23), mêmes tirs pour tous les décodeurs d'un même code. Intervalles à 95 % ; rapport apparié à PyMatching sur les mêmes tirs.

| Décodeur | code ordinaire | XZZX | gain XZZX | XZZX / PyMatching [IC 95 %] | McNemar p |
|---|---|---|---|---|---|
| pymatching | 0.813% [0.781% ; 0.846%] | 0.200% [0.184% ; 0.216%] | ×4.07 | 1.00 [1.00 ; 1.00] | 1.0e+00 |
| fusion-blossom | 1.034% [0.999% ; 1.071%] | 0.388% [0.367% ; 0.411%] | ×2.66 | 1.94 [1.82 ; 2.08] | 5.5e-98 |
| beliefmatching | 0.822% [0.791% ; 0.855%] | 0.187% [0.172% ; 0.203%] | ×4.39 | 0.94 [0.90 ; 0.98] | 6.0e-03 |
| mwpf | 0.806% [0.775% ; 0.839%] | 0.171% [0.157% ; 0.186%] | ×4.71 | 0.86 [0.81 ; 0.90] | 2.7e-09 |
| tesseract | 0.806% [0.774% ; 0.838%] | 0.167% [0.153% ; 0.183%] | ×4.81 | 0.84 [0.80 ; 0.88] | 2.8e-12 |
| bposd | 0.816% [0.785% ; 0.849%] | 0.180% [0.165% ; 0.195%] | ×4.54 | 0.90 [0.85 ; 0.95] | 4.6e-05 |
| bplsd | 0.824% [0.792% ; 0.857%] | 0.229% [0.213% ; 0.247%] | ×3.60 | 1.15 [1.09 ; 1.21] | 1.2e-06 |
| stimbposd | 0.807% [0.775% ; 0.839%] | 0.170% [0.156% ; 0.186%] | ×4.74 | 0.85 [0.81 ; 0.90] | 2.1e-10 |
| relay-bp | 0.867% [0.835% ; 0.901%] | 0.196% [0.180% ; 0.212%] | ×4.43 | 0.98 [0.93 ; 1.03] | 4.4e-01 |

Rejouer : `research/xzzx-sweep/sweep.py` (une exécution par code, décodeur et graine), puis `research/xzzx-sweep/analyse.py --seeds 21 22 23`. Construction du code XZZX : `redteam/xzzx.py` (bruit conjugué par Hadamard sur une paire diagonale de chaque plaquette, testé dans `tests/test_xzzx.py`).

## À distance 7 (100 000 tirs, graine 21)

Le gain du code XZZX grandit avec la taille : environ ×8 au lieu de ×4. Mais à ce niveau, il n'y a qu'une quarantaine d'erreurs sur 100 000 tirs par décodeur : les écarts entre décodeurs ne sont plus mesurables, sauf fusion-blossom via sinter, toujours derrière (1,29 [1,08 ; 1,58], p = 0,01). Il faudrait environ dix fois plus de tirs pour départager les autres.

| Décodeur | code ordinaire | XZZX | gain XZZX | XZZX / PyMatching [IC 95 %] | McNemar p |
|---|---|---|---|---|---|
| pymatching | 0.351% [0.316% ; 0.390%] | 0.045% [0.034% ; 0.060%] | ×7.80 | 1.00 [1.00 ; 1.00] | 1.0e+00 |
| fusion-blossom | 0.357% [0.322% ; 0.396%] | 0.058% [0.045% ; 0.075%] | ×6.16 | 1.29 [1.08 ; 1.58] | 1.1e-02 |
| beliefmatching | 0.354% [0.319% ; 0.393%] | 0.044% [0.033% ; 0.059%] | ×8.05 | 0.98 [0.80 ; 1.19] | 1.0e+00 |
| mwpf | 0.344% [0.310% ; 0.382%] | 0.043% [0.032% ; 0.058%] | ×8.00 | 0.96 [0.78 ; 1.16] | 8.1e-01 |
| tesseract | 0.337% [0.303% ; 0.375%] | 0.039% [0.029% ; 0.053%] | ×8.64 | 0.87 [0.72 ; 1.03] | 1.8e-01 |
| bposd | 0.353% [0.318% ; 0.392%] | 0.043% [0.032% ; 0.058%] | ×8.21 | 0.96 [0.78 ; 1.17] | 8.2e-01 |
| bplsd | 0.369% [0.333% ; 0.409%] | 0.056% [0.043% ; 0.073%] | ×6.59 | 1.24 [0.98 ; 1.59] | 9.0e-02 |
| stimbposd | 0.339% [0.305% ; 0.377%] | 0.041% [0.030% ; 0.056%] | ×8.27 | 0.91 [0.75 ; 1.10] | 4.5e-01 |
| relay-bp | 0.399% [0.362% ; 0.440%] | 0.054% [0.041% ; 0.070%] | ×7.39 | 1.20 [1.00 ; 1.47] | 9.3e-02 |
