"""Biais Z en mémoire Z : comment le biais déforme le graphe de couplage que voit PyMatching.

Question : sous biais Z, en mémoire X, la pénalité de réglage de PyMatching est 1,00 ;
en mémoire Z, elle est de 1,17 à 1,23. Explication proposée : en mémoire Z, l'observable
est retournée par les erreurs X, que le biais raréfie (p X ≈ p / (2 (η + 1)) au lieu de p / 3),
alors que les retournements de mesure et de réinitialisation ne changent pas. Les arêtes
« temporelles » (même stabilisateur, deux rounds consécutifs, surtout des erreurs de
mesure) deviennent beaucoup plus probables que les arêtes « spatiales » (erreurs X sur
les données) : un décodeur réglé sur le nominal, qui les croit comparables, apparie mal.
En mémoire X, les erreurs Z utiles passent de p / 3 à environ p / 2 : le rapport change
à peine.

Sans option, le script mesure, sur le graphe de PyMatching (arêtes parallèles fusionnées),
le rapport des probabilités d'arête vrai / nominal, séparément pour les arêtes temporelles,
spatiales et de bord, dans la composante qui porte l'observable. Cela appuie l'explication
sans la démontrer. Le test décisif (`--test`) : un PyMatching « hybride », construit sur le
graphe nominal dont chaque classe d'arêtes est multipliée par un seul facteur, la médiane
de sa classe. S'il retrouve le taux du décodeur informé sur les mêmes tirs, c'est bien le
rapport entre classes qui coûte, pas le détail arête par arête.

    python research/biais-memoire-z/aretes.py
    python research/biais-memoire-z/aretes.py --test --seeds 11 12 13 --shots 300000
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pymatching

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from redteam.decoders import dem_for  # noqa: E402
from redteam.mismatch import Setup, sample  # noqa: E402
from redteam.stats import mcnemar_p, paired_ratio, wilson  # noqa: E402

KINDS = ("temporelle", "spatiale", "diagonale", "bord")


def edges(dem) -> dict:
    """(u, v) -> (probabilité, observables) du graphe de PyMatching ; v = None pour le bord."""
    out = {}
    for u, v, data in pymatching.Matching.from_detector_error_model(dem).edges():
        out[(u, v)] = (data["error_probability"], frozenset(data.get("fault_ids", set())))
    return out


def observable_component(graph: dict) -> set:
    """Détecteurs de la composante connexe qui contient une arête retournant l'observable."""
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for u, v in graph:
        find(u)
        if v is not None:
            parent[find(u)] = find(v)
    roots = {find(u) for (u, v), (_, obs) in graph.items() if obs}
    return {d for d in parent if find(d) in roots}


def classify(u, v, coords) -> str:
    """Temporelle : même stabilisateur, rounds voisins. Spatiale : même round. Diagonale : les deux changent (erreurs de porte « crochet »)."""
    if v is None:
        return "bord"
    (xu, yu, tu, *_), (xv, yv, tv, *_) = coords[u], coords[v]
    if (xu, yu) == (xv, yv):
        return "temporelle"
    return "spatiale" if tu == tv else "diagonale"


def class_ratios(reference: dict, true: dict, component: set, coords) -> dict:
    ratios = {kind: [] for kind in KINDS}
    for key, (p_nominal, _) in reference.items():
        if key[0] in component and key in true:
            ratios[classify(*key, coords)].append(true[key][0] / p_nominal)
    return {kind: r for kind, r in ratios.items() if r}


def hybrid(reference: dict, factors: dict, coords) -> pymatching.Matching:
    """Graphe nominal, chaque arête multipliée par le facteur médian de sa classe."""
    m = pymatching.Matching()
    for (u, v), (p, obs) in reference.items():
        q = min(p * factors.get(classify(u, v, coords), 1.0), 0.5)
        if v is None:
            m.add_boundary_edge(u, fault_ids=set(obs), error_probability=q)
        else:
            m.add_edge(u, v, fault_ids=set(obs), error_probability=q)
    return m


def describe() -> None:
    for basis in ("z", "x"):
        setup = Setup(5, 5, 0.002, basis, True)
        nominal = setup.nominal()
        nominal_dem = dem_for(nominal)
        coords = nominal_dem.get_detector_coordinates()
        reference = edges(nominal_dem)
        component = observable_component(reference)
        print(f"\nmémoire {basis.upper()}, d = 5, p = 0,002 : {len(component)} détecteurs dans la composante de l'observable")
        for scenario in setup.scenarios()[1:]:
            ratios = class_ratios(reference, edges(dem_for(scenario.true_circuits(nominal)[0])), component, coords)
            summary = ", ".join(f"{kind} {len(r)} arêtes, médiane {np.median(r):.3f} [{np.min(r):.3f} ; {np.max(r):.3f}]" for kind, r in ratios.items())
            print(f"  {scenario.name:18s} rapport vrai / nominal : {summary}")


def test(seeds: list[int], shots: int) -> None:
    setup = Setup(5, 5, 0.002, "z", True)
    nominal = setup.nominal()
    nominal_dem = dem_for(nominal)
    coords = nominal_dem.get_detector_coordinates()
    reference = edges(nominal_dem)
    component = observable_component(reference)
    tuned = pymatching.Matching.from_detector_error_model(nominal_dem)
    for scenario in setup.scenarios()[1:]:
        circuit = scenario.true_circuits(nominal)[0]
        true_dem = dem_for(circuit)
        factors = {kind: float(np.median(r)) for kind, r in class_ratios(reference, edges(true_dem), component, coords).items()}
        decoders = {"réglé": tuned, "hybride": hybrid(reference, factors, coords), "informé": pymatching.Matching.from_detector_error_model(true_dem)}
        wrong = {name: [] for name in decoders}
        for seed in seeds:
            dets, obs, _ = sample([circuit], shots, seed)
            for name, decoder in decoders.items():
                wrong[name].append(np.any(decoder.decode_batch(dets) != obs, axis=1))
        wrong = {name: np.concatenate(w) for name, w in wrong.items()}
        n = len(wrong["réglé"])
        print(f"\nmémoire Z, {scenario.name}, facteurs médians {', '.join(f'{k} {v:.4f}' for k, v in factors.items())}, {n} tirs (graines {seeds})")
        for name, w in wrong.items():
            low, high = wilson(int(w.sum()), n)
            line = f"  {name:8s} {int(w.sum()):5d} erreurs, {w.mean():.3e} [{low:.3e}, {high:.3e}]"
            if name != "informé":
                a, b = w, wrong["informé"]
                both, only_a, only_b = int((a & b).sum()), int((a & ~b).sum()), int((~a & b).sum())
                ratio, rlow, rhigh = paired_ratio(both, only_a, only_b, n, seed=seeds[0])
                line += f" | {name}/informé = {ratio:.3f} [{rlow:.3f}, {rhigh:.3f}], McNemar p = {mcnemar_p(only_a, only_b):.1e}"
            print(line, flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="test décisif : PyMatching hybride contre réglé et informé, mêmes tirs")
    parser.add_argument("--seeds", type=int, nargs="+", default=[11, 12, 13])
    parser.add_argument("--shots", type=int, default=300_000)
    args = parser.parse_args()
    if args.test:
        test(args.seeds, args.shots)
    else:
        describe()


if __name__ == "__main__":
    main()
