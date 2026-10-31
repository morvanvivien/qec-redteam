# Registre de la red team QEC

Mis à jour le 2026-10-31. Généré par `python -m redteam.registre` depuis [registre.json](registre.json) ; ne pas éditer à la main.

Tout ce que nous avons examiné y figure, y compris ce qui s'est révélé faux et nos propres erreurs. Chaque entrée renvoie à ses preuves dans ce dépôt et, quand c'est possible, à la commande qui la rejoue.

| Catégorie | Nombre | Définition |
|---|---|---|
| Défauts confirmés | 5 | Défaut confirmé : comportement faux d'un logiciel public, rejoué depuis zéro, graine fixée, intervalles de confiance. |
| Défauts connus, cause trouvée par nous | 1 | Défaut déjà signalé par un tiers ; nous apportons la cause, la portée ou un correctif vérifié. |
| Choix documentés par l'auteur | 1 | Ressemblait à un défaut ; la documentation de l'auteur le décrit comme un choix voulu. Seule sa conséquence est à nous. |
| Profils mesurés (pas des défauts) | 5 | Comportement mesuré qui n'est pas un défaut (sensibilité, latence, classement) : il décrit le décodeur, il ne l'accuse pas. |
| Ce qui tient | 1 | Épreuve passée : rien d'anormal sous le bruit testé. |
| Pistes ouvertes | 2 | Observation non expliquée, à examiner avant toute conclusion. |
| Faux positifs et pistes écartées | 5 | Hypothèse ou piste écartée par la mesure. Gardée ici pour montrer ce qui a été vérifié, pas seulement ce qui a été trouvé. |
| Nos erreurs de méthode, corrigées avant publication | 3 | Erreur de notre propre méthode, repérée et corrigée avant toute publication. |

## Défauts confirmés

### QEC-2026-002 — L'option --store_unique False ne désactive pas le dédoublonnage

- **Cible :** decoder-bench (commit 9733a55)
- **Date :** 2026-09-28
- **Constat :** argparse avec type=bool : bool("False") vaut True, toute valeur non vide laisse le dédoublonnage actif.
- **Preuves :** [constat-001-decoder-bench-dedoublonnage.md](constat-001-decoder-bench-dedoublonnage.md), [decoder-bench-1-store-unique.md](issues/decoder-bench-1-store-unique.md)
- **Rejouer :** `python -c "import argparse; p = argparse.ArgumentParser(); p.add_argument('--s', type=bool); print(p.parse_args(['--s', 'False']).s)"`
- **Signalé :** 2026-09-28 — https://github.com/satvikmaurya/decoder-bench/issues/2 — ouvert, sans réponse au 31/10

### QEC-2026-004 — Probabilités additionnées puis exception à chaque décodage sur un qubit saturé

- **Cible :** relay-bp (IBM), module stim/sinter (0.2.2 (PyPI) et main d185194)
- **Date :** 2026-09-29
- **Constat :** CheckMatrices.from_dem additionne les probabilités d'une arête (somme jusqu'à 4,5) ; les arêtes ≥ 1 sont traitées comme certaines et le biais np.matrix fait lever TypeError. Déclenché dès une dépolarisation de 0,4 par TICK sur un seul qubit. Rejoué sur 6 graines (d = 3 et 5), exception à chaque fois ; la correction naïve donne 49,7 % d'erreur contre 13,8 % pour le décodeur qui ignore l'événement.
- **Preuves :** [constat-003-relay-bp-probabilites-additionnees.md](constat-003-relay-bp-probabilites-additionnees.md), [repro_crash.py](../research/relay-bp-priors/repro_crash.py), [results-repro_crash.txt](../research/relay-bp-priors/results-repro_crash.txt), [results-measure_effect-d5.txt](../research/relay-bp-priors/results-measure_effect-d5.txt), [results-measure_effect-d3.txt](../research/relay-bp-priors/results-measure_effect-d3.txt)
- **Rejouer :** `.venv/bin/python research/relay-bp-priors/repro_crash.py`
- **Signalé :** 2026-09-30 — https://github.com/trmue/relay/issues/43 — l'auteur a répondu le 16/10 (« I think you are correct », en voyage, il reviendra dessus) ; réponse et offre de PR postées le 31/10 ; aucun correctif au 31/10

### QEC-2026-005 — Un a priori d'exactement 1/2 produit des corrections qui violent le syndrome

