# qec-redteam

Red team indépendante des décodeurs de correction d'erreurs quantiques. Objectif : trouver, de façon reproductible, les modèles de bruit sous lesquels un décodeur public s'effondre, et en faire une suite de tests que les mainteneurs adoptent. Voir [PLAN.md](PLAN.md).

## Installation

```
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Le venv isole le projet du Python install manager du poste, qui vide `site-packages` à ses mises à jour.

## Lancer

```
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m redteam.baseline --out out/baseline
```

La deuxième commande produit `out/baseline/baseline.csv` et `out/baseline/baseline.png` : taux d'erreur logique par round du code de surface tourné (mémoire Z, d = 3, 5, 7) décodé par PyMatching, sous bruit circuit-level uniforme. Sous le seuil, une distance plus grande doit donner un taux plus bas.

## Reproduire decoder-bench

```
.\.venv\Scripts\python.exe -m redteam.reproduce --out out/decoder_bench
.\.venv\Scripts\python.exe -m redteam.trace <data>\traces
.\.venv\Scripts\python.exe -m redteam.montecarlo --p 0.0005 0.001 --max-shots 50000000
```

La première mesure, sur les mêmes tirs, le taux de Monte Carlo et le taux par syndrome unique, et les compare aux chiffres publiés. La deuxième inspecte les traces publiées. La troisième resserre le Monte Carlo à bas bruit. Résultats et portée dans [docs/constat-001-decoder-bench-dedoublonnage.md](docs/constat-001-decoder-bench-dedoublonnage.md).

## Brique 2 : bruit réel contre bruit nominal

Décodeurs publics en plus (Linux ; relay-bp et tesseract-decoder n'ont pas de roue Windows, et tesseract-decoder pas de roue cp314 : Python 3.11 à 3.13 sous Linux). Sous Windows, installer les sept autres (`ldpc`, `stimbposd`, `mwpf`, `fusion-blossom`, `scipy`, et `beliefmatching` avec `--no-deps`, sa borne numpy excluant Python 3.14) ; relay-bp se compile depuis sa sdist avec rustup (chaîne GNU, sans MSVC) et maturin (voir `research/relay-bp-priors/environnement-core-fix-windows.txt`) ; la suite de tests saute les tests des décodeurs absents au lieu d'échouer :

```
.venv/bin/pip install -r requirements-decoders.txt
.venv/bin/python -m redteam.mismatch --distance 5 --p 0.002 --decoders pymatching bposd relay-bp
.venv/bin/python -m redteam.duel --distance 5 --p 0.002 --scenario nominal "diaphonie ZZ 3p" --decoders pymatching tesseract
.venv/bin/python -m redteam.latency --distance 5 --p 0.002 --decoders pymatching tesseract
.venv/bin/python -m redteam.confirm --scenario "ancilla chaude x100" --decoder bposd
.venv/bin/python -m redteam.report out/mismatch/*.csv --latency out/latency/*/*.csv
```

Résultats dans [docs/brique-2-resultats.md](docs/brique-2-resultats.md), cassure confirmée dans [docs/constat-003-relay-bp-probabilites-additionnees.md](docs/constat-003-relay-bp-probabilites-additionnees.md).

## Structure

- `redteam/circuits.py` : circuits de référence (stim), bruit uniforme ou SI1000.
- `redteam/noise.py` : bruit SI1000, modèle de decoder-bench repris tel quel.
- `redteam/baseline.py` : expérience de seuil (sinter + pymatching).
- `redteam/reproduce.py` : reproduction des chiffres publiés de decoder-bench.
- `redteam/dedup.py` : dédoublonnage des syndromes à l'identique de leur générateur.
- `redteam/trace.py` : inspection des traces HDF5 publiées.
- `redteam/montecarlo.py` : Monte Carlo de référence.
- `redteam/stats.py` : comparaison de deux taux, intervalle de Wilson, rapport apparié par bootstrap, test de McNemar.
- `redteam/perturb.py` : réécriture du bruit SI1000 site par site (qubit, coupleur, round, type), diaphonie corrélée, biais Z.
- `redteam/scenarios.py` : catalogue des bruits réels (homogène, local, corrélé, temporel, biaisé), fuites et rafales par mélange de circuits.
- `redteam/decoders.py` : neuf décodeurs publics derrière une même interface, garde-fou ldpc #105.
- `redteam/mismatch.py` : banc de désaccord, décodeur réglé contre décodeur informé sur les mêmes tirs, une cellule par processus.
- `redteam/duel.py` : décodeurs réglés sur les mêmes tirs, pour affirmer un renversement de classement.
- `redteam/latency.py` : latence tir par tir, p50 à max.
- `redteam/confirm.py` : rejeu d'une cellule depuis zéro, même graine puis graines indépendantes.
- `redteam/report.py` : tableaux Markdown des résultats.
- `redteam/profil.py` : profil de robustesse QEC v0.1, cinq épreuves, mode rapide pour l'intégration continue ; méthode dans [docs/profil-robustesse-v0.1.md](docs/profil-robustesse-v0.1.md), logo dans `docs/logo/`.
- `redteam/registre.py` : registre de tout ce qui a été trouvé, écarté ou laissé ouvert ([docs/registre.md](docs/registre.md)).
- `redteam/qldpc.py` : gross code [[144,12,12]] d'IBM, repris de relay-bp (`third_party/relay_bp/`, Apache 2.0).
- `third_party/decoder_bench/` : fichiers de decoder-bench, non modifiés, licence MIT.
- `docs/` : sources, constats, textes des issues envoyées ou en attente.
- `research/ldpc-105/` : cause, reproductions et correctif vérifié du défaut mémoire de ldpc (issue #105), en anglais pour les mainteneurs.
- `research/relay-bp-priors/` : reproductions, mesures et correctifs des deux défauts de relay-bp (constat 003), en anglais.
- `tests/` : 112 tests, 25 secondes environ.
- `out/` : résultats, non versionnés.
