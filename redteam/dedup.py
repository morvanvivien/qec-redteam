"""Dédoublonnage des syndromes, à l'identique de la génération de traces de decoder-bench.

Leur générateur ne stocke qu'un syndrome jamais vu, avec l'observable de sa
première occurrence, et s'arrête à l'enregistrement qui atteint la cible.

Les syndromes déjà vus sont tenus dans un tableau numpy trié de clés opaques,
une par ligne : 42 octets par syndrome à d = 7, contre plus de 100 pour un
ensemble Python, et aucune boucle Python sur les lignes.
"""

import numpy as np


def as_keys(rows: np.ndarray) -> np.ndarray:
    """Une clé opaque par ligne, comparée octet par octet."""
    contiguous = np.ascontiguousarray(rows)
    return contiguous.view(np.dtype((np.void, contiguous.shape[1]))).ravel()


def empty_seen(width: int) -> np.ndarray:
    """Ensemble vide de syndromes vus, pour des lignes de `width` octets."""
    if width <= 0:
        raise ValueError(f"largeur positive attendue, reçu {width}")
    return np.empty(0, dtype=np.dtype((np.void, width)))


def first_occurrences(
    rows: np.ndarray,
    seen: np.ndarray,
    remaining: int,
) -> tuple[np.ndarray, np.ndarray, int | None]:
    """Masque des lignes jamais vues, nouveau tableau des lignes vues, indice d'arrêt.

    `remaining` est le nombre d'enregistrements encore à collecter. L'indice
    d'arrêt est celui de la ligne qui atteint la cible, None si elle n'est pas
    atteinte dans ce lot. `seen` n'est pas modifié.
    """
    if remaining <= 0:
        raise ValueError(f"nombre d'enregistrements restants positif attendu, reçu {remaining}")

    keys = as_keys(rows)
    batch_unique, first_index = np.unique(keys, return_index=True)
    never_seen = ~np.isin(batch_unique, seen, assume_unique=True)
    kept_index = np.sort(first_index[never_seen])

    stopped_at = None
    if len(kept_index) >= remaining:
        kept_index = kept_index[:remaining]
        stopped_at = int(kept_index[-1])

    mask = np.zeros(len(rows), dtype=bool)
    mask[kept_index] = True
    return mask, np.union1d(seen, keys[kept_index]), stopped_at