- **Cible :** relay-bp (IBM), cœur Rust min-sum (0.2.2 (PyPI) et main d185194 ; correctif du cœur compilé depuis la sdist 0.2.2)
- **Date :** 2026-09-30
- **Constat :** Décision dure posterior <= 0 et messages min-sum sans signe : un contrôle, trois colonnes à 1/2, syndrome nul, sortie [1, 1, 1], échec après 3 680 itérations. Le correctif < règle l'exemple minimal sans régression (300 problèmes, empreinte identique) mais pas une vraie fuite ; plafonner à 1/2 − 1e−5 la règle (fuite d'ancilla, d = 5 : 12,8 % → 1,22 % sur 3 graines, contre 3,94 % sans connaître la fuite). Seconde cause localisée le 12/10 dans min_sum.rs : un a priori de 1/2 est un effacement (rapport logarithmique exactement 0, que MinSumBPDecoder::new ne traite pas à part), et sur le vrai DEM d'une fuite les colonnes à 1/2 forment un ensemble bloquant du graphe de Tanner (à d = 5 : 14 colonnes, 10 détecteurs touchés, chacun au moins deux fois). Dans compute_check_to_variable, une magnitude entrante nulle met à 0 les messages sortants vers les autres colonnes ; tous les messages entrant dans l'ensemble et ses a posteriori restent donc exactement 0 à chaque itération (la mémoire de Mem-BP et les gammas de Relay multiplient un 0), et posterior <= 0 tranche l'ensemble en bloc sans regarder le syndrome ; < choisit l'autre bloc. Réplique numpy des règles de min_sum.rs sur 200 tirs : syndrome satisfait 2/200 (fuite d'ancilla) et 0/200 (fuite de donnée) avec les a priori tels quels, 67/200 et 59/200 plafonnés à 1/2 − 1e−5, qui garde un signe. Même ensemble bloquant à d = 3 (12 et 14 colonnes). Correctif équivalent dans le cœur : remplacer tout rapport logarithmique de valeur absolue inférieure à 4e−5 par +4e−5. Correctif du cœur écrit, compilé (rustup GNU + maturin sous Windows, 13 tests amont ok, empreinte de régression inchangée) et mesuré le 12/10 : avec le cœur corrigé et sans plafond Python, relay-bp informé passe de 12,84 % à 1,24 % [1,12 ; 1,38] (fuite d'ancilla) et de 5,60 % à 1,26 % [1,14 ; 1,40] (fuite de donnée), d = 5, graines 101 à 103, 30 000 tirs chacune, au niveau du plafond Python (1,25 % et 1,18 %) et de la mesure Linux du 30/09 (1,22 % et 1,19 %) ; PyMatching informé 0,87 % et 1,01 %.
- **Preuves :** [constat-003-relay-bp-probabilites-additionnees.md](constat-003-relay-bp-probabilites-additionnees.md), [repro_half_prior.py](../research/relay-bp-priors/repro_half_prior.py), [results-repro_half_prior-pypi.txt](../research/relay-bp-priors/results-repro_half_prior-pypi.txt), [results-repro_half_prior-main.txt](../research/relay-bp-priors/results-repro_half_prior-main.txt), [results-repro_half_prior-fix.txt](../research/relay-bp-priors/results-repro_half_prior-fix.txt), [results-measure_effect-d5-clamped.txt](../research/relay-bp-priors/results-measure_effect-d5-clamped.txt), [stopping_set.py](../research/relay-bp-priors/stopping_set.py), [results-stopping_set-d5.txt](../research/relay-bp-priors/results-stopping_set-d5.txt), [results-stopping_set-d3.txt](../research/relay-bp-priors/results-stopping_set-d3.txt), [relay-bp-43-core-comment.md](issues/relay-bp-43-core-comment.md), [fix-zero-llr-core.patch](../research/relay-bp-priors/fix-zero-llr-core.patch), [results-repro_half_prior-core-fix.txt](../research/relay-bp-priors/results-repro_half_prior-core-fix.txt), [results-repro_half_prior-pypi-windows-build.txt](../research/relay-bp-priors/results-repro_half_prior-pypi-windows-build.txt), [results-measure_effect-d5-core-fix.txt](../research/relay-bp-priors/results-measure_effect-d5-core-fix.txt), [environnement-core-fix-windows.txt](../research/relay-bp-priors/environnement-core-fix-windows.txt)
- **Rejouer :** `.venv/bin/python research/relay-bp-priors/repro_half_prior.py`
- **Signalé :** 2026-09-30 — https://github.com/trmue/relay/issues/43 — second complément (cause dans le cœur, correctif mesuré) posté le 13/10 ; l'auteur a répondu le 16/10 (« I think you are correct », en voyage, il reviendra dessus) ; réponse et offre de PR postées le 31/10 ; aucun correctif au 31/10

### QEC-2026-016 — Sur le code principal d'IBM, un qubit qui fuit fait échouer tous les décodages informés

- **Cible :** relay-bp (IBM), cœur Rust min-sum, sur le gross code [[144,12,12]] (0.2.2 (PyPI))
- **Date :** 2026-09-30
- **Constat :** Le DEM du gross code n'étant pas décomposable, relay-bp ne plante pas mais reçoit 59 colonnes d'a priori exactement 1/2. Informé tel quel : 74 erreurs sur 150 tirs (49 %), 150 échecs de convergence sur 150, 11,5 s par tir ; a priori plafonnés à 1/2 − 1e−5 : 0 sur 150, aucun échec ; réglé sur le nominal : 0 sur 150. p = 0,003, graines 5, 6 et 7, fuite d'ancilla et fuite de qubit de données.
- **Preuves :** [gross_half_prior.py](../research/relay-bp-priors/gross_half_prior.py), [results-gross_half_prior-pilot.txt](../research/relay-bp-priors/results-gross_half_prior-pilot.txt), [results-gross_half_prior-ancilla-s6.txt](../research/relay-bp-priors/results-gross_half_prior-ancilla-s6.txt), [results-gross_half_prior-donnee-s7.txt](../research/relay-bp-priors/results-gross_half_prior-donnee-s7.txt), [README.md](../third_party/relay_bp/README.md)
- **Rejouer :** `.venv/bin/python research/relay-bp-priors/gross_half_prior.py --p 0.003 --shots 60 --seed 6 --scenario "fuite ancilla"`
- **Signalé :** 2026-10-01 — https://github.com/trmue/relay/issues/43 — complément posté sous l'issue #43 le 01/10 ; l'auteur a répondu le 16/10 (« I think you are correct », en voyage, il reviendra dessus) ; réponse et offre de PR postées le 31/10 ; aucun correctif au 31/10

