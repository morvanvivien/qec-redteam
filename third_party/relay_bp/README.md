# Circuit du gross code, repris de relay-bp

`gross_144_12_12_memory_Z_p0.001.stim` est une copie non modifiée (seul le nom change) de

    tests/testdata/bicycle_bivariate/circuit=bicycle_bivariate_144_12_12_memory_Z,distance=12,rounds=12,error_rate=0.001,noise_model=uniform_circuit,basis=CX,A=x^3+y+y^2,B=y^3+x+x^2.stim

du dépôt https://github.com/trmue/relay (IBM), commit d185194, licence Apache 2.0 (`LICENSE.txt`).

Code bivarié bicyclique [[144, 12, 12]], mémoire Z, 12 rounds, bruit circuit uniforme de probabilité 0,001 sur tous les canaux. `redteam.qldpc` en tire les autres valeurs de p en multipliant toutes les probabilités, ce qui redonne exactement les fichiers d'IBM aux autres taux.
