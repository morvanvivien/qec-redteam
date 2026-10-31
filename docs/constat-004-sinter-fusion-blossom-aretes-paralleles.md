# Constat 004 — sinter donne à fusion-blossom des arêtes parallèles non fusionnées

Date : 30 septembre 2026. Statut : **signalé le 01/10** : [Stim #1116](https://github.com/quantumlib/Stim/issues/1116), texte dans [issues/stim-fusion-blossom-parallel-edges.md](issues/stim-fusion-blossom-parallel-edges.md). Pas de PR de notre part : le `CONTRIBUTING.md` de Stim exclut le code généré par IA.

## En une phrase

L'adaptateur de sinter qui branche fusion-blossom sur un modèle d'erreurs stim crée une arête par composante d'erreur, sans jamais fusionner celles qui relient les deux mêmes détecteurs : sous un bruit fortement biaisé, fusion-blossom se trompe alors jusqu'à 3,4 fois plus souvent (26 % de plus à d = 5) que le même algorithme avec des arêtes fusionnées, qui égale exactement PyMatching.

## Comment on est tombé dessus

Piste ouverte QEC-2026-015 du registre : sous biais Z (η = 1000), fusion-blossom informé du biais faisait moins bien que réglé sur le bruit nominal (pénalité 0,77 [0,69 ; 0,86]), alors que PyMatching informé et réglé coïncidaient. Aucune conclusion n'a été tirée avant d'avoir lu le code et la documentation.

## La cause, lue puis vérifiée

`glue/sample/src/sinter/_decoding/_decoding_fusion_blossom.py`, fonction `detector_error_model_to_fusion_blossom_solver_and_fault_masks` (sinter 1.16.0 et branche principale de stim au commit 131793e du 22/09/2026) : chaque composante d'erreur du DEM devient une arête `(a, b, log((1 − p)/p))` ajoutée à une liste, sans regroupement. Le modèle du cas étudié donne 3 724 arêtes pour 502 paires de détecteurs distinctes, dont 480 portent plusieurs arêtes. fusion-blossom accepte ces arêtes parallèles et n'utilise que la moins chère : il voit la probabilité de la composante la plus probable au lieu de leur probabilité combinée, 1/2 (1 − Π(1 − 2 pᵢ)).

Ce n'est pas un choix documenté :

- le seul commentaire du fichier sur le sujet concerne la décomposition (« Treat each component of a decomposed error as an independent error »), pas la fusion ;
- l'adaptateur mwpf du même dossier, ajouté plus tard, fusionne explicitement les hyperarêtes identiques (`deduplicate_hyperedges`) ;
- PyMatching fusionne les arêtes parallèles ;
- fusion-blossom 0.2.13 : aucune mention des arêtes parallèles dans sa documentation publiée (README, docstrings vides).

Recherche dans les issues de `quantumlib/Stim` (« fusion_blossom », « fusion blossom edges ») le 30/09 : rien sur ce point.

## L'effet, rejoué depuis zéro

Code de surface tourné d = 5, 5 rounds, mémoire X, SI1000 à p = 0,002 dont la dépolarisation est remplacée par un canal de Pauli biaisé vers Z (η = 1000, même probabilité totale). Trois décodeurs construits sur le DEM réel, mêmes tirs, graines 11, 12 et 13, 26 000 tirs chacune (`research/sinter-fusion-blossom/parallel_edges.py`).

| Graine | fusion-blossom via sinter | fusion-blossom, arêtes fusionnées | PyMatching |
|---|---|---|---|
| 11 | 285 | 216 | 215 |
| 12 | 276 | 223 | 224 |
| 13 | 293 | 239 | 238 |
| **cumul, 78 000 tirs** | **1,095 % [1,024 ; 1,170]** | **0,869 % [0,806 ; 0,937]** | 0,868 % |

Rapport 1,26 ; sur les tirs discordants, 224 fois seul l'adaptateur de sinter se trompe, 48 fois seule la version fusionnée (McNemar p = 2e−28).

L'effet dépend de la force du biais (d = 5, mêmes graines, 78 000 tirs chacun) :

| Biais η | via sinter | arêtes fusionnées | rapport | McNemar p |
|---|---|---|---|---|
| 10 | 0,733 % | 0,738 % | 0,99 | 0,67 |
| 100 | 0,969 % | 0,812 % | **1,19** | 2e−18 |
| 1000 | 1,095 % | 0,869 % | **1,26** | 2e−28 |

Et de la distance (η = 1000, mêmes graines, 78 000 tirs chacune) : l'écart est le plus fort sur le plus petit code.

| d | Paires avec arêtes parallèles | via sinter | arêtes fusionnées | PyMatching | rapport | McNemar p |
|---|---|---|---|---|---|---|
| 3 | 72 sur 78 | 5,07 % | 1,50 % | 1,50 % | **3,38** | < 1e−300 |
| 5 | 480 sur 502 | 1,095 % | 0,869 % | 0,868 % | 1,26 | 2e−28 |
| 7 | 1 512 sur 1 558 | 0,412 % | 0,386 % | 0,386 % | 1,07 | 0,008 |

À chaque distance, la version fusionnée égale PyMatching au tir près ou presque, ce qui valide la mesure. Pourquoi l'écart décroît avec la distance n'est pas établi (N1).

Même chose sous SI1000 ordinaire, mémoire Z, graines 21 à 23 : 340 contre 337 erreurs sur 78 000, rapport 1,009, McNemar p = 0,83. **Aucun effet mesurable sous bruit dépolarisant** : les composantes parallèles y ont des probabilités très inégales, et la plus probable domine la somme.

## Sur le code XZZX, fait pour le bruit biaisé (01/10)

Le code XZZX est le code de surface avec une porte de Hadamard sur un qubit de données de chaque paire diagonale : c'est le code proposé pour les qubits à biais de bruit. Même bruit (η = 1000, p = 0,002, mémoire X), mêmes trois décodeurs, mêmes graines 11, 12 et 13, 26 000 tirs chacune (`research/sinter-fusion-blossom/xzzx.py`, sorties dans `xzzx-runs/`).

| d | via sinter | arêtes fusionnées (= PyMatching) | rapport XZZX | rapport code de surface ordinaire | McNemar p |
|---|---|---|---|---|---|
| 3 | 5,09 % [4,94 ; 5,25] | 0,81 % [0,75 ; 0,88] | **6,27** | 3,38 | < 1e−300 |
| 5 | 0,380 % [0,339 ; 0,425] | 0,173 % [0,146 ; 0,205] | **2,19** | 1,26 | 9e−33 |
| 7 | 0,064 % [0,049 ; 0,085] | 0,044 % [0,031 ; 0,061] | **1,47** | 1,07 | 9e−4 |

Le défaut coûte deux fois plus sur le code fait pour ce bruit : le gain du code XZZX (à d = 5, 0,173 % au lieu de 0,869 % avec le code ordinaire) est à moitié perdu via sinter. À d = 7, 84 erreurs seulement au total : le rapport est significatif mais son intervalle est large.

La construction conjugue le bruit plutôt que les portes : sur les qubits de données concernés, les parts X et Z de chaque canal de Pauli sont échangées ; les retournements de préparation et de mesure ne changent pas. Contrôle : PyMatching profite bien du code XZZX (0,81 % contre 1,50 % à d = 3), comme attendu.

## Portée

- Touche quiconque décode avec `sinter.collect(decoders=["fusion_blossom"])` un bruit où plusieurs mécanismes de probabilités comparables tombent sur la même arête : bruit biaisé (qubits de chat, qubits à biais de bruit), modèles d'erreurs calibrés sur une vraie puce.
- Ne touche pas fusion-blossom lui-même, ni PyMatching, ni l'adaptateur mwpf.
- Le correctif est local : regrouper les composantes par paire de détecteurs et par effet sur les observables avant de calculer les poids, comme le fait déjà l'adaptateur mwpf.

## Ce qui n'est pas établi

| # | Point | Pourquoi |
|---|---|---|
| N1 | Pourquoi l'écart décroît avec la distance (×3,4 à d = 3, ×1,07 à d = 7) | Non étudié ; hypothèse : à petite distance, une seule arête mal pesée suffit à changer la chaîne choisie |
| N2 | ~~L'effet sur des codes adaptés au biais (XZZX)~~ | Mesuré le 01/10 : plus fort que sur le code ordinaire (×6,3 à d = 3, ×2,2 à d = 5, ×1,5 à d = 7) |
| N3 | Quand deux composantes parallèles ont des effets différents sur les observables, la version fusionnée garde la plus probable | Choix de notre correctif ; ne change pas le résultat ici (elle égale PyMatching) |

## Rejouer

```
.venv/bin/python research/sinter-fusion-blossom/parallel_edges.py --seeds 11 12 13 --shots 26000
.venv/bin/python research/sinter-fusion-blossom/parallel_edges.py --nominal --seeds 21 22 23 --shots 26000
.venv/bin/python research/sinter-fusion-blossom/xzzx.py --distance 5 --seeds 11 12 13 --shots 26000
```

Environ 20 minutes chacune sur un cœur ; sorties dans `research/sinter-fusion-blossom/results-*.txt`.