### QEC-2026-015 — sinter ne fusionne pas les arêtes parallèles données à fusion-blossom : jusqu'à ×3,4 d'erreurs sous bruit biaisé

- **Cible :** sinter (stim, Google), adaptateur fusion_blossom (sinter 1.16.0 ; stim main 131793e ; fusion-blossom 0.2.13)
- **Date :** 2026-09-30
- **Constat :** Piste ouverte le 30/09 (fusion-blossom informé d'un biais Z faisait pire que réglé), expliquée le même jour. L'adaptateur crée une arête par composante d'erreur sans regrouper celles d'une même paire de détecteurs (3 724 arêtes pour 502 paires) ; l'adaptateur mwpf voisin, lui, les fusionne. Sous biais Z η = 1000, d = 5 : 1,095 % contre 0,869 % une fois fusionnées (= PyMatching 0,868 %), 3 graines, 78 000 tirs, McNemar p = 2e−28. Sous SI1000 ordinaire : aucun effet (0,436 % contre 0,432 %, p = 0,83). Selon la distance à η = 1000 : ×3,38 à d = 3 (5,07 % contre 1,50 %), ×1,26 à d = 5, ×1,07 à d = 7 (p = 0,008) ; selon le biais à d = 5 : ×0,99 à η = 10, ×1,19 à η = 100. Sur le code XZZX, fait pour ce bruit (01/10) : ×6,27 à d = 3 (5,09 % contre 0,81 %), ×2,19 à d = 5 (0,380 % contre 0,173 %, McNemar p = 9e−33), ×1,47 à d = 7 (p = 9e−4) ; le défaut coûte deux fois plus que sur le code ordinaire. En mémoire Z (13/10, d = 5, graines 11 à 13, 600 000 tirs) : l'adaptateur de sinter fait 5,62e−4 à η = 1000 contre 3,05e−4 une fois les arêtes fusionnées, exactement PyMatching (183 erreurs chacun) : ×1,84, McNemar p = 3e−45 ; ×1,78 à η = 100 (p = 5e−41) ; rien à η = 10. Le défaut coûte plus qu'en mémoire X (×1,26). C'est lui qui explique, dans le banc de désaccord en mémoire Z, fusion-blossom informé moins bon que réglé (pénalité 0,61 et 0,65).
- **Preuves :** [constat-004-sinter-fusion-blossom-aretes-paralleles.md](constat-004-sinter-fusion-blossom-aretes-paralleles.md), [parallel_edges.py](../research/sinter-fusion-blossom/parallel_edges.py), [results-biais-eta1000-d5.txt](../research/sinter-fusion-blossom/results-biais-eta1000-d5.txt), [results-si1000-d5.txt](../research/sinter-fusion-blossom/results-si1000-d5.txt), [results-biais-eta1000-d3.txt](../research/sinter-fusion-blossom/results-biais-eta1000-d3.txt), [results-biais-eta1000-d7.txt](../research/sinter-fusion-blossom/results-biais-eta1000-d7.txt), [results-biais-eta10-d5.txt](../research/sinter-fusion-blossom/results-biais-eta10-d5.txt), [results-biais-eta100-d5.txt](../research/sinter-fusion-blossom/results-biais-eta100-d5.txt), [xzzx.py](../research/sinter-fusion-blossom/xzzx.py), [d3_s11.txt](../research/sinter-fusion-blossom/xzzx-runs/d3_s11.txt), [d3_s12.txt](../research/sinter-fusion-blossom/xzzx-runs/d3_s12.txt), [d3_s13.txt](../research/sinter-fusion-blossom/xzzx-runs/d3_s13.txt), [d5_s11.txt](../research/sinter-fusion-blossom/xzzx-runs/d5_s11.txt), [d5_s12.txt](../research/sinter-fusion-blossom/xzzx-runs/d5_s12.txt), [d5_s13.txt](../research/sinter-fusion-blossom/xzzx-runs/d5_s13.txt), [d7_s11.txt](../research/sinter-fusion-blossom/xzzx-runs/d7_s11.txt), [d7_s12.txt](../research/sinter-fusion-blossom/xzzx-runs/d7_s12.txt), [d7_s13.txt](../research/sinter-fusion-blossom/xzzx-runs/d7_s13.txt), [d5_r5_p0.002_x_biais_s20260929_biais.csv](brique-2/d5_r5_p0.002_x_biais_s20260929_biais.csv), [d5_r5_p0.002_x_biais_s20260929_biais_lents.csv](brique-2/d5_r5_p0.002_x_biais_s20260929_biais_lents.csv), [results-biais-eta1000-d5-memoire-z.txt](../research/sinter-fusion-blossom/results-biais-eta1000-d5-memoire-z.txt), [results-biais-eta100-d5-memoire-z.txt](../research/sinter-fusion-blossom/results-biais-eta100-d5-memoire-z.txt), [d5_r5_p0.002_z_biais_s20260929_windows.csv](brique-2/d5_r5_p0.002_z_biais_s20260929_windows.csv), [stim-1116-memoire-z-comment.md](issues/stim-1116-memoire-z-comment.md)
- **Rejouer :** `.venv/bin/python research/sinter-fusion-blossom/parallel_edges.py --seeds 11 12 13 --shots 26000`
- **Signalé :** 2026-10-01 — https://github.com/quantumlib/Stim/issues/1116 — issue #1116 ouverte le 01/10, compléments XZZX (01/10) et mémoire Z (31/10) postés, sans réponse au 31/10 ; offre de PR retirée le 31/10, CONTRIBUTING.md excluant le code généré par IA ; la fonction est inchangée sur main au 31/10

## Défauts connus, cause trouvée par nous

### QEC-2026-003 — Écriture hors limites dans le balayage combinatoire d'OSD (issue ldpc #105)

- **Cible :** ldpc (BP+OSD, BP+LSD) (2.4.1)
- **Date :** 2026-09-28
- **Constat :** Les boucles de paires ne sont pas bornées par k : dès que k < ordre, écriture hors du vecteur, plantage sous Windows, corruption silencieuse sous Linux au-delà de l'ordre 24. Cause, étendue et correctif de quelques lignes vérifiés avant/après ; sorties identiques sur 46 configurations.
- **Preuves :** [constat-002-ldpc-balayage-combinatoire.md](constat-002-ldpc-balayage-combinatoire.md), [README.md](../research/ldpc-105/README.md)
- **Rejouer :** `.venv/bin/python research/ldpc-105/repro_osd_k.py`
- **Signalé :** 2026-09-29 — https://github.com/quantumgizmos/ldpc/pull/116 — issue d'un tiers (#105) ouverte depuis le 05/08 ; notre commentaire (cause, portée, correctif vérifié) posté le 29/09 ; un tiers corrige osd.hpp seul le 24/10 (PR 112), le plantage lsd_cs passe par osd_dense.hpp et reste ; notre PR 116 ouverte le 31/10, vérifiée sous Linux, sans réponse au 31/10

## Choix documentés par l'auteur

### QEC-2026-001 — Taux d'erreur publiés mesurés sur des syndromes dédoublonnés

- **Cible :** decoder-bench (commit 9733a55 ; traces Zenodo 10.5281/zenodo.16914504)
- **Date :** 2026-09-28
- **Constat :** Les traces ne gardent qu'un exemplaire de chaque syndrome : le taux publié dépasse le Monte Carlo de 22 % à p = 0,001 et de 83 % à p = 0,0005 (PyMatching, d = 7). Le dédoublonnage est un choix voulu (thèse de l'auteur, annexe A.2.1.3) ; la conséquence chiffrée n'était écrite nulle part.
- **Preuves :** [constat-001-decoder-bench-dedoublonnage.md](constat-001-decoder-bench-dedoublonnage.md)
- **Rejouer :** `.venv/bin/python -m redteam.reproduce --out out/decoder_bench`
- **Signalé :** 2026-09-28 — https://github.com/satvikmaurya/decoder-bench/issues/3 — ouvert, sans réponse au 31/10

