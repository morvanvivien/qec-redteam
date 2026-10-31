# Sources QEC pour reproduction : extraction factuelle

Lecture faite le 27/09/2026. Aucun outil QEC n'a été installé ni exécuté. Les textes ont été lus en brut (HTML arXiv, texte extrait du PDF, fichiers du dépôt GitHub) et les copies locales sont dans `scratchpad\qec-src\`.

Convention : « vérifié » signifie lu mot pour mot dans la source. « Déduit » signifie calculé ou inféré par moi à partir de la source. « Estimé » signifie ordre de grandeur de ma part, à confirmer par exécution.

## Vue d'ensemble

| Source | Objet réel | Code public | Utilise stim et pymatching | Coût sur PC |
|---|---|---|---|---|
| arXiv 2504.19651 | Attaque par sélection d'erreurs contre un seul décodeur, DeepQ (apprentissage par renforcement) | Non pour l'attaque. Oui pour DeepQ d'origine | Non | Calcul léger, pile logicielle ancienne |
| decoder-bench | Générateur de traces HDF5 et banc de mesure de décodeurs | Oui, MIT | Oui | Minutes pour PyMatching, jours CPU pour les autres |
| arXiv 2609.07035 | Test de conformité de 9 configurations de 5 bibliothèques | Oui, Zenodo et GitHub | Oui | Une station de travail, budget d'une journée |
| arXiv 2603.20127 | Analyse par énumération et optimisation polynomiale, précision et robustesse à l'incertitude sur p | Dépôt anonyme préliminaire | stim oui, pymatching oui | Grappe 16 cœurs, plafond 24 h par instance |
| arXiv 2609.19090 | Garde fou contre un conseiller IA trompeur | Aucun lien | Non lu | Non évalué |

## Alerte de cadrage

L'article 2504.19651 n'attaque ni PyMatching, ni Union-Find, ni BP-OSD, ni aucun décodeur branché sur stim. Il attaque uniquement DeepQ, un décodeur par apprentissage par renforcement de 2018, sous un bruit sans erreur de mesure. MWPM n'y sert que d'arbitre (referee). Toute reproduction doit donc passer par l'environnement DeepQ et non par la chaîne stim, sinter, pymatching.

---

## 1. arXiv 2504.19651 : Fooling the Decoder

### Identité (vérifié)

* Titre : « Fooling the Decoder: An Adversarial Attack on Quantum Error Correction ».
* Auteurs : Jerome Lenssen (VTT, Espoo) et Alexandru Paler (Aalto University).
* Versions : v1 du 28/04/2025, v2 du 08/09/2026. Catégorie quant-ph.
* URL : https://arxiv.org/abs/2504.19651 et https://arxiv.org/html/2504.19651v2

### Code et expérience

* Code de surface avec d² qubits de données (vérifié par la formule du nombre de motifs, C(d², n) × 2^n, qui donne 50, 1 200 et 18 400 à d=5). Donc 25 qubits de données à d=5. Le mot « rotated » n'apparaît nulle part dans l'article. La disposition d par d avec qubits sur les sommets et stabilisateurs en plaquettes vient du README de DeepQ, ce qui correspond à la disposition compacte du code tourné (déduit).
* Distance attaquée : d=5 uniquement. Contrôles de robustesse à d=3, 5, 7. Entraînement jusqu'à d=9 pour estimer le seuil.
* Type d'expérience : mémoire (« surface code memory experiment »). Il n'y a pas de nombre de rounds fixé, l'épisode dure jusqu'à l'échec. La métrique est la durée de vie du qubit logique en cycles de mesure.
* Le texte ne précise pas la base (X ou Z). DeepQ corrige X et Z, et l'arbitre MWPM utilise deux graphes séparés.

### Modèle de bruit (vérifié)

* Formulation des auteurs : « phenomenological depolarising noise, without measurement errors ». La conclusion admet : « All experiments use code capacity noise ». En pratique c'est donc du code capacity dépolarisant sur les qubits de données.
* Valeur principale : p = 0.001.
* Contrôle MAX : p = 0.006.
* Figure 4 : influence de p sur l'attaque pour N dans {8, 16, 32}, valeurs lisibles seulement sur la figure.
* Contrôles de robustesse : p de 0.001 à 0.013 par pas de 0.001, 200 épisodes par taux, nouveau tirage du modèle de bruit tous les 10 épisodes.
* Bruit spatialement inhomogène : probabilités tirées dans N(p_phys, σ²) avec σ entre 0.0001 et 0.0005, variantes dépolarisante, bit flip et phase flip, plus trois motifs (cross, quadrant, concentric) avec biais β.
* Bruit dépendant du temps : p_t = p_phys + β sin(2π ω t + r_i), avec déphasage r_i par qubit.

### Décodeurs (vérifié)

