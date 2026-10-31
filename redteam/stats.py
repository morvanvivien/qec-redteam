"""Comparaison de taux d'erreur mesurés sur des nombres de tirs différents."""

import math


def two_proportion_z(errors_a: int, shots_a: int, errors_b: int, shots_b: int) -> float:
    """Écart entre deux taux, en écarts types, sous l'hypothèse d'un taux commun.

    Positif quand le taux de A dépasse celui de B. Au delà de 3 en valeur
    absolue, les deux mesures ne décrivent pas la même grandeur.
    """
    if shots_a <= 0 or shots_b <= 0:
        raise ValueError(f"nombres de tirs positifs attendus, reçu {shots_a} et {shots_b}")
    if not (0 <= errors_a <= shots_a and 0 <= errors_b <= shots_b):
        raise ValueError(f"erreurs entre 0 et le nombre de tirs attendues, reçu {errors_a}/{shots_a} et {errors_b}/{shots_b}")
    pooled = (errors_a + errors_b) / (shots_a + shots_b)
    variance = pooled * (1.0 - pooled) * (1.0 / shots_a + 1.0 / shots_b)
    if variance == 0.0:
        return 0.0
    return (errors_a / shots_a - errors_b / shots_b) / math.sqrt(variance)


def wilson(errors: int, shots: int, z: float = 1.96) -> tuple[float, float]:
    """Intervalle de Wilson à 95 % d'un taux errors / shots."""
    if shots <= 0 or not 0 <= errors <= shots:
        raise ValueError(f"0 <= erreurs <= tirs attendu, reçu {errors}/{shots}")
    rate = errors / shots
    denominator = 1.0 + z * z / shots
    center = (rate + z * z / (2 * shots)) / denominator
    half = z * math.sqrt(rate * (1.0 - rate) / shots + z * z / (4 * shots * shots)) / denominator
    return max(0.0, center - half), min(1.0, center + half)


def paired_ratio(both: int, only_a: int, only_b: int, shots: int, resamples: int = 20_000, seed: int = 0) -> tuple[float, float, float]:
    """Rapport des taux d'erreur de A sur B, mesurés sur les mêmes tirs, et son intervalle à 95 %.

    `both` : tirs où A et B se trompent ; `only_a`, `only_b` : un seul des deux.
    L'intervalle vient d'un bootstrap multinomial sur les quatre cases, ce qui
    tient compte de la corrélation entre les deux décodages. Rapport infini
    quand B ne se trompe jamais.
    """
    import numpy as np

    if min(both, only_a, only_b) < 0 or both + only_a + only_b > shots:
        raise ValueError(f"cases incohérentes : {both}, {only_a}, {only_b} sur {shots}")
    errors_a, errors_b = both + only_a, both + only_b
    ratio = math.inf if errors_b == 0 else errors_a / errors_b
    rng = np.random.default_rng(seed)
    cells = np.array([both, only_a, only_b, shots - both - only_a - only_b]) / shots
    draws = rng.multinomial(shots, cells, size=resamples)
    a, b = draws[:, 0] + draws[:, 1], draws[:, 0] + draws[:, 2]
    with np.errstate(divide="ignore", invalid="ignore"):
        ratios = np.where(b > 0, a / np.maximum(b, 1), np.inf)
    big = np.finfo(float).max
    low, high = (math.inf if q >= big else float(q) for q in np.quantile(np.minimum(ratios, big), [0.025, 0.975]))
    return ratio, low, high


def mcnemar_p(only_a: int, only_b: int) -> float:
    """Valeur p exacte bilatérale de McNemar : A et B se trompent-ils aussi souvent ?"""
    n = only_a + only_b
    if n == 0:
        return 1.0
    k = min(only_a, only_b)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2.0 * tail)