## Profils mesurés (pas des défauts)

### QEC-2026-006 — Classement renversé par une diaphonie ZZ non calibrée

- **Cible :** tesseract, mwpf, BP+OSD, stimbposd (tesseract 0.1.1.dev20260822020007, mwpf 0.2.12, ldpc 2.4.1, stimbposd 0.2.0)
- **Date :** 2026-09-30
- **Constat :** Réglés sur le nominal, tesseract fait 0,62 à 0,70 fois les erreurs de PyMatching sous bruit nominal et 1,29 à 1,53 fois sous diaphonie ZZ à 3p (d = 5, 3 graines, 40 000 tirs appariés) ; mwpf passe de 0,76 à 2,4–2,9. Même chose en miroir (XX, mémoire X). Effacé à d = 3, renversé à d = 5. Informés de la diaphonie, ils repassent devant : sensibilité à la calibration, pas défaut. À d = 7 (p = 0,003, graine 42) : 0,35 [0,23 ; 0,48] sous bruit nominal (10 000 tirs), 2,00 [1,40 ; 3,04] sous diaphonie ZZ 3p (3 000 tirs, McNemar p = 3e−4) : l'inversion grandit avec la distance. Série d = 3 fermée le 12/10 sur 3 graines (41, 42, 43 ; 60 000 tirs appariés chacune, poste Windows, sans tesseract) : mwpf 0,81 à 0,85 fois PyMatching au nominal, 1,00 à 1,05 sous ZZ 3p (avantage effacé, pas renversé) ; BP+OSD 1,00 à 1,05 puis 1,20 à 1,24 ; stimbposd 0,87 à 0,90 puis 1,02 à 1,06 ; BP+LSD 1,31 à 1,44 puis 1,68 à 1,72 ; beliefmatching 0,92 puis 0,98 à 0,99 ; fusion-blossom inchangé. Les journaux des duels de septembre (d = 3 et 5) n'ayant jamais été versionnés (QEC-2026-021), les duels d = 5 et le d = 3 avec tesseract sont relancés sous Linux. Rejeu d = 5 le 13/10 (Windows, graines 31 à 33, 40 000 tirs chacune, sans tesseract) : mwpf 0,65 à 0,76 fois PyMatching au nominal, 2,53 à 3,02 sous ZZ 3p (McNemar p ≤ 3e−43) ; BP+OSD 0,81 à 0,96 puis 2,33 à 2,71. Le renversement de mwpf est répliqué sur une autre machine ; celui de tesseract repose encore sur les mesures Linux de septembre (Linux requis pour le rejouer).
- **Preuves :** [brique-2-resultats.md](brique-2-resultats.md), [results-d7-zz-s42.txt](../research/duel-d7/results-d7-zz-s42.txt), [batches-d7_p0.003_diaphonie_ZZ_3p_s42_b250.jsonl](../research/duel-d7/batches-d7_p0.003_diaphonie_ZZ_3p_s42_b250.jsonl), [results-d3-s41-windows.txt](../research/duel-d3/results-d3-s41-windows.txt), [results-d3-s42-windows.txt](../research/duel-d3/results-d3-s42-windows.txt), [results-d3-s43-windows.txt](../research/duel-d3/results-d3-s43-windows.txt), [results-d5-s31-windows.txt](../research/duel-d5/results-d5-s31-windows.txt), [results-d5-s32-windows.txt](../research/duel-d5/results-d5-s32-windows.txt), [results-d5-s33-windows.txt](../research/duel-d5/results-d5-s33-windows.txt)
- **Rejouer :** `.venv/bin/python -m redteam.duel --distance 5 --p 0.002 --scenario nominal "diaphonie ZZ 3p" --decoders pymatching tesseract mwpf --shots 40000 --seed 32`