* Cible unique : DeepQ de Sweke, Kesselring, van Nieuwenburg, Eisert (Machine Learning: Science and Technology, 2020, arXiv 1810.07207).
* Arbitre d'origine : réseau de neurones feedforward. Remplacé par un MWPM, poids d'arête 1 par défaut, deux graphes (X et Z, Y décomposé), nœuds de bord reliés entre eux par un poids 0. Aucune bibliothèque MWPM n'est nommée, aucune version.
* AlphaQubit n'est cité que comme contexte.

### Construction de l'attaque (vérifié)

* Type : boîte blanche, hors ligne. Les auteurs la décrivent comme un « white-box, offline stress test » et comme une borne supérieure de robustesse, pas comme un exploit déployable.
* Espace de perturbation : le choix de la configuration d'erreurs de Pauli réellement appliquée aux qubits de données. L'attaque ne retourne aucun bit de syndrome en transit.
* Contrainte : chaque candidat est un tirage authentique du modèle de bruit non modifié à p = 0.001. Le budget est N candidats par round. Il n'y a aucune borne de norme. Pour la section III.4 seulement, contrainte ajoutée de 2 erreurs au plus par round.
* Algorithme d'optimisation : sélection combinatoire, sans gradient. FGSM est écarté parce que le volume de syndromes est un tenseur binaire. Algorithme 1 :
  1. Entrées : environnement E, fonction Q, N > 0.
  2. Chaîne T vide.
  3. Tant que l'épisode n'est pas fini : tirer N volumes de syndromes depuis E.
  4. Calculer j* = argmin sur j de max sur a de Q(σ(E_j), a).
  5. Appliquer l'erreur E_j* à l'état caché.
  6. Appliquer l'action gloutonne associée.
  7. Ajouter E_j* à T.
  8. Retourner T.
* Quatre sélecteurs testés : MIN (plus petite valeur Q), MAX (plus grande), MIN-VAR et MAX-VAR (variance des valeurs Q). 500 répétitions par couple (méthode, N).
* Modèle de menace, cinq hypothèses : A1 accès en lecture aux poids, A2 pouvoir de choisir quelle erreur physique se réalise, A3 budget d'échantillonnage N, A4 exécution hors ligne, A5 une seule cible et un seul bruit.

### Résultats chiffrés (vérifié)

| Grandeur | Valeur |
|---|---|
| Durée de vie de référence, d=5, p=0.001 | environ 10^5 cycles |
| Durée de vie sous attaque MIN, N=32 | 60 cycles |
| Facteur de réduction | « more than three orders of magnitude », soit environ 1 667 (déduit) |
| Longueur moyenne de la chaîne | 12 volumes de syndromes |
| Candidats consommés par attaque réussie | 32 × 12, environ 384 |
| Rareté de la trajectoire retenue | N^-L = 32^-12, environ 10^-18 |
| Taux d'échec spontané | proche de 10^-5 par cycle |
| Gain acheté par la sélection | environ treize ordres de grandeur en probabilité d'échec |
| Contrôle MAX à p=0.006 | N de 2 à 4 fait passer la durée de vie de 302 à 4 482 cycles (500 répétitions) |
| Temps par attaque, N=32 | 1.23 s |
| Temps par attaque, N=16 | 1.5 s |
| Temps par attaque, N=8 | 3.2 s |
| Seuil estimé de DeepQ | p_th environ 0.004 |
| Section III.4 | 1 000 attaques avec N=50, erreurs concentrées au centre, qubit (2,3) le plus touché |

MAX-VAR fait un peu moins bien que MIN. MAX et MIN-VAR donnent de longues durées de vie et sont omis des figures. Les valeurs de durée de vie pour N=8 et N=16 ne figurent que sur la figure 3.

Déduit : 12 volumes pour 60 cycles donne 5 mesures par volume, ce qui colle avec un volume de profondeur d=5 dans DeepQ.

Tableau 1 de l'article, tolérance aux fautes, sans erreur de mesure, arbitre MWPM :

| d | Erreurs simultanées | Motifs | Taux d'échec en % | Recours à l'arbitre | Syndromes restants |
|---|---|---|---|---|---|
| 3 | 1 | 18 | 0.0 | 8 | 8 |
| 3 | 2 | 144 | 32.64 | 96 | 163 |
| 3 | 3 | 672 | 53.27 | 527 | 1 116 |
| 5 | 1 | 50 | 0.0 | 0 | 0 |
| 5 | 2 | 1 200 | 0.5 | 1 139 | 1 559 |
| 5 | 3 | 18 400 | 4.93 | 17 868 | 47 108 |
| 7 | 1 | 98 | 0.0 | 21 | 21 |
| 7 | 2 | 4 704 | 0.0 | 4 008 | 6 506 |
| 7 | 3 | 147 392 | 0.37 | 144 244 | 423 040 |

Autres détails : l'estimation du taux d'erreur logique de la figure 8 est arrêtée à 100 échecs de décodage. La figure 7 utilise 20 000 pas d'environnement par taux d'erreur. Le décodeur entraîné à p = 0.011 donne le plus bas taux d'erreur logique à toutes les distances.

### Différence entre v1 et v2 (vérifié sur les deux HTML)

