# Constat 002 — Cause et correctif de la corruption du tas de ldpc (#105)

Date : 28 septembre 2026. Statut : **signalé le 29/09** sous l'issue ldpc #105, texte dans [issues/ldpc-105-comment.md](issues/ldpc-105-comment.md). Correctif proposé le 31/10 : [PR 116](https://github.com/quantumgizmos/ldpc/pull/116), texte dans [issues/ldpc-pr-116.md](issues/ldpc-pr-116.md).

## En une phrase

Le plantage de ldpc que nous avons rencontré était déjà signalé (issue #105, 5 août 2026, sans réponse). Nous en avons trouvé la cause dans le code C++, écrit un correctif de quelques lignes, et prouvé par exécution qu'il supprime l'écriture hors limites sans changer un seul résultat de décodage.

## Comment on est tombé dessus

En branchant les décodeurs publics sur le banc de la brique 2, BP+LSD de la bibliothèque ldpc a fait tomber Python avec le code Windows `0xC0000374` (corruption du tas). Paramétrage légitime, identique à celui de decoder-bench : `osd_method="osd_cs"`, `osd_order=10`, alias documentés de `lsd_method="lsd_cs"`, `lsd_order=10`.

Avant toute conclusion, recherche dans les issues de ldpc : l'issue #105 décrit exactement ce défaut. **Ce n'est donc pas une trouvaille.** Ce qui manquait dans #105, c'est la cause, l'étendue réelle et un correctif.

## La cause

Dans `src_cpp/osd_dense.hpp`, lignes 84 à 95, le balayage combinatoire crée des vecteurs candidats de longueur `k`, puis écrit `candidat[i] = 1` et `candidat[j] = 1` pour toutes les paires `i < j < ordre`. Rien ne vérifie que `i` et `j` restent sous `k`.

Dans LSD, `k` est la dimension d'**un cluster**, qui peut être bien plus petite que l'ordre demandé. Dès que `k < ordre`, le code écrit hors du vecteur. Le même défaut existe dans `src_cpp/osd.hpp`, lignes 90 à 99, pour BP+OSD.

Cette cause explique toutes les observations de #105 et les nôtres :

| Observation | Explication |
|---|---|
| Ordres 0 et 1 propres, 2 et plus corrompus | à l'ordre 1, la double boucle ne produit aucune paire |
| Mode exhaustif `lsd_e` propre | sa boucle s'arrête à la longueur `k` du vecteur |
| Linux silencieux, Windows plante | glibc laisse 24 octets utilisables à toute petite allocation : jusqu'à l'ordre 24, l'écriture reste dans la marge. Le tas Windows en laisse moins, l'écriture touche l'en-tête du bloc voisin |
| BP+OSD jugé propre dans #105 | sur une matrice entière, `k` est grand, donc rarement inférieur à l'ordre |

## Les preuves

### 1. Sur la bibliothèque publiée (roue 2.4.1, Windows)

BP+OSD en mode `osd_cs`, sur des matrices dont on choisit `k`, un processus par cas :

| Ordre | Plante | Propre |
|---|---|---|
| 64 | k = 1 à 48 | k = 60 et plus |
| 16 | k = 1 à 8 | k = 16 et plus |

Les cas k = 60 et 63 à l'ordre 64 débordent de 1 à 4 octets seulement, ce que la marge de l'allocateur absorbe. Deux cellules ont planté en violation d'accès (`0xC0000005`) au lieu de l'arrêt habituel : la corruption peut atteindre d'autres données que les en-têtes du tas.

BP+LSD d'ordre 10 sur un code de surface d = 5 : **un seul décodage d'un seul syndrome** (tir 29) fait planter un processus neuf. Le même syndrome passe en LSD_CS d'ordre 1, en mode exhaustif d'ordre 10 et en LSD_0.

### 2. Avant et après correctif, sur les en-têtes C++ compilés

Compilation d'un petit programme C++ qui appelle les deux décodeurs, avec le compilateur zig installé dans l'environnement du projet (aucune installation système). Avec une bibliothèque standard « durcie », tout accès hors limites s'arrête immédiatement, quel que soit l'allocateur.

| Contrôle | Code d'origine | Code corrigé |
|---|---|---|
| Accès hors limites, chemin LSD | piège pour k < 10 | jamais |
| Accès hors limites, chemin BP+OSD | piège pour k < 10 | jamais |
| Sorties, 46 configurations × 500 décodages | — | identiques octet pour octet |

## Le correctif

Borner les deux boucles de paires par `min(ordre, k)`. Quand l'ordre ne dépasse pas `k`, il produit exactement les mêmes candidats, dans le même ordre. Quand l'ordre dépasse `k`, il ne retire que des candidats inutiles : des doublons des candidats à un seul bit, ou le vecteur nul. La règle de sélection ne retient qu'un poids strictement plus faible, donc ces candidats ne changent jamais le résultat. Patch : [research/ldpc-105/fix-combination-sweep-bounds.patch](../research/ldpc-105/fix-combination-sweep-bounds.patch).

## Conséquence pour les résultats publiés

C'était la question laissée ouverte par #105 : une corruption silencieuse sous Linux a-t-elle faussé des résultats publiés ? Notre réponse, avec ses limites :

- les candidats hors limites ne changent pas la sortie ;
- sous glibc, jusqu'à l'ordre 24, les écritures restent dans la propre allocation du vecteur et n'abîment rien d'autre ;
- donc les résultats `lsd_cs` produits sous Linux à ces ordres, dont ceux de decoder-bench (ordre 10), ne devraient pas être faussés ;
- au delà de l'ordre 24, ou sous un autre allocateur, rien ne peut être affirmé en général.

## Ce qui n'est pas fait

| # | Point | Pourquoi |
|---|---|---|
| N1 | Construire l'extension Python corrigée et lancer les tests de ldpc | pas de compilateur MSVC sur le poste ; seuls les en-têtes ont été compilés |
| N2 | Vérifier sous Linux avec `MALLOC_CHECK_=3` ou AddressSanitizer | pas de Linux sur le poste |
| N3 | Mesurer la distribution des dimensions de clusters dans LSD | les statistiques de ldpc ne l'exposent pas |

## Ce que ça change pour le projet

C'est la première vraie contribution technique de la red team : la cause d'un défaut de sécurité mémoire dans la bibliothèque de référence du décodage BP+OSD et BP+LSD (225 étoiles), avec un correctif vérifié. Si le mainteneur l'accepte, c'est la brique 3 atteinte en avance : du code à nous dans une bibliothèque de décodeurs.

Ce n'est pas la cassure visée par la brique 2 (un bruit plausible qui fait s'effondrer un décodeur). Elle reste à trouver.

## Rejouer

```
.\.venv\Scripts\python.exe research\ldpc-105\repro_osd_k.py
.\.venv\Scripts\python.exe research\ldpc-105\repro_lsd_single_decode.py
.\.venv\Scripts\python.exe research\ldpc-105\verify_fix.py <data>\build
```

La troisième commande suppose les quatre exécutables compilés, voir [research/ldpc-105/README.md](../research/ldpc-105/README.md).