### QEC-2026-007 — Queue de latence lourde sous bruit perturbé

- **Cible :** tesseract, mwpf (tesseract 0.1.1.dev20260822020007, mwpf 0.2.12)
- **Date :** 2026-09-30
- **Constat :** tesseract : p99 de 21 ms au nominal à 399 ms sous « tout x3 », tirs jusqu'à 1,9 s ; mwpf : p99 de 0,16 à 0,65 s. Rejoué avec une graine indépendante. Inhérent à la recherche A* et à la croissance de clusters ; rédhibitoire pour un décodage temps réel sans borne de temps.
- **Preuves :** [brique-2-resultats.md](brique-2-resultats.md), [lents_s20260929.csv](brique-2/latence/lents_s20260929.csv), [rejeu_s777.csv](brique-2/latence/rejeu_s777.csv)
- **Rejouer :** `.venv/bin/python -m redteam.latency --distance 5 --p 0.002 --decoders tesseract mwpf --scenarios nominal "tout x3" --shots 1000 --seed 777`

### QEC-2026-009 — Un qubit chaud, une fuite ou une rafale non annoncés coûtent ×2 à ×3,7 à tous

- **Cible :** les 9 décodeurs testés (voir requirements-decoders.txt)
- **Date :** 2026-09-29
- **Constat :** Même ordre de grandeur pour tous les décodeurs : c'est le prix d'une calibration périmée, pas un défaut d'un décodeur en particulier.
- **Preuves :** [brique-2-resultats.md](brique-2-resultats.md)
- **Rejouer :** `.venv/bin/python -m redteam.mismatch --distance 5 --p 0.002 --decoders pymatching --only "ancilla chaude x100" "fuite ancilla 1r"`

### QEC-2026-018 — Sur le code XZZX, les décodeurs à hypergraphe battent PyMatching de 15 %, BP+LSD et fusion-blossom via sinter perdent du terrain