Les chiffres sont identiques (10^5 vers 60, N=32, 1.23 s). Le résumé de la v1 annonçait « up to five orders of magnitude », ce que ses propres chiffres ne soutiennent pas. La v2 corrige en « more than three orders of magnitude » et ajoute le modèle de menace (II.1), le coût de l'attaque (III.3) et la liste des limites.

### Code public et outils

* Aucun dépôt, aucune déclaration de disponibilité du code dans v1 ni dans v2.
* Aucune mention de stim, sinter, pymatching, PyTorch ou TensorFlow. Aucune version. Matériel non précisé.
* DeepQ d'origine : https://github.com/R-Sweke/DeepQ-Decoding (GPL 3.0, 50 étoiles, dernier push le 19/09/2022). Dépendances listées sans version : Python 3, numpy, scipy, tensorflow, keras, gym, et un fork modifié de keras-rl, https://github.com/R-Sweke/keras-rl
* Modèles préentraînés présents dans ce dépôt : `trained_models/d5_dp/` pour p dans {0.001, 0.003, 0.005, 0.007, 0.009, 0.011} et `trained_models/d5_x/` pour p de 0.001 à 0.015. Ils sont entraînés avec p_meas = p_phys, donc avec mesures fautives.
* Définition de la durée de vie dans le README de DeepQ : nombre total de mesures de syndrome pendant lesquelles l'agent survit, à comparer à 1/p pour un qubit seul.

### Reproduire sur un PC

