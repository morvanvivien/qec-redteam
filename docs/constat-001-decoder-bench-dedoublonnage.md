# Constat 001 — decoder-bench mesure ses taux sur des syndromes dédoublonnés

Date : 28 septembre 2026. Statut : **signalé aux mainteneurs le 28/09**, issues [#2](https://github.com/satvikmaurya/decoder-bench/issues/2) et [#3](https://github.com/satvikmaurya/decoder-bench/issues/3).

Ce constat porte sur un banc de mesure, pas sur un décodeur. Ce n'est pas la cassure visée par la brique 2.

## En une phrase

Les traces de decoder-bench ne gardent qu'un exemplaire de chaque syndrome. Le « taux d'erreur logique » publié est donc un taux par syndrome unique, plus élevé que le taux de Monte Carlo dès que le bruit est faible : environ +21 % à p = 0,001 et +83 % à p = 0,0005 pour PyMatching à d = 7.

## Portée réelle : un choix documenté, une conséquence non chiffrée

Le dédoublonnage n'est **pas un défaut caché**. L'auteur le décrit comme un choix voulu dans sa thèse (annexe A.2.1.3) :

> « Since this sampling is random, the same syndrome can be sampled multiple times, especially for small code distances. To avoid this, decoder-bench hashes the syndromes it has seen already and stores them in a hash map. This allows decoder-bench to store only unique syndromes. Syndromes and observables have a 1:1 mapping, so discarding a duplicate syndrome discards the corresponding observable as well. »

Avantages avancés : décodeurs testés sur une plus grande variété de motifs, comparés sur le même jeu de problèmes, redondances éliminées.

Ce que nous apportons se limite donc à trois points :

1. **La conséquence chiffrée.** Ni la thèse ni le README du dépôt ne disent que le taux mesuré sur une trace dédoublonnée n'est pas le taux de Monte Carlo. Le README ne mentionne pas le dédoublonnage du tout. Un lecteur qui compare le CSV publié à la littérature se trompe de 21 à 83 % à bas bruit.
2. **Une affirmation inexacte.** Un syndrome n'a pas un observable unique : le même syndrome peut venir d'erreurs de classes logiques différentes, c'est la définition même d'une erreur logique. Ne garder que la première occurrence jette cette information.
3. **Une option inopérante.** `--store_unique False` ne désactive rien (voir plus bas).

C'est une contribution modeste et constructive, pas une découverte.

## Ce qui est établi

Cible : code de surface tourné, d = 7, 7 rounds, mémoire Z, bruit SI1000, décodeur PyMatching. Notre circuit est identique au leur au caractère près, pour les quatre valeurs de p vérifiées.

### 1. Les traces publiées ne contiennent aucun doublon

Traces de l'archive Zenodo 10.5281/zenodo.16914504, comparées à un tirage frais d'un million de syndromes sur le même circuit.

| p | Trace publiée : enregistrements | doublons | syndromes nuls | Tirage frais : syndromes uniques sur 1 000 000 | syndromes nuls |
|---|---|---|---|---|---|
| 0,0009 | 856 892 | 0 | 1 | 857 383 | 26 207 |
| 0,001 | 898 240 | 0 | 1 | 897 615 | 17 293 |
| 0,003 | 999 993 | 0 | 1 | 999 994 | 6 |
| 0,005 | 1 000 000 | 0 | 0 | 1 000 000 | 0 |

Un tirage de Monte Carlo à p = 0,001 contient 17 293 syndromes nuls sur un million. La trace publiée en contient un seul. Le nombre d'enregistrements de chaque trace correspond, à 0,07 % près, au nombre de syndromes uniques d'un tirage d'un million.

### 2. Le code le fait par défaut, et l'option pour l'éviter ne marche pas

- `dataset_gen.py`, `gen_syndromes(..., store_unique=True)` : seul un syndrome jamais vu est stocké, avec l'observable de sa première occurrence.
- `generator.py`, ligne 168 : `parser.add_argument('--store_unique', type=bool, default=True, ...)`. Avec argparse, `bool("False")` vaut `True`. La commande `--store_unique False` laisse donc le dédoublonnage actif.

### 3. Le taux publié s'écarte du Monte Carlo à bas p, et l'émulation du dédoublonnage le retrouve

Taux d'erreur logique par tir. Publié : `benchmark_results.csv`, 5 000 000 enregistrements. z : écart au chiffre publié en écarts types.

| p | Publié | Monte Carlo (nous) | z | Dédoublonné (nous) | z |
|---|---|---|---|---|---|
| 0,005 | 0,0499594 | 0,0500146 (250 073 / 5 000 000) | +0,4 | 0,0500146 | +0,4 |
| 0,003 | 0,0079552 | 0,0079372 (47 623 / 6 000 000) | −0,3 | 0,0079448 | −0,2 |
| 0,001 | 1,264 × 10⁻⁴ | 1,040 × 10⁻⁴ (5 201 / 50 000 000) | **−4,6** | 1,172 × 10⁻⁴ | −1,3 |
| 0,0005 | 1,06 × 10⁻⁵ | 0,578 × 10⁻⁵ (289 / 50 000 000) | **−4,1** | 1,38 × 10⁻⁵ | +1,4 |

Là où le dédoublonnage est sans effet (p = 0,003 et 0,005), notre Monte Carlo retrouve le chiffre publié. Là où il agit, notre Monte Carlo s'en écarte, et la même mesure faite sur les syndromes uniques le retrouve.

Rapport publié sur Monte Carlo : 1,22 ± 0,05 à p = 0,001 et 1,83 ± 0,27 à p = 0,0005. L'incertitude vient surtout du chiffre publié, qui ne repose que sur 632 et 53 erreurs.

Les deux lignes à bas p viennent du Monte Carlo de 50 millions de tirs (`redteam.montecarlo`, 69 secondes). La mesure couplée de `redteam.reproduce`, sur 6 et 12 millions de tirs, donnait 0,997 × 10⁻⁴ et 0,592 × 10⁻⁵, compatibles.

### 4. Les syndromes d'une trace sont plus lourds que ceux d'un tirage

Poids moyen d'un syndrome : 9,08 dans la trace contre 8,36 en Monte Carlo à p = 0,001 ; 8,47 contre 7,54 à p = 0,0009. Le temps de décodage par tir mesuré sur une trace est donc lui aussi décalé vers le haut.

Temps de décodage PyMatching par tir sur ce poste, meilleur de 5 passes, trace publiée d'un million de tirs contre tirage frais de même taille :

| p | Trace publiée | Tirage frais | Écart |
|---|---|---|---|
| 0,0009 | 2,89 µs | 2,60 µs | +11 % |
| 0,001 | 3,09 µs | 2,87 µs | +8 % |
| 0,003 | 10,02 µs | 10,00 µs | 0 % |

L'écart grandit avec le nombre de tirs bruts consommés pour remplir la trace, donc il est plus fort sur les traces de 5 millions d'enregistrements que sur celles d'un million.

## Ce qui n'est pas établi

| # | Point ouvert | Pourquoi |
|---|---|---|
| N1 | L'article IISWC 2025 discute peut-être l'effet sur le taux | Article non lu, accès IEEE refusé. La thèse de l'auteur, lue le 28/09, décrit le dédoublonnage sans en chiffrer l'effet |
| N2 | Les résultats publiés sur 5 000 000 enregistrements viennent de traces dédoublonnées | Déduit des mesures, pas observé : l'archive Zenodo ne contient que les traces d'un million de tirs |
| N3 | L'effet sur les autres décodeurs et les autres codes (d = 11, qLDPC, couleur) | Non mesuré |
| N4 | L'effet sur le classement entre décodeurs | Non mesuré. Tous sont évalués sur la même trace, le classement est probablement peu touché |

## Rejouer

```
.\.venv\Scripts\python.exe -m redteam.reproduce --out out/decoder_bench
.\.venv\Scripts\python.exe -m redteam.trace <data>\traces
```

La première commande dure environ deux minutes et écrit `out/decoder_bench/reproduction.md`. La seconde demande les quatre traces d = 7 de l'archive Zenodo (100 Mo) et écrit `out/decoder_bench/traces.md`.

## Suite proposée

1. Fait le 28/09 : Monte Carlo de 50 millions de tirs à bas p.
2. Fait le 28/09 : effet sur le temps de décodage par tir.
3. Lire l'article IISWC pour lever N1.
4. Signaler aux mainteneurs, sur leur dépôt, le défaut de l'option `--store_unique` et l'effet du dédoublonnage, avec une correction proposée : stocker pour chaque syndrome unique son nombre d'occurrences et le nombre d'occurrences où l'observable est retourné, ce qui garde des traces compactes et rend le taux de Monte Carlo exact. Fait le 28/09, voir [brouillon-issue-decoder-bench.md](brouillon-issue-decoder-bench.md).