- **Cible :** les 9 décodeurs, code XZZX sous bruit biaisé vers Z (pymatching 2.4.0, fusion-blossom 0.2.13 (via sinter 1.16.0), mwpf 0.2.12, tesseract 0.1.1.dev20260822020007, ldpc 2.4.1, stimbposd 0.2.0, beliefmatching 0.2.0, relay-bp 0.2.2)
- **Date :** 2026-10-01
- **Constat :** d = 5, p = 0,002, η = 1000, mémoire X, décodeurs construits sur le vrai DEM, 300 000 tirs appariés par décodeur et par code (graines 21 à 23). Code ordinaire : tous à 0,81–0,87 % sauf fusion-blossom via sinter (1,03 %). XZZX : PyMatching 0,200 % (gain ×4,1) ; tesseract 0,84 [0,80 ; 0,88] fois PyMatching, stimbposd 0,85, mwpf 0,86, BP+OSD 0,90, beliefmatching 0,94, relay-bp 0,98 (n.s.) ; BP+LSD 1,15 [1,09 ; 1,21] (pas dû à notre réglage prudent : lsd_e ordre 2 et 4 donnent 1,12 et 1,16, BP+LSD se comporte comme BP+OSD d'ordre 0, voir QEC-2026-020) ; fusion-blossom via sinter 1,94 [1,82 ; 2,08] (constat 004). Le code XZZX rend les erreurs corrélées plus importantes : les décodeurs qui les voient (hypergraphe) en tirent davantage. Profil, pas défaut, sauf fusion-blossom (constat 004).
- **Preuves :** [xzzx-resultats.md](xzzx-resultats.md), [sweep.py](../research/xzzx-sweep/sweep.py), [analyse.py](../research/xzzx-sweep/analyse.py), [results-d5-eta1000.txt](../research/xzzx-sweep/results-d5-eta1000.txt), [runs](../research/xzzx-sweep/runs), [xzzx.py](../redteam/xzzx.py), [test_xzzx.py](../tests/test_xzzx.py)
- **Rejouer :** `.venv/bin/python research/xzzx-sweep/sweep.py --code xzzx --decoder tesseract --seed 21 --shots 100000 && .venv/bin/python research/xzzx-sweep/analyse.py --seeds 21`

### QEC-2026-019 — Profil sur le gross code (mode gross) : seuls relay-bp et BP+LSD vont au bout ; relay-bp échoue à la cohérence

- **Cible :** décodeurs non limités aux graphes sur le gross code [[144,12,12]] (relay-bp 0.2.2, ldpc 2.4.1, stimbposd 0.2.0, tesseract 0.1.1.dev20260822020007, mwpf 0.2.12)
- **Date :** 2026-10-01
- **Constat :** p = 0,003, ancilla aléatoire au round 6, E1 20 tirs, E2 60 tirs. BP+LSD (lsd_0) : E1 et E2 réussies. relay-bp : E1 réussie, E2 échouée (informé 14/60, réglé 0/60), conséquence des a priori de 1/2 (QEC-2026-016). BP+OSD ordre 10, stimbposd, tesseract, mwpf : délai (stimbposd 27 s par tir, tesseract 20 à 100 s, mwpf et BP+OSD non terminés en 20 et 40 min). Décodeurs de couplage non applicables.
- **Preuves :** [gross.md](profils/gross.md), [relay-bp_gross.json](../research/profil-gross/relay-bp_gross.json), [bplsd_gross.json](../research/profil-gross/bplsd_gross.json), [latence_gross.py](../research/profil-gross/latence_gross.py), [latence-stimbposd.txt](../research/profil-gross/latence-stimbposd.txt), [latence-tesseract.txt](../research/profil-gross/latence-tesseract.txt)
- **Rejouer :** `.venv/bin/python -m redteam.profil relay-bp bplsd --mode gross --out research/profil-gross`

## Ce qui tient

### QEC-2026-008 — Aucun effondrement sous mauvais réglage homogène, dérive, coupleur chaud ou biais Z (mémoires X et Z)

- **Cible :** les 9 décodeurs testés (voir requirements-decoders.txt)
- **Date :** 2026-09-29
- **Constat :** Pénalité de réglage ≤ 1,6 partout (d = 5, p = 0,002, 200 erreurs par cellule). PyMatching tient aussi en latence : p99 < 61 µs dans tous les scénarios. Biais Z, mémoire X, neuf décodeurs (BP+LSD ajouté le 12/10) : pénalités 0,94 à 1,17, sauf fusion-blossom 0,77 (constat 004). Mémoire Z, huit décodeurs sans tesseract (13/10) : le biais divise le taux par 12 ; pénalités 1,04 à 1,39, BP+LSD 1,58 à 1,70, fusion-blossom 0,61 à 0,65 (constat 004) ; aucune exception, relay-bp compris. Mécanisme de la pénalité en mémoire Z : QEC-2026-022.
- **Preuves :** [brique-2-resultats.md](brique-2-resultats.md), [d5_r5_p0.002_z_s20260929_rapides.csv](brique-2/d5_r5_p0.002_z_s20260929_rapides.csv), [d5_r5_p0.002_z_s20260929_lents.csv](brique-2/d5_r5_p0.002_z_s20260929_lents.csv), [d5_r5_p0.002_x_biais_s20260929_biais.csv](brique-2/d5_r5_p0.002_x_biais_s20260929_biais.csv), [d5_r5_p0.002_x_biais_s20260929_biais_lents.csv](brique-2/d5_r5_p0.002_x_biais_s20260929_biais_lents.csv), [d5_r5_p0.002_x_biais_s20260929_bplsd_windows.csv](brique-2/d5_r5_p0.002_x_biais_s20260929_bplsd_windows.csv), [d5_r5_p0.002_z_biais_s20260929_windows.csv](brique-2/d5_r5_p0.002_z_biais_s20260929_windows.csv), [d5_r5_p0.002_z_biais_s20260929_relay_windows.csv](brique-2/d5_r5_p0.002_z_biais_s20260929_relay_windows.csv)
- **Rejouer :** `.venv/bin/python -m redteam.mismatch --distance 5 --p 0.002 --decoders pymatching`

## Pistes ouvertes

### QEC-2026-022 — En mémoire Z, ignorer le biais coûte 16 à 27 % même à PyMatching, alors qu'en mémoire X cela ne coûte rien

- **Cible :** les décodeurs réglés sur le nominal, mémoire Z sous biais Z (PyMatching 2.4.0 et sept autres (voir requirements-decoders.txt))
- **Date :** 2026-10-13
- **Constat :** d = 5, p = 0,002, η = 10 à 1000 : pénalité de réglage de PyMatching 1,17 à 1,23 (banc, graine 20260929), 1,16 à 1,27 rejouée avec les graines 11 à 13 (900 000 tirs, McNemar p ≤ 3e−9) ; 1,00 en mémoire X. Les autres décodeurs : 1,04 à 1,39, BP+LSD 1,58 à 1,70. Observé : en mémoire Z le biais déforme très inégalement le graphe de couplage (arêtes temporelles ×0,89 ; la plupart des arêtes spatiales, diagonales et de bord ×0,001 à η = 1000, mais certaines arêtes des rounds de bord gardent ×0,86) ; en mémoire X tout bouge de ×1,02 à ×1,3. Explication simple réfutée : un PyMatching dont le graphe nominal est corrigé par le facteur médian de chaque classe d'arêtes fait pire que le réglé (1,85 à 1,91 fois l'informé). Mécanisme non établi ; ce n'est pas un défaut (le décodeur informé fait mieux, comme il se doit), mais une sensibilité au réglage à comprendre avant d'en parler.
- **Preuves :** [brique-2-resultats.md](brique-2-resultats.md), [d5_r5_p0.002_z_biais_s20260929_windows.csv](brique-2/d5_r5_p0.002_z_biais_s20260929_windows.csv), [aretes.py](../research/biais-memoire-z/aretes.py), [results-aretes.txt](../research/biais-memoire-z/results-aretes.txt), [results-hybride.txt](../research/biais-memoire-z/results-hybride.txt)
- **Rejouer :** `python research/biais-memoire-z/aretes.py --test --seeds 11 12 13 --shots 300000`