* Calcul : 500 répétitions à 1.23 s donnent environ 10 minutes par configuration pour N=32, environ 27 minutes pour N=8. Une attaque coûte environ 384 évaluations du réseau Q.
* La référence coûte plus cher que l'attaque : 500 épisodes de 10^5 cycles font de l'ordre de 5 × 10^7 pas d'environnement (déduit).
* Verrous : pile TensorFlow 1 et Keras de 2018, fork keras-rl, code de l'attaque non publié donc à réécrire, et incertitude sur l'agent attaqué (modèle préentraîné de Sweke ou agent réentraîné avec arbitre MWPM, et à quel p d'entraînement).

---

## 2. decoder-bench

### Identité (vérifié)

* Dépôt : https://github.com/satvikmaurya/decoder-bench, licence MIT, branche par défaut `master`, créé le 20/08/2025, dernier push le 06/02/2026, 16 étoiles, version de paquet 0.1.0.
* Article : Maurya, Viszlai, Raveendran, Das, Tannu, « decoder-bench: Benchmarking Decoders for Quantum Error Correction », IISWC 2025, pages 286 à 295, DOI 10.1109/IISWC66894.2025.00032.
* Jeux de données : https://doi.org/10.5281/zenodo.16914504 avec `code.zip` (115.6 ko) et `datasets.zip` (2.8 Go).
* Aucune version arXiv trouvée. La page IEEE a refusé la lecture (HTTP 418), donc le texte de l'article n'a pas été lu. Tout ce qui suit vient du dépôt.

### Structure

```
decoder_bench/
  generator.py        ligne de commande, construit les circuits
  dataset_gen.py      échantillonne et écrit le HDF5
  sampler.py          échantillonneur parallèle, registre des décodeurs
  decoders.py         cinq décodeurs enregistrés
  eval.py             évaluation d'un couple (trace, décodeur)
  eval.sh             campagne complète
  generate.sh         génération des traces
  results/benchmark_results.csv   résultats publiés
  common/             noise.py, dem_matrices.py, build_circuit.py, codes_q.py, color_code_gen.py
  ls_ckt_gen/         circuits de lattice surgery
```

### Codes et expériences (vérifié dans generator.py)

| Code | Construction | Rounds |
|---|---|---|
| surface | `stim.Circuit.generated('surface_code:rotated_memory_{basis}', rounds=d, distance=d)` | d |
| qldpc | bivariate bicycle, d dans {6, 10, 12}, paramètres (6,6), (9,6), (12,6) | d |
| color | treillis triangulaire, `ColorCode(d, rounds=d)` | d |
| ls | lattice surgery sur code de surface, mesure logique par fusion | d par opération |

Base de mémoire x ou z au choix. Les campagnes publiées sont toutes en base z.

### Modèles de bruit (vérifié)

* `circuit` : SI1000(p) appliqué après construction par `NoiseModel.SI1000(p).noisy_circuit(circuit)`. Table exacte : CX et CZ à p, H et autres Clifford à un qubit à p/10, attente à p/10, réinitialisations R, RX, RY à 2p, mesures M, MX, MR, MRX, MRZ à 5p, attente pendant mesure et réinitialisation à 2p.
* `phenom` : `before_measure_flip_probability=p` et `before_round_data_depolarization=p`, rounds = d.
* `code_capacity` : un seul round, X_ERROR(p) (ou Z_ERROR selon la base) sur les qubits de données après la première réinitialisation, mesures parfaites.
* Valeurs de p des campagnes publiées : 0.0005, 0.001, 0.003, 0.005.

### Décodeurs comparés (vérifié dans decoders.py)

| Nom | Bibliothèque | Paramètres |
|---|---|---|
| pymatching | PyMatching | `Matching.from_stim_circuit(circuit)`, décodage par lot |
| belieffind | ldpc, `BeliefFindDecoder` | max_iter 100, minimum_sum, uf_method inversion, 1 fil |
| bplsd | ldpc, `BpLsdDecoder` | max_iter 100, minimum_sum, osd_cs, osd_order 10 |
| relay-bp | relay_bp, `RelayDecoderF32` | gamma0 0.1, pre_iter 80, num_sets 60, set_max_iter 60, gamma_dist_interval (-0.24, 0.66), stop_nconv 3 |
| mwpf | mwpf, `SolverSerialJointSingleHair` | cluster_node_limit 50, timeout 3.0, poids `int(log((1-p)/p))` |

Absents : Union-Find seul, Fusion Blossom, Tesseract, stimbposd, décodeurs neuronaux.

### Format des traces HDF5 (vérifié dans dataset_gen.py)

| Clé | Type | Contenu |
|---|---|---|
| `syndromes` | bool, (enregistrements, détecteurs), gzip | événements de détection |
| `observables` | bool, (enregistrements, observables), gzip | observables logiques |
| `check_matrix` | uint8 | matrice de contrôle tirée du DEM |
| `obs_matrix` | uint8 | matrice des observables |
| `priors` | float | probabilités des mécanismes |
| `circuit` | chaîne UTF 8 | circuit stim bruité complet |

Nom de fichier : `{code}_{bruit}_{d}_{p}_{base}.h5`, par exemple `surface_circuit_7_0.005_z.h5`. Échantillonnage par `compile_detector_sampler(seed=iteration + 42)`, 1 000 000 tirs par itération.

### Métriques (vérifié dans sampler.py)

* `logical_error_rate` = erreurs / tirs. C'est un taux par tir, donc sur d rounds, pas un taux par round.
* `time_per_shot` = temps CPU (`process_time`) passé dans `decode_batch`, divisé par le nombre de tirs.
* `total_time` = somme des temps CPU des ouvriers.
* Campagne : 5 000 000 tirs demandés, lots de 1 000, 32 ouvriers. Les tirs sont les premiers enregistrements de la trace, lus en tranches contiguës.

### Chiffres publiés, code de surface, base z, SI1000 (vérifié dans benchmark_results.csv)

Taux d'erreur logique par tir.

| d | p | Tirs | pymatching | belieffind | mwpf | relay-bp |
|---|---|---|---|---|---|---|
| 7 | 0.0005 | 5 000 000 | 1.06e-05 | 8.78e-05 | 5.6e-06 | 4.32e-05 |
| 7 | 0.001 | 5 000 000 | 1.264e-04 | 5.774e-04 | 7.64e-05 | 1.654e-04 |
| 7 | 0.003 | 5 000 000 | 0.0079552 | 0.0248494 | 0.0061828 | 0.0068258 |
| 7 | 0.005 | 5 000 000 | 0.0499594 | 0.1186482 | 0.0485052 | 0.0445128 |
| 11 | 0.0005 | 10 000 000 | 0.0 | 4.6e-06 | 1e-07 | 2.84e-05 |
| 11 | 0.001 | 5 000 000 | 1.8e-06 | 2.534e-04 | 1e-06 | 1.558e-04 |
| 11 | 0.003 | 1 000 000 | 0.002204 | 0.054002 | 0.003004 | 0.008467 |
| 11 | 0.005 | 1 000 000 | 0.04057 | 0.235005 | 0.061868 | absent |

Temps CPU de décodage par tir.

| d | p | pymatching | belieffind | mwpf | relay-bp |
|---|---|---|---|---|---|
| 7 | 0.0005 | 2.90 µs | 2.92 ms | 2.55 ms | 4.32 ms |
| 7 | 0.001 | 4.74 µs | 3.79 ms | 4.89 ms | 6.14 ms |
| 7 | 0.003 | 13.2 µs | 10.0 ms | 55.5 ms | 29.6 ms |
| 7 | 0.005 | 21.9 µs | 16.2 ms | 139.8 ms | 81.5 ms |
| 11 | 0.0005 | 14.2 µs | 158 ms | 13.9 ms | 56.1 ms |
| 11 | 0.001 | 25.9 µs | 332 ms | 35.6 ms | 125.6 ms |
| 11 | 0.003 | 44.7 µs | 357 ms | 257 ms | 620 ms |
| 11 | 0.005 | 117 µs | 761 ms | 561 ms | absent |

Nombres d'erreurs pour pymatching à d=7 (déduit) : 53, 632, 39 776 et 249 797.

Autres familles, résumé :

* qldpc d=12 : à p=0.001, relay-bp 1.08e-05, bplsd 6.12e-05, belieffind 1.1716e-03, mwpf 1.232e-03.
* qldpc d=6 : à p=0.001, relay-bp 1.9214e-03, bplsd 1.9598e-03, mwpf 2.5662e-03, belieffind 2.69e-03.
* color d=7 : à p=0.001, relay-bp 7.83e-04, mwpf 8.54e-04, belieffind 5.0288e-03, bplsd 9.0894e-03.
* lattice surgery d=11 : à p=0.001, pymatching 4.9e-06 à 71.8 µs par tir, mwpf 2.3e-06 à 214 ms par tir. À p=0.005, pymatching 0.094562, mwpf 0.183176 (500 000 tirs).

### Versions figées (vérifié dans requirements.txt et pyproject.toml)

Python 3.10 ou plus, stim 1.15.0, sinter 1.15.0, PyMatching 2.3.0, ldpc 2.3.8, numpy 2.3.2, scipy 1.16.1, h5py 3.14.0, networkx 3.5, pandas 2.3.1, ray 2.45.0 ou plus. `relay_bp` et `mwpf` sont importés par decoders.py mais ne sont ni listés ni figés.

### Pièges relevés à la lecture du code

1. **Traces dédoublonnées.** `store_unique` vaut True par défaut et `generate.sh` ne le change pas. Seuls les syndromes jamais vus sont stockés. Le taux publié est donc mesuré sur des syndromes uniques et non sur la distribution de Monte Carlo. Effet attendu : négligeable à p=0.003 et p=0.005, sensible à p=0.001 et fort à p=0.0005, avec un taux publié supérieur au taux réel (estimé, à mesurer).
2. **Option inopérante.** `--store_unique` est déclaré avec `type=bool`. Avec argparse, toute chaîne non vide vaut True, donc `--store_unique False` laisse le dédoublonnage actif.
3. **Graines non portables.** Les graines sont fixées, mais stim ne garantit pas les mêmes tirages d'une version ou d'une machine à l'autre. La relecture exacte passe par les traces Zenodo.
4. **Poids mwpf tronqués.** `int(np.log((1 - p)/p))` arrondit les poids à l'entier, ce qui écrase la résolution.
5. **Exemples du README inexacts.** `gen_surface_circuit((distance=7, ...))` n'est pas du Python valide. La section « Output Format » annonce des métadonnées alors que le fichier contient six clés précises.
6. **Scripts incomplets.** `generate.sh` ne génère pas le code de surface d=11 alors que le CSV contient ces lignes.

### Reproduire sur un PC

* PyMatching, d=7 : de 14.5 s à 110 s de CPU pour 5 000 000 tirs. d=11 : de 45 s à 142 s.
* Autres décodeurs à d=7 et p=0.001 pour 5 000 000 tirs : belieffind 18 943 s, mwpf 24 434 s, relay-bp 30 686 s de CPU.
* À d=11 et p=0.001 : belieffind 1 659 217 s de CPU, soit environ 19 jours CPU.
* Téléchargement : 2.8 Go pour les traces.

---

## 3. arXiv 2609.07035 : conformance testing

### Identité (vérifié)

* Titre : « Capability-Gated Conformance Testing of Quantum Error-Correction Decoder Libraries ».
* Auteurs : Jiachen Shen (University of Houston) et Hui Zhong (Miami University, Ohio).
* v1 du 07/09/2026, 60 pages, gabarit ACM TQC, licence CC BY. Catégories quant-ph et cs.AR.

### Codes et population (vérifié, tableaux 3 et 25)

| Id | Famille | d | Détecteurs | Arêtes | Syndromes | Optimum unique |
|---|---|---|---|---|---|---|
| I1 | répétition | 3 | 2 | 3 | 4 | 4 |
| I2 | répétition | 5 | 4 | 5 | 16 | 16 |
| I3 | répétition | 7 | 6 | 7 | 64 | 64 |
| I4 | surface rotated | 3 | 4 | 7 | 16 | 16 |
| I5 | surface unrotated | 3 | 6 | 13 | 64 | 31 |
| I6 | surface rotated | 5 | 12 | 21 | 4 096 | 2 736 |
| Total | | | | | 4 260 | 2 867 |

Expériences de mémoire compilées en modèle d'erreurs de détecteurs. Tous les syndromes sont testés, donc aucune graine et aucune erreur d'échantillonnage.

### Modèles de bruit (vérifié)

* Population énumérée : code capacity, p = 0.01, extraction de syndrome parfaite, poids uniforme log((1-p)/p) = 4.595.
* Mesure au niveau circuit (section 7.6) : code de surface rotated, profil de bruit symétrique à 10^-3, poids physiques natifs, d=5 et d=7, 20 000 tirs par cellule, un seul réétiquetage. Poids moyen de syndrome 1.8 à d=5 et 5.3 à d=7. Le générateur stim et les paramètres précis ne sont pas cités dans le texte.
* Recherche sous charge (section 8) : graphes dérivés de circuits, d=11 sur 11 rounds (1 320 détecteurs, 6 718 arêtes) et d=13 sur 13 rounds (2 184 détecteurs, 11 398 arêtes). Poids remplacés par des entiers pairs dans [2, 4096], donc ce n'est pas un modèle de bruit. Syndromes stratifiés sur |σ| dans {8, 16, 32, 64}, 800 syndromes et 50 réétiquetages par cellule.

### Panel (vérifié, tableau 4)

| Id | Bibliothèque et configuration | L1 | L2 | Retour |
|---|---|---|---|---|
| pm | pymatching 2.4.0, sparse blossom | silencieux | oui | observables |
| pmc | pymatching 2.4.0, corrélations activées | silencieux | silencieux | observables |
| fb | fusion-blossom 0.2.13 | silencieux | oui | correction |
| ldpc | ldpc 2.4.1, BP avec OSD 0 | silencieux | silencieux | correction |
| ldpc-r | ldpc 2.4.1, ordonnancement série aléatoire | silencieux | silencieux | correction |
| mwpf-j | mwpf, serial joint-single-hair | silencieux | silencieux | correction |
| mwpf-s | mwpf, serial single-hair | silencieux | silencieux | correction |
| mwpf-u | mwpf, serial union-find | silencieux | silencieux | correction |
| tess | tesseract-decoder | silencieux | silencieux | correction |

L1 = correction à distance bornée, L2 = optimisation exacte de poids minimum. pmc se comporte exactement comme pm. Les versions de mwpf et de tesseract-decoder ne sont pas données dans le texte.

### Méthode (vérifié)

* Propriété résiduelle : la correction rendue doit expliquer le syndrome dans l'espace d'indices de l'appelant.
* Certificat sans oracle (lemme 5.3) : deux corrections faisables de poids différents prouvent que la plus lourde n'est pas de poids minimum.
* Six relations : R1 ordre des mécanismes, R2 numérotation des détecteurs, R3 et R3b largeur et décalage des observables, R4 ordre des appels, R5 scission de mécanisme, R6 mise à l'échelle des poids. Le contrat déployable exclut R5, qui exige une résolution exacte par syndrome.
* États de déclaration : oui, non, silencieux. Un verdict de conformité n'existe que contre une capacité déclarée.
* Oracle exact : programme linéaire en nombres entiers. Un défaut a été trouvé dans cet oracle, l'écart relatif MIP par défaut de 10^-4 n'était pas remis à zéro (40 784 annoncé contre 40 782 réel).

### Chiffres clés (vérifié)

| Mesure | Valeur |
|---|---|
| Cellules d'audit documentaire | 54, dont 4 portent une déclaration |
| L1 déclaré | 0 sur 7 |
| Rendement direct, dérivé, applicabilité pour L1 | 0.0 %, 13.8 %, 62.1 % (sur 791 cas, 7 119 cellules) |
| Résultats jugés sans échec résiduel | 717 244 |
| Certificats produits | 639 sur 76 680 comparaisons appariées, 639 vérifiés, 0 échec |
| mwpf-u | optimum sous une numérotation, correction 26 % plus lourde sous une autre, sur 26 des 2 867 syndromes |
| Exemple à d=5 | syndrome 011111101000, poids 17.687434 contre 22.282554 |
| Recherche sous charge | 160 000 comparaisons, 0 certificat contre pymatching et fusion-blossom |
| Oracle exact | 1 599 syndromes résolus sur 1 600, tous égaux à l'optimum |
| R6 sur BP avec OSD | 1 598 et 1 748 réponses changées |
| Corruptions de correction détectées | taux d'erreur lu sur les observables 0 sur 219, recalculé par l'appelant 176, contrat 215, vérification exhaustive 219 |
| Perturbations du poids rendu | 72 sur 72 détectées par une simple somme |

Dépendance à la présentation sur syndromes tirés du bruit (tableau 8, 20 000 tirs par cellule) :

| d | Sujet | Correction changée | Poids changé | Classe logique changée |
|---|---|---|---|---|
| 5 | ldpc | 47 (0.23 %) | 34 (0.17 %) | 1 (0.005 %) |
| 5 | pm | 0 | 0 | 0 |
| 5 | fb | 0 | 0 | 0 |
| 7 | ldpc | 135 (0.68 %) | 89 (0.45 %) | 0 |
| 7 | pm | 0 | 0 | 0 |
| 7 | fb | 3 (0.01 %) | 0 | 0 |

### Coûts (vérifié)

| Mesure | Valeur |
|---|---|
| Oracle poids minimum, d=7, 11, 15 | 6.66 ms, 7.22 ms, 7.54 ms par syndrome |
| Oracle avec unicité, d=7, 11, 15 | 28.44 ms, 66.75 ms, 95.05 ms |
| Balayage complet à d=15 | pymatching 0.31 s, fusion-blossom 0.35 s, BP avec OSD 0.48 à 0.54 s, oracle 35.5 s |
| Passe d'oracle réalisée | 1 062 s à d=11, 3 171 s à d=13 |
| Certificat, deux sujets | 240.7 s à d=11, 533.3 s à d=13 |
| Coût pour un appelant | 0.067 ms par syndrome pour trois passes pymatching |

### Outils et artefact (vérifié, annexe H)

* Environnement : CPython 3.11.4 sous Windows, Stim 1.16.0, PyMatching 2.4.0, fusion-blossom 0.2.13, ldpc 2.4.1, NumPy 2.2.6, SciPy 1.17.1, NetworkX 3.6.1. Deux sujets tournent dans un environnement séparé. Déclarations extraites le 28/08/2026 depuis les paquets installés.
* Artefact : https://doi.org/10.5281/zenodo.22235839
* Dépôt : https://github.com/Mercury0828/deccon-artifact
* Vérificateur autonome `deccon-cert`, en Python avec la seule bibliothèque standard, onze contrôles.

### Reproduire sur un PC

Tout a tourné sur une seule station de travail. La recherche sous charge était budgétée à une journée de station. La vérification des 639 certificats ne demande aucune bibliothèque de décodage.

---

## 4. arXiv 2603.20127 : robustesse à l'incertitude sur le taux d'erreur

### Identité (vérifié)

* Titre : « Analyzing Decoders for Quantum Error Correction ».
* Auteurs : Abtin Molavi et Aws Albarghouthi (University of Wisconsin, Madison), Feras Saad (Carnegie Mellon).
* v1 du 20/03/2026, 29 pages, catégories cs.PL et quant-ph, licence CC BY 4.0. Pas de version HTML sur arXiv, texte lu depuis le PDF.

### Codes et expériences (vérifié)

* Code de surface rotated, expérience de mémoire.
* d dans {3, 5, 7, 9} et r dans {1, 3, 5, 7, 9} avec r inférieur ou égal à d, soit 14 programmes.
* Circuits stim compilés en modèle d'erreurs de détecteurs. La base de mémoire n'est pas précisée.
* Exemple pédagogique : code de répétition à trois qubits.

### Modèle de bruit (vérifié)

* SI1000 dans tous les cas, p réglant la dépolarisation des portes à deux qubits.
* p dans {0.01, 0.001, 0.0001}.
* « Dérive » au sens de l'article : ce n'est pas une évolution temporelle. Chaque probabilité de canal de Bernoulli v devient une variable x contrainte à l'hyperrectangle 0.9 v ≤ x ≤ 1.1 v, soit 10 % d'incertitude, et on cherche le pire cas.

### Décodeurs (vérifié)

pymatch (PyMatching, Higgott 2021), bp-osd (Panteleev et Kalachev 2021), relay-bp (Müller et al. 2025). Aucune version ni hyperparamètre dans le texte. Le décodeur est traité en boîte noire.

### Méthode (vérifié)

* Sémantique formelle à petits pas d'un noyau du format de circuit stim.
* Le taux d'erreur logique est un polynôme multilinéaire en les probabilités physiques. Précision = évaluation du polynôme en un point. Robustesse = maximisation sur l'hyperrectangle.
* Bornes sûres : p(L ∩ S) ≤ p(L) ≤ 1 moins p(S \ L), où S est l'ensemble des chaînes d'erreurs explorées.
* Énumération par poids de Hamming croissant. Variantes : split-search (la moitié des ouvriers démarre au poids ⌊d/2⌋ + 1) et recherche locale (mouvements flip et shift).
* Optimisation : les extrema sont sur les sommets. Élagage par signe de la dérivée partielle, simplification des termes appariés, puis énumération exhaustive des variables restantes. Aucun solveur externe.
* Variante hybride : énumération plus 10 000 tirs aléatoires, intervalle de confiance de Chernoff avec α = 0.01.
* Critère de convergence : nombre minimal de tirs tel que borne haute / borne basse ≤ √10.

### Chiffres clés (vérifié)

* Instance d=5 : taux d'erreur logique déterminé à 0.1 % près en environ 3 × 10^6 tirs, contre 100 fois plus pour l'échantillonnage.
* À p = 0.01, l'énumération seule ne converge que sur 2 programmes, la variante hybride sur les 14. À ce niveau stim est plus efficace d'un ordre de grandeur au moins.
* À p = 0.0001, l'énumération est la plus efficace. Tirs jusqu'à convergence entre 10^6 et 10^8.
* Robustesse : écart entre précision et pire cas de 28.6 % pour relay-bp, 21.6 % pour bp-osd, 21.7 % pour pymatch. Sur (d=3, r=3, p=0.001), relay-bp est plus précis mais moins robuste que bp-osd.
* Plus grande instance de robustesse résolue : d=3, r=3, 286 canaux d'erreur donc 286 variables. Temps de convergence entre 0 et 1 500 s.
* Recherche locale : shift améliore 24 programmes sur 25 avec un rapport de tirs moyen de 0.73. flip améliore 13 sur 25 avec 1.05.
* split-search à d=9 : l'énumération standard demande environ 6 fois plus de tirs pour la première borne basse.
* Aucun tableau de taux d'erreur logique chiffré. Les résultats sont dans les figures 8 à 13.

### Outils, code et coût (vérifié)

* Bibliothèque Python maison qui prend des circuits stim en entrée. Version de stim non précisée.
* Artefact : https://anonymous.4open.science/r/analyzing-decoders-8034/ (version préliminaire, image Docker annoncée). La page n'a pas pu être lue.
* Matériel : 16 cœurs d'un AMD EPYC 7763 à 2.45 GHz, 32 Go de mémoire.
* Arrêt à 24 h ou 10^9 tirs par instance.

### Reproduire sur un PC

Les instances de robustesse (d=3 et d=5 avec r=1) convergent en moins de 1 500 s sur 16 cœurs et sont à la portée d'un PC. La campagne de précision complète ne l'est pas avec un plafond de 24 h par instance.

---

## 5. arXiv 2609.19090

« Securing quantum error correction against misleading advice from AI agents », A. Barış Özgüler, v1 du 16/09/2026, 74 pages. Lu : le résumé seulement.

L'article demande si un attaquant peut pousser un conseiller IA à recommander une mise à jour nuisible de la correction d'erreurs. Il montre sur le code torique que deux rotations X cohérentes opposées donnent les mêmes historiques de syndromes, puis propose des mesures de calibration et un évaluateur séparé qui n'accepte une mise à jour que si l'amélioration est certifiée, sans supposer le conseiller honnête.

---

## Cible de reproduction recommandée

### Le résultat à reproduire en premier

decoder-bench, trace `surface_circuit_7_0.005_z.h5`, décodeur pymatching : **taux d'erreur logique par tir 0.0499594 sur 5 000 000 tirs, soit 249 797 erreurs, à 21.9 µs de CPU par tir.**

Pourquoi ce point : il exerce toute la chaîne (stim, modèle de bruit, modèle d'erreurs de détecteurs, PyMatching), la valeur publiée est un fichier CSV lisible, la statistique est très forte, le dédoublonnage des traces y est sans effet, et le calcul tient en moins d'une minute.

### Paramètres exacts

| Paramètre | Valeur |
|---|---|
| Code | code de surface rotated |
| Expérience | mémoire Z |
| Distance | 7 |
| Rounds | 7 |
| Circuit | `stim.Circuit.generated('surface_code:rotated_memory_z', rounds=7, distance=7)` |
| Bruit | `NoiseModel.SI1000(0.005).noisy_circuit(circuit)` de `decoder_bench/common/noise.py` |
| SI1000 à p = 0.005 | CX 0.005, H 0.0005, attente 0.0005, réinitialisation 0.01, mesure 0.025, attente pendant mesure 0.01 |
| Décodeur | `pymatching.Matching.from_stim_circuit(circuit)`, `decode_batch` |
| Versions | Python 3.10 ou plus, stim 1.15.0, sinter 1.15.0, PyMatching 2.3.0, numpy 2.3.2, h5py 3.14.0 |
| Métrique | erreurs / tirs, par tir de 7 rounds |

### Deux façons de vérifier

| Voie | Entrée | Tirs | Résultat attendu | Temps CPU de décodage |
|---|---|---|---|---|
| A, relecture exacte | 5 000 000 premiers enregistrements de la trace Zenodo | 5 000 000 | 249 797 erreurs | environ 110 s |
| B, tirage frais | circuit lu dans la clé `circuit` du même fichier | 1 000 000 | taux entre 0.04924 et 0.05068 (3 écarts types combinés, déduit) | environ 22 s |

La voie B sans téléchargement reste possible en reconstruisant le circuit avec noise.py du dépôt.

Conversion utile (déduit) : taux par round = (1 moins (1 moins 2 P)^(1/7)) / 2, soit environ 0.00746 à p = 0.005.

### Étapes suivantes, dans l'ordre

1. Même couple à p = 0.003 : 0.0079552 attendu (39 776 erreurs), 13.2 µs par tir.
2. Même couple à p = 0.001 : 1.264e-04 publié (632 erreurs). Un tirage frais devrait donner moins à cause du dédoublonnage. Mesurer cet écart prouve qu'on comprend la trace.
3. Contrôle d'entrée dans la trace : compter les lignes identiques et vérifier que le syndrome nul n'apparaît qu'une fois.
4. Conformité 2609.07035 : lancer `deccon-cert` sur les 639 certificats de l'artefact, attendu 639 vérifiés et 0 échec.
5. Attaque 2504.19651, en dernier : installer DeepQ, retrouver la durée de vie de référence à d=5 et p=0.001, puis coder l'algorithme 1 et viser 60 cycles à N=32.

### Limites de cette extraction

* L'article IISWC de decoder-bench n'a pas été lu (accès refusé), seul le dépôt l'a été.
* Les traces Zenodo n'ont pas été téléchargées. Le nom de fichier et le dédoublonnage sont déduits du code, pas constatés dans les données.
* Le dépôt anonyme de 2603.20127 n'a pas pu être lu.
* Pour 2609.19090, seul le résumé a été lu, comme demandé.
