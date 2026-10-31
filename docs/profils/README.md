# Profils de robustesse QEC v0.1 — 9 décodeurs publics

Mesurés du 30/09/2026 sur Linux, 4 cœurs, graine 20261001 ; méthode dans [../profil-robustesse-v0.1.md](../profil-robustesse-v0.1.md). E1 à E4 : code de surface ; E5 (latence) refaite sur machine au calme, 1 000 tirs par scénario. Un JSON par décodeur dans ce dossier.

| Décodeur | E1 Tenue | E2 Cohérence | E3 Désaccord | E4 Classement | E5 Latence | p99 nominal → perturbé |
|---|---|---|---|---|---|---|
| pymatching | réussie | réussie | C | A | B | 24 → 49 µs |
| fusion-blossom | réussie | réussie | C | A | B | 364 → 1 228 µs |
| beliefmatching | réussie | réussie | C | C | A | 6 757 → 9 177 µs |
| bplsd | réussie | réussie | C | C | B | 4 875 → 12 299 µs |
| bposd | réussie | réussie | C | C | A | 14 730 → 15 808 µs |
| stimbposd | réussie | réussie | C | C | A | 30 028 → 34 865 µs |
| relay-bp | **échouée** | non mesurable | non mesurable | A | B | 1 869 → 6 973 µs |
| tesseract | réussie | réussie | C | C | C | 17 152 → 334 907 µs |
| mwpf | réussie | réussie | C | D | B | 181 305 → 495 342 µs |

Notes : A meilleur, D moins bon, selon les seuils de la méthode. E3 : pire pénalité de réglage sur trois bruits réels. E4 : glissement du rapport à PyMatching entre bruit nominal et diaphonie ZZ (PyMatching = référence). relay-bp échoue E1 par une exception à chaque décodage (constat 003) ; ses épreuves qui en dépendent ne sont pas mesurables.

- **pymatching** : E3 pire pénalité 3.90 ; E4 glissement relatif à PyMatching x1.00 ; E5 p99 perturbé / p99 nominal x2.0
- **fusion-blossom** : E3 pire pénalité 3.35 ; E4 glissement relatif à PyMatching x0.91 ; E5 p99 perturbé / p99 nominal x3.4
- **beliefmatching** : E3 pire pénalité 2.92 ; E4 glissement relatif à PyMatching x1.69 ; E5 p99 perturbé / p99 nominal x1.4
- **bplsd** : E3 pire pénalité 2.94 ; E4 glissement relatif à PyMatching x2.21 ; E5 p99 perturbé / p99 nominal x2.5
- **bposd** : E3 pire pénalité 3.33 ; E4 glissement relatif à PyMatching x2.17 ; E5 p99 perturbé / p99 nominal x1.1
- **stimbposd** : E3 pire pénalité 3.44 ; E4 glissement relatif à PyMatching x2.35 ; E5 p99 perturbé / p99 nominal x1.2
- **relay-bp** : E3 pire pénalité 2.58 ; E4 glissement relatif à PyMatching x0.88 ; E5 p99 perturbé / p99 nominal x3.7
- **tesseract** : E3 pire pénalité 3.62 ; E4 glissement relatif à PyMatching x2.37 ; E5 p99 perturbé / p99 nominal x19.5
- **mwpf** : E3 pire pénalité 3.97 ; E4 glissement relatif à PyMatching x4.02 ; E5 p99 perturbé / p99 nominal x2.7