### QEC-2026-023 — BP+OSD un peu meilleur face à PyMatching sous Windows que sous Linux, au nominal, d = 5

- **Cible :** ldpc BpOsdDecoder (BP+OSD osd_cs ordre 10), comparé à PyMatching (ldpc 2.4.1 ; Windows (numpy 2.5.4, scipy 1.18.1) contre Linux (septembre, scipy 1.17.1))
- **Date :** 2026-10-13
- **Constat :** Duels d = 5, p = 0,002, mémoire Z, bruit nominal, 40 000 tirs appariés par graine : BP+OSD / PyMatching = 0,87 [0,77 ; 0,99], 0,81 [0,71 ; 0,92] et 0,96 [0,83 ; 1,11] sous Windows (graines 31 à 33, 13/10), contre 1,07 [0,93 ; 1,23] et 1,03 [0,88 ; 1,20] sous Linux en septembre (graines 31 et 32). Les tirs diffèrent d'une machine à l'autre (graines stim non portables), ce qui n'explique pas un décalage systématique ; les intervalles se touchent à peine et les comptes Linux sont perdus (QEC-2026-021), donc l'écart peut être un hasard. Causes possibles non vérifiées : ordre des colonnes de la matrice de contrôle (scipy), arrondis de BP différents entre compilateurs. Sous diaphonie ZZ, les deux plateformes concordent (2,2 à 2,7). À trancher par un même lot de syndromes décodé sur les deux machines.
- **Preuves :** [brique-2-resultats.md](brique-2-resultats.md), [results-d5-s31-windows.txt](../research/duel-d5/results-d5-s31-windows.txt), [results-d5-s32-windows.txt](../research/duel-d5/results-d5-s32-windows.txt), [results-d5-s33-windows.txt](../research/duel-d5/results-d5-s33-windows.txt)
- **Rejouer :** `python -m redteam.duel --distance 5 --p 0.002 --scenario nominal --decoders pymatching bposd --shots 40000 --seed 31`

## Faux positifs et pistes écartées

### QEC-2026-010 — « Le dédoublonnage est un défaut caché »

- **Cible :** decoder-bench (commit 9733a55)
- **Date :** 2026-09-28
- **Constat :** Première lecture : défaut. La thèse de l'auteur le décrit comme un choix voulu. Reclassé en choix documenté (QEC-2026-001). Leçon : lire la documentation de l'auteur avant de conclure.
- **Preuves :** [constat-001-decoder-bench-dedoublonnage.md](constat-001-decoder-bench-dedoublonnage.md)

### QEC-2026-011 — « La somme des probabilités dégrade relay-bp même sans saturation »

- **Cible :** relay-bp (IBM) (0.2.2)
- **Date :** 2026-09-30
- **Constat :** Écarté : ancilla x100 (aucune arête ≥ 1), 4,85 % publié contre 4,81 % corrigé sur 30 000 tirs, écart non significatif.
- **Preuves :** [results-measure_effect-d5.txt](../research/relay-bp-priors/results-measure_effect-d5.txt)
- **Rejouer :** `.venv/bin/python research/relay-bp-priors/measure_effect.py --distance 5 --shots 10000 --seeds 101 102 103 --scenarios "ancilla chaude x100"`

### QEC-2026-012 — « Remplacer <= par < dans le cœur suffit »

- **Cible :** relay-bp (IBM) (main d185194 + correctif)
- **Date :** 2026-09-30
- **Constat :** Écarté : sur une vraie fuite d'ancilla, 1 301 et 1 303 erreurs sur 10 000 avec le correctif, contre 1 302 et 1 298 sans. Seul le plafonnement sous 1/2 répare.
- **Preuves :** [results-measure_effect-d5-fix.txt](../research/relay-bp-priors/results-measure_effect-d5-fix.txt)

### QEC-2026-017 — « L'adaptateur sinter de tesseract masque des décodages en faible confiance »

- **Cible :** tesseract, adaptateur sinter (tesseract-decoder 0.1.1.dev20260822020007)
- **Date :** 2026-09-30
- **Constat :** L'adaptateur ne transmet pas low_confidence_flag. Mesuré : 0 décodage en faible confiance sur 4 500 tirs (nominal, tout x3, ancilla chaude x100 ; d = 5, p = 0,002, graine 99). Sans effet ici.
- **Preuves :** [probe.py](../research/tesseract-low-confidence/probe.py), [results-probe-s99.txt](../research/tesseract-low-confidence/results-probe-s99.txt)
- **Rejouer :** `.venv/bin/python research/tesseract-low-confidence/probe.py --shots 1500 --seed 99`

