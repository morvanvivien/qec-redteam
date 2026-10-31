# Constat 003 — relay-bp casse sur un qubit saturé : exception dans son module stim, corrections invalides dans son cœur

Date : 29 septembre 2026. Statut : **signalé au mainteneur le 30/09** (dépôt `trmue/relay`, IBM), par l'auteur depuis le compte `morvanvivien`, texte dans [issues/relay-bp-saturated-priors.md](issues/relay-bp-saturated-priors.md). Détails en anglais pour le mainteneur : [research/relay-bp-priors/](../research/relay-bp-priors/README.md).

## En une phrase

Le module stim/sinter livré avec relay-bp additionne les probabilités des mécanismes d'erreur au lieu de les combiner. Dès qu'un qubit devient aléatoire pendant un round (fuite, rafale, qubit mort), certaines arêtes dépassent la probabilité 1 et chaque décodage lève une exception. Si l'on corrige seulement l'exception, le décodeur traite ces arêtes comme des erreurs certaines et devient pire que s'il ignorait tout du vrai bruit. En dessous, dans le cœur Rust, une probabilité d'exactement 1/2 (celle d'un qubit complètement aléatoire) fait rendre des corrections qui ne respectent pas le syndrome, après des milliers d'itérations.

## C'est une cassure au sens de la brique 2

- **Décodeur public :** relay-bp 0.2.2, la dernière version sur PyPI, et la branche principale au commit d185194 du 21/07/2026. C'est le décodeur de référence d'IBM pour les codes qLDPC, testé par decoder-bench.
- **Bruit plausible :** un seul qubit rendu aléatoire pendant un seul round. C'est le modèle le plus simple d'une fuite, d'une rafale de rayonnement ou d'un qubit défaillant, et un DEM calibré sur une vraie puce peut en contenir.
- **Reproductible :** un script de 60 lignes qui n'utilise que stim, numpy et relay-bp, un seul décodage, un résultat déterministe.

## Ce qui est établi

### 1. La cause, lue dans le code puis vérifiée

`relay_bp/stim/sinter/check_matrices.py`, méthode `CheckMatrices.from_dem`, cas du DEM décomposé (le cas par défaut avec sinter) :

```python
error_priors = dem_matrices.hyperedge_to_edge_matrix @ dem_matrices.priors
```

La probabilité d'une arête y est la **somme** des probabilités des mécanismes qui la contiennent. Des mécanismes indépendants se combinent en 1/2 (1 − Π(1 − 2 pᵢ)), qui ne dépasse jamais 1/2. Ensuite, `prune_decided_errors` retire toute arête de probabilité ≥ 1 comme erreur **certaine**, et construit un biais de syndrome par `np.sum` sur une matrice creuse scipy : le résultat est une `np.matrix`, que le cœur Rust refuse.

### 2. Le seuil de déclenchement

d = 3, bruit uniforme p = 0,002, un qubit de données dépolarisé à chaque TICK du deuxième round :

| Dépolarisation par TICK | Somme max par arête | Arêtes > 1/2 | Arêtes ≥ 1 | relay-bp |
|---|---|---|---|---|
| 0,05 | 0,18 | 0 | 0 | ok |
| 0,10 | 0,33 | 0 | 0 | ok |
| 0,20 | 0,61 | 1 | 0 | ok, une arête pondérée « erreur probable » |
| 0,30 | 0,86 | 3 | 0 | ok, trois arêtes « erreur probable » |
| 0,40 | 1,09 | 4 | 1 | **exception à chaque décodage** |
| 0,75 (mélange complet) | 2,01 | 5 | 5 | **exception à chaque décodage** |

### 3. L'effet, rejoué depuis zéro sur trois graines

d = 5, SI1000 à p = 0,002, graines 101, 102 et 103, 10 000 tirs chacune, tous les décodeurs construits sur le DEM **réel** du tir. Intervalles de Wilson à 95 %.

| Vrai bruit | relay-bp publié | exception seule corrigée | probabilités combinées | PyMatching |
|---|---|---|---|---|
| qubit de données central rendu aléatoire au round du milieu (3 sur 5) | **exception**, 3 graines sur 3 | 11,4 % [11,0 ; 11,7] | 5,6 % [5,3 ; 5,9] | 0,98 % [0,87 ; 1,10] |
| ancilla centrale x100 (aucune arête ≥ 1) | 4,85 % [4,62 ; 5,10] | identique | 4,81 % [4,58 ; 5,06] | 4,34 % |

Les trois graines donnent le même rapport, « exception seule corrigée » sur « probabilités combinées » : 2,01, 2,00 et 2,08 (McNemar p < 1e-50 à chaque graine).

Pour situer « pire qu'ignorant », d = 3, bruit SI1000 à p = 0,002, graines 201, 202 et 203, 5 000 tirs chacune (15 000 cumulés). « Réglé » : construit sur le DEM nominal, il ignore l'événement. « Informé » : construit sur le DEM réel du tir.

| Vrai bruit | relay-bp informé, publié | relay-bp informé, exception seule corrigée | relay-bp réglé | relay-bp informé, combinées | PyMatching réglé | PyMatching informé |
|---|---|---|---|---|---|---|
| qubit de données central aléatoire au round du milieu (2 sur 3) | **exception** (3/3) | **49,7 %** [48,9 ; 50,5] | 13,8 % [13,3 ; 14,4] | 6,7 % [6,3 ; 7,1] | 13,3 % | 3,8 % |
| une ancilla tirée au sort, aléatoire pendant un round tiré au sort | **exception** (3/3) | **28,6 %** [27,9 ; 29,3] | 19,5 % [18,8 ; 20,1] | 20,1 % [19,5 ; 20,8] | 19,9 % | 4,3 % |

Avec la seule exception corrigée, relay-bp informé fait 3,6 fois pire que relay-bp qui ignore la fuite, et tombe à pile ou face dans le premier cas. Avec les probabilités combinées, il gagne un facteur 2 sur une fuite de donnée mais rien sur une fuite d'ancilla, là où PyMatching gagne un facteur 4,6.

### 4. Second défaut, dans le cœur : une probabilité d'exactement 1/2

`crates/relay_bp/src/bp/min_sum.rs`, `compute_hard_decision` : `Bit::from(posterior <= 0)`. Un a priori de 1/2 donne un logarithme de rapport nul, donc des messages de magnitude nulle. Or min-sum ne propage que des signes et des minima : un message nul n'a pas de signe et éteint le contrôle qui le reçoit. À égalité (a posteriori nul), le bit est décidé « erreur ».

Reproduction minimale (`research/relay-bp-priors/repro_half_prior.py`, numpy, scipy et relay-bp seulement, déterministe) : un contrôle, trois colonnes, syndrome nul.

| Build | A priori | Correction rendue | Respecte le syndrome | Succès | Itérations (Relay) |
|---|---|---|---|---|---|
| PyPI 0.2.2 | 1/2, 1/2, 1/2 | [1, 1, 1] | **non** | non | 3 680 |
| branche principale d185194, compilée depuis les sources | 1/2, 1/2, 1/2 | [1, 1, 1] | **non** | non | 3 680 |
| principale + `<` au lieu de `<=` | 1/2, 1/2, 1/2 | [0, 0, 0] | oui | oui | 3 |
| PyPI 0.2.2 | 0,49999 x3 | [0, 0, 0] | oui | oui | 3 |

Le correctif d'un caractère (`research/relay-bp-priors/fix-hard-decision-tie.patch`) ne change rien ailleurs : sur 300 problèmes aléatoires sans probabilité 1/2, l'empreinte SHA-256 des sorties est identique avant et après.

Sur le vrai DEM d'une fuite d'ancilla (d = 5), le syndrome nul est décodé en une correction de poids 14 (les 14 colonnes à 1/2) qui ne respecte pas le syndrome. Le correctif `<` seul ne suffit pas sur ce DEM : les taux restent inchangés (1 301 et 1 303 erreurs sur 10 000, graines 101 et 102). Ce qui répare, c'est d'ôter la discontinuité : un a priori plafonné à 1/2 − 1e−5 garde un signe et se décode normalement (749 → 83 erreurs sur 6 000, graine 101).

#### La seconde cause, localisée dans le cœur (12/10)

Lu dans `min_sum.rs` (identique sur PyPI 0.2.2 et sur la branche principale d185194, au remaniement SIMD de `min_two_magnitudes` près, qui garde la même règle) :

1. `log_prior_ratios()` = ln((1 − p) / p). Un a priori d'exactement 1/2 donne exactement 0. Seul p = 0 (rapport infini) est traité à part, en `N::max_value()` ; le 0 ne l'est pas.
2. `compute_check_to_variable` : chaque message sortant d'un contrôle a pour magnitude le minimum (ou le second minimum) des magnitudes des *autres* messages entrants. Une colonne à 1/2 envoie une magnitude exactement 0 : tout contrôle qui la touche n'envoie donc plus rien aux autres colonnes, et elle-même ne reçoit une magnitude non nulle que d'un contrôle où elle est la seule à 1/2.
3. `compute_variable_prior` (Mem-BP) : a priori × (1 − γ) + a posteriori précédent × γ. Avec 0 et 0, cela reste 0 pour tout γ, y compris les gammas tirés au hasard par les jeux de Relay. Aucun nombre d'itérations ne change un 0 exact.
4. `compute_hard_decision` : `posterior <= 0` décide « erreur ». Pour un 0 exact c'est un départage qui n'a jamais regardé le syndrome ; `<` choisit l'autre côté, tout aussi arbitraire.

Sur le vrai DEM d'une fuite, les colonnes à exactement 1/2 forment un **ensemble bloquant** (*stopping set*) du graphe de Tanner : chaque détecteur qu'elles touchent est touché par au moins deux d'entre elles. C'est la configuration classique où la propagation de croyance s'arrête sur un canal à effacements, et un a priori de 1/2 est exactement un effacement ; min-sum en hérite. Tous les messages entrant dans l'ensemble valent 0 à chaque itération, ses a posteriori restent 0, il est décidé en bloc (tout « erreur » avec `<=`, tout « pas d'erreur » avec `<`), les détecteurs allumés autour de la fuite ne sont expliqués par personne, aucun des 60 jeux de Relay ne converge, et le décodeur rend la décision de sa phase de pré-itération (`relay.rs`, `decode_detailed`). Vérifié par `research/relay-bp-priors/stopping_set.py` (stim, numpy, beliefmatching ; réplique en numpy des règles de mise à jour de `min_sum.rs`, mémoire γ0 = 0,1, 80 itérations, 200 tirs par cas, graine 101) :

| d, événement | colonnes à 1/2 | détecteurs touchés | ensemble bloquant | a priori tels quels : messages entrants et a posteriori de l'ensemble | syndrome satisfait après 80 itérations, tels quels | plafonnés à 1/2 − 1e−5 |
|---|---|---|---|---|---|---|
| 5, ancilla centrale, round du milieu | 14 | 10 | oui | exactement 0 à chaque itération | 2 / 200 | 67 / 200 |
| 5, qubit de données central, round du milieu | 14 | 10 | oui | exactement 0 | 0 / 200 | 59 / 200 |
| 3, ancilla centrale | 12 | 7 | oui | exactement 0 | 1 / 200 | 79 / 200 |
| 3, qubit de données central | 14 | 10 | oui | exactement 0 | 0 / 200 | 75 / 200 |

(Les 80 itérations de la réplique ne couvrent que la phase de pré-itération ; les 60 jeux de Relay en ajoutent 3 600, qui ne changent rien à un 0 exact mais font converger davantage de tirs plafonnés.)

Pourquoi le plafond répare : 1/2 − 1e−5 donne un rapport logarithmique de 4e−5, minuscule mais non nul et du côté « pas d'erreur ». Les magnitudes ne sont plus nulles, les signes (les parités du syndrome) circulent, et sur l'ensemble bloquant min-sum se comporte comme un décodeur à signes seuls, qui le résout. Détail sans conséquence : `num_traits` donne `is_negative(−0.0) = true`, si bien que les zéros signés produits par `.neg()` font basculer des parités entre messages nuls ; les magnitudes restant nulles, les décisions n'en dépendent pas.

#### Correctif dans le cœur, compilé et mesuré (12/10)

`research/relay-bp-priors/fix-zero-llr-core.patch`, contre les sources 0.2.2 (sdist PyPI, sha256 `be47a267…`) : dans `MinSumBPDecoder::new`, tout rapport logarithmique de valeur absolue inférieure à 4e−5 est remplacé par +4e−5 (un a priori de 1/2 devient « très légèrement pas d'erreur », comme le plafond Python), et la décision dure devient `<` (stricte). Compilé sous Windows avec la chaîne GNU de rustup (rustc 1.99.0, maturin 1.15.0, Python 3.14 ; pas de roue Windows publiée, donc la sdist non patchée a été compilée de la même façon comme témoin : elle redonne au caractère près `results-repro_half_prior-pypi.txt`, empreinte `a3b3349e…` comprise). Sur l'arbre patché, `cargo test -p relay-bp --release` : 13 tests amont, 13 ok. Environnement complet dans `environnement-core-fix-windows.txt`.

| Build | A priori | Correction rendue | Succès | Empreinte de régression (300 problèmes sans 1/2) |
|---|---|---|---|---|
| sdist 0.2.2 compilée ici (témoin) | 1/2, 1/2, 1/2 | [1, 1, 1] | non, 3 680 itérations | `a3b3349e…` |
| sdist 0.2.2 compilée ici (témoin) | 1/2, 1/2, 0,01 | [1, 1, 0] | oui | |
| **cœur corrigé** | 1/2, 1/2, 1/2 | [0, 0, 0] | oui, 3 itérations | **`a3b3349e…`, inchangée** |
| **cœur corrigé** | 1/2, 1/2, 0,01 | [0, 0, 0] | oui | |

Mesure appariée (`measure_effect.py`, d = 5, p = 0,002, graines 101, 102, 103, 10 000 tirs chacune, décodeurs construits sur le DEM réel) avec le cœur corrigé et les probabilités combinées côté Python **sans** plafond Python (colonne `corrected`) ; la colonne `clamped` (plafond Python en plus) sert de témoin :

| Vrai bruit | `corrected`, cœur publié (Linux, 30/09) | **`corrected`, cœur corrigé** | `clamped`, cœur corrigé | `clamped`, cœur publié (Linux, 30/09) | PyMatching informé |
|---|---|---|---|---|---|
| fuite d'ancilla 1r | 12,84 % [12,47 ; 13,23] | **1,24 % [1,12 ; 1,38]** (120, 123, 130 erreurs) | 1,25 % (120, 123, 131) | 1,22 % (111, 128, 128) | 0,87 % |
| fuite de donnée centrale | 5,60 % [5,35 ; 5,87] | **1,26 % [1,14 ; 1,40]** (117, 120, 142) | 1,18 % (122, 110, 121) | 1,19 % (115, 118, 123) | 1,01 % |

Le correctif du cœur seul ramène relay-bp informé au niveau du plafond Python : 12,8 % → 1,24 % et 5,6 % → 1,26 %. Sur la fuite de donnée, `corrected` reste 26 erreurs au-dessus de `clamped` sur 30 000 (379 contre 353) : intervalles qui se recouvrent, pas de test apparié entre ces deux colonnes dans le script, donc non significatif en l'état ; deux différences fines possibles, ε en f64 juste en dessous de ln(0,50001/0,49999) et le `<` strict qui touche tout a posteriori exactement nul. Limite connue du patch : en virgule fixe (`int_bits`/`frac_bits`), `N::from_f64(4e−5)` peut retomber à 0 ; il ne couvre vraiment que F32 et F64, ce qu'utilise le module stim (`RelayDecoderF64`). Un correctif plus propre traiterait les a priori de 1/2 comme des effacements à peler avant BP.

Correctif complet mesuré (probabilités combinées, biais en tableaux, a priori plafonnés à 1/2 − 1e−5 ; `ClampedCheckMatrices`), rejoué depuis zéro : d = 5, une ancilla tirée au sort rendue aléatoire pendant un round tiré au sort, graines 101, 102 et 103, 10 000 tirs chacune.

| relay-bp informé, publié | exception seule corrigée | combinées | **combinées et plafonnées** | relay-bp réglé (ignore la fuite) | PyMatching réglé | PyMatching informé |
|---|---|---|---|---|---|---|
| exception (3/3) | 8,83 % [8,51 ; 9,15] | 12,84 % [12,47 ; 13,23] | **1,22 % [1,11 ; 1,35]** | 3,94 % [3,73 ; 4,17] | 3,84 % | 0,85 % [0,75 ; 0,96] |

Mêmes graines, deux autres événements :

| Vrai bruit | relay-bp publié | exception seule corrigée | combinées et plafonnées | relay-bp réglé | PyMatching informé |
|---|---|---|---|---|---|
| qubit de données central aléatoire au round du milieu | exception (3/3) | 11,37 % | **1,19 % [1,07 ; 1,32]** | 2,71 % | 0,98 % |
| rafale à 0,5 sur un qubit et ses voisins, un round | exception (3/3) | 3,01 % | **2,82 % [2,64 ; 3,01]** | 7,73 % | 2,54 % |

Avec le correctif complet, relay-bp tire enfin parti de la connaissance de la fuite (3,94 % → 1,22 %, facteur 3,2), comme PyMatching (facteur 4,5). Le rejeu de la graine 101 redonne au tir près les comptes des passages précédents (866, 1 302, 75).

### 5. Sur le code principal d'IBM, le gross code [[144, 12, 12]]

Circuit repris tel quel des données de test de relay-bp (`third_party/relay_bp/`, Apache 2.0), mémoire Z, 12 rounds, bruit uniforme p = 0,003. Son DEM n'est pas décomposable : relay-bp prend le chemin sans somme et **ne plante pas**. Mais un qubit rendu aléatoire pendant un round donne 59 colonnes d'a priori exactement 1/2, le cas du défaut de cœur. Rejoué sur trois graines indépendantes (`research/relay-bp-priors/gross_half_prior.py`) :

| Graine, événement | Informé, tel quel | Informé, plafonné sous 1/2 | Réglé sur le nominal |
|---|---|---|---|
| 5, fuite d'ancilla (pilote, 30 tirs) | 14 erreurs, 30 échecs sur 30 | 0 erreur, 0 échec | 0 erreur, 0 échec |
| 6, fuite d'ancilla (60 tirs) | 18 erreurs, 60 échecs sur 60 | 0, 0 | 0, 0 |
| 7, fuite de qubit de données (60 tirs) | 42 erreurs, 60 échecs sur 60 | 0, 0 | 0, 0 |
| **cumul, 150 tirs** | **74 (49 % [41 ; 57]), 150 échecs** | **0 [0 ; 2,5 %]** | **0** |

Chaque décodage informé tel quel épuise tout le budget d'itérations (3 680) : 11,5 s par tir contre 0,8 à 1,5 s pour les deux autres. Sur 150 tirs appariés, informé tel quel faux et plafonné juste : 74 fois ; l'inverse : 0 fois (McNemar p ≈ 1e−22).

### 6. Déjà vu ? Déjà corrigé ?

- Aucune issue du dépôt `trmue/relay` (12 issues, ouvertes et fermées, lues le 29/09) ne traite de ce point.
- La branche principale a corrigé un défaut voisin (le biais des observables calculé sur la mauvaise matrice, « Fix syndrome pruning (#42) »), pas celui-ci : la même exception s'y produit.
- Documentation lue : le README (PyPI 0.2.2) et les docstrings de `from_dem` et `prune_decided_errors`. La docstring décrit l'élagage des probabilités « 1 − seuil → 1 », c'est-à-dire des erreurs vraiment certaines ; rien n'annonce une somme ni une limite sur les DEM acceptés. Leçon du constat 001 appliquée : ce n'est pas un choix documenté.

## Ce qui n'est pas établi

| # | Point | Pourquoi |
|---|---|---|
| N1 | L'écart qui reste entre relay-bp corrigé et PyMatching, tous deux informés (1,22 % contre 0,85 %) | non étudié ; relay-bp est conçu pour les codes qLDPC, pas pour le code de surface |
| N2 | L'effet sur les codes qLDPC (code « gross »), la cible principale de relay-bp | Mesuré seulement sur le code de surface |
| N3 | Le cas `decomposed_hyperedges=False`, où la somme n'a pas lieu | Non testé : sinter décompose par défaut, et relay-bp choisit ce chemin tout seul |

## Correctif proposé

Trois changements, dont deux dans `check_matrices.py` : combiner les probabilités (1/2 (1 − Π(1 − 2 pᵢ)), calculé en logarithmes) et rendre les biais en tableaux numpy à une dimension. Troisième : plafonner les a priori à 1/2 − 1e−5 (ou, dans le cœur, décider l'égalité en « pas d'erreur » et traiter explicitement les messages nuls). Version de mesure dans [research/relay-bp-priors/corrected.py](../research/relay-bp-priors/corrected.py) (`ClampedCheckMatrices`). Avec ce correctif, plus aucune arête ne dépasse 1/2 et il n'y a plus d'exception. Sous bruit nominal (d = 5, p = 0,002), somme et combinaison diffèrent d'au plus 2 % par arête ; sur 20 000 tirs (graine 5), 23 prédictions changent, pour 97 erreurs avec la version publiée contre 88 avec la version corrigée, écart non significatif.

## Rejouer

```
.venv/bin/python research/relay-bp-priors/repro_crash.py
.venv/bin/python research/relay-bp-priors/repro_half_prior.py
.venv/bin/python research/relay-bp-priors/measure_effect.py --distance 5 --shots 10000 --seeds 101 102 103
```

Le premier dure 2 secondes. Le second environ une heure sur 4 cœurs ; ses sorties sont dans `research/relay-bp-priors/results-*.txt`.