### QEC-2026-020 — Fausse piste : BP+LSD derrière BP+OSD sur le code XZZX, expliqué par l'ordre d'OSD

- **Cible :** ldpc BpLsdDecoder sur le code XZZX (ldpc 2.4.1)
- **Date :** 2026-10-01
- **Constat :** d = 5, η = 1000, mêmes tirs : BP+LSD 0,229 % contre BP+OSD (ordre 10) 0,180 % sur 300 000 tirs, alors que les deux sont à égalité sur le code ordinaire (0,824 % et 0,816 %). Graine 21, 100 000 tirs : lsd_0 ordre 0, lsd_e ordre 2 et lsd_e ordre 4 donnent 1,11, 1,12 et 1,16 fois PyMatching. Pas encore établi : rôle des paramètres BP communs (min-sum, 100 itérations), comparaison avec lsd_cs ordre 0. Aucune conclusion tant que la documentation de l'auteur n'a pas été relue. Expliqué le même jour (graine 21, 100 000 tirs, même BP) : BP+OSD d'ordre 0 fait 248 erreurs, BP+LSD lsd_0 244, BP+OSD osd_cs ordre 10 187. BP+LSD se comporte comme BP+OSD d'ordre 0, ce qu'il est censé reproduire par grappe ; le gain vient de la recherche globale d'ordre 10 d'OSD, que l'ordre par grappe de LSD ne remplace pas sur ce code (lsd_e 2 et 4 n'aident pas, 4 bits par pas aggrave : 289). Pas un défaut.
- **Preuves :** [lsd_order.py](../research/xzzx-sweep/lsd_order.py), [results-lsd-order-s21.txt](../research/xzzx-sweep/results-lsd-order-s21.txt), [results-d5-eta1000.txt](../research/xzzx-sweep/results-d5-eta1000.txt), [lsd_vs_osd.py](../research/xzzx-sweep/lsd_vs_osd.py), [results-lsd-vs-osd-s21.txt](../research/xzzx-sweep/results-lsd-vs-osd-s21.txt)
- **Rejouer :** `.venv/bin/python research/xzzx-sweep/lsd_vs_osd.py --shots 100000`

## Nos erreurs de méthode, corrigées avant publication

### QEC-2026-013 — Référence « informée » moyennée sur les positions d'un événement

- **Cible :** notre banc (redteam.mismatch) (avant f62d973)
- **Date :** 2026-09-29
- **Constat :** Pour une fuite tirée au hasard, moyenner le bruit sur toutes les positions donnait une référence pire que le réglage nominal (pénalité 0,55). Remplacée par un décodeur qui connaît la position de chaque événement. Aucun chiffre publié avec l'ancienne méthode.
- **Preuves :** [brique-2-resultats.md](brique-2-resultats.md)

### QEC-2026-014 — « Somme et combinaison diffèrent de moins de 0,1 % » : faux, c'est 2 %

- **Cible :** notre constat 003 (brouillon)
- **Date :** 2026-09-29
- **Constat :** Affirmation du brouillon vérifiée avant publication : écart relatif maximal de 2 % par arête, 23 prédictions sur 20 000 changent. Texte corrigé avant l'envoi.
- **Preuves :** [constat-003-relay-bp-probabilites-additionnees.md](constat-003-relay-bp-probabilites-additionnees.md)

### QEC-2026-021 — Six journaux cités comme preuves n'ont jamais été versionnés : *.log est ignoré par git

- **Cible :** notre registre et notre dépôt (registre du 01/10 (26c4f87))
- **Date :** 2026-10-12
- **Constat :** Le registre du 01/10 citait docs/brique-2/duel_zz_d5_s31.log, duel_zz_d5_s32.log, duel_xx_d5_x_s33.log, duel_zz_d3_s41.log, duel_zz_d7_s42.log et biais_d5_x.log. Ils existaient sur le conteneur de calcul, mais .gitignore ignore *.log et aucun n'a été commité : perdus avec le conteneur, découverts au premier clone. Le vérificateur ne testait que la présence sur le disque ; il refuse désormais toute preuve que git ignorerait (git check-ignore), avec un test. Preuves remplacées par ce qui est versionné et porte les mêmes chiffres (CSV du banc biaisé, fichiers du duel d = 7) et par des rejeux (d = 3 sous Windows, d = 5 sous Linux). Aucun chiffre publié n'est touché, mais les duels d = 5 de septembre ne sont plus rejouables au tir près. Leçon connexe, lue dans la documentation de stim (compile_detector_sampler) : une graine n'est reproductible qu'à machine et version identiques ; sur une autre machine, un rejeu est une réplication indépendante (exemple : mémoire X nominal, PyMatching, 204 erreurs sur 50 000 tirs sous Linux contre 205 sur 46 000 sous Windows, même graine). Rejeux faits (12 et 13/10, Windows) : duels d = 3 graines 41 à 43 et d = 5 graines 31 à 33 pour mwpf et BP+OSD, banc biaisé complété. Non rejoué : tesseract (pas de roue Windows, compilation depuis les sources échouée le 13/10), Linux requis.
- **Preuves :** [registre.py](../redteam/registre.py), [test_registre.py](../tests/test_registre.py), [brique-2-resultats.md](brique-2-resultats.md), [results-d5-s31-windows.txt](../research/duel-d5/results-d5-s31-windows.txt)
- **Rejouer :** `python -m redteam.registre --check`

