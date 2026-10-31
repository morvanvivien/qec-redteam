"""Profil de robustesse QEC v0.1 : cinq épreuves reproductibles pour un décodeur public.

Un profil décrit un décodeur ; il ne l'homologue pas. Chaque épreuve fixe son
code, son bruit, sa graine et son nombre de tirs : deux personnes qui lancent
la même version obtiennent les mêmes chiffres. Méthode : docs/profil-robustesse-v0.1.md.

    E1 Tenue        décode sans exception un DEM valide contenant un qubit saturé ;
                    syndrome nul -> prédiction nulle ; mêmes tirs -> mêmes sorties.
    E2 Cohérence    le vrai modèle d'erreurs ne doit pas nuire : informé d'une fuite,
                    le décodeur ne fait pas significativement pire que réglé.
    E3 Désaccord    pénalité de réglage (réglé / informé) sur trois bruits réels.
    E4 Classement   taux rapporté à PyMatching, sous bruit nominal et sous diaphonie ZZ.
    E5 Latence      p50, p99, max par tir, nominal et bruit perturbé.

Mode « rapide » (E1 et E2, d = 3, moins d'une minute pour un décodeur rapide) :
pensé pour l'intégration continue d'une bibliothèque. Mode « complet » : les cinq.
Mode « gross » : E1 et E2 sur le gross code [[144,12,12]] d'IBM, p = 0,003,
une ancilla rendue aléatoire au round du milieu ; les décodeurs de couplage
(graphe seulement) y sont « non applicables », le modèle n'étant pas décomposable.

    python -m redteam.profil pymatching --mode rapide
    python -m redteam.profil relay-bp --mode complet --out docs/profils
"""

import argparse
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from redteam.decoders import REGISTRY, build, dem_for
from redteam.duel import duel
from redteam.latency import measure
from redteam.mismatch import Setup, run_cell, sample
from redteam.scenarios import Scenario, central_ancilla, randomize
from redteam.stats import paired_ratio

VERSION = "0.1"
SEED = 20261001
REUSSIE, ECHOUEE, NON_MESURABLE, NON_APPLICABLE = "réussie", "échouée", "non mesurable", "non applicable"
QUICK = Setup(3, 3, 0.002)
GROSS = Setup(12, 12, 0.003, code="gross")
MATCHING = {"pymatching", "fusion-blossom", "beliefmatching"}


@dataclass
class Epreuve:
    code: str
    nom: str
    verdict: str
    note: str = ""
    mesures: dict = field(default_factory=dict)
    detail: str = ""


@dataclass
class Profil:
    decodeur: str
    version_profil: str
    mode: str
    epreuves: list[Epreuve]

    @property
    def tenue(self) -> bool:
        return all(e.verdict != ECHOUEE for e in self.epreuves if e.code in ("E1", "E2"))


def saturated(setup: Setup) -> Scenario:
    """Une ancilla centrale rendue complètement aléatoire au round du milieu."""
    nominal = setup.nominal()
    if setup.code == "gross":
        from redteam.qldpc import data_and_ancillas

        q = data_and_ancillas(nominal)[1][0]
    else:
        q = central_ancilla(nominal)
    middle = setup.rounds // 2
    return Scenario("fuite ancilla centrale", "corrélé", f"ancilla {q} aléatoire au round {middle}", (randomize({q}, middle, middle),))


def grade(value: float, bounds: tuple[float, float, float]) -> str:
    return "A" if value <= bounds[0] else "B" if value <= bounds[1] else "C" if value <= bounds[2] else "D"


def e1_tenue(decoder: str, shots: int = 500, setup: Setup = QUICK) -> Epreuve:
    nominal = setup.nominal()
    leak = saturated(setup).true_circuits(nominal)[0]
    checks = {}
    try:
        tuned = build(decoder, dem_for(nominal))
        dets, _ = nominal.compile_detector_sampler(seed=SEED).sample(shots, separate_observables=True)
        first, second = tuned.decode(dets), build(decoder, dem_for(nominal)).decode(dets)
        checks["déterministe"] = bool(np.array_equal(first, second))
        zero = np.zeros((1, nominal.num_detectors), dtype=bool)
        checks["syndrome nul, DEM nominal"] = not tuned.decode(zero).any()
        informed = build(decoder, dem_for(leak))
        leak_dets, _ = leak.compile_detector_sampler(seed=SEED).sample(shots, separate_observables=True)
        informed.decode(leak_dets)
        checks["DEM saturé décodé"] = True
        checks["syndrome nul, DEM saturé"] = not informed.decode(zero).any()
    except Exception as error:  # une exception est le résultat de l'épreuve
        failed = next((k for k in ("déterministe", "syndrome nul, DEM nominal", "DEM saturé décodé") if k not in checks), "DEM saturé décodé")
        checks[failed] = False
        return Epreuve("E1", "Tenue", ECHOUEE, "", checks, f"{type(error).__name__}: {error}"[:200])
    verdict = REUSSIE if all(checks.values()) else ECHOUEE
    return Epreuve("E1", "Tenue", verdict, "", checks, ", ".join(k for k, v in checks.items() if not v))


def e2_coherence(decoder: str, shots: int = 4000, setup: Setup = QUICK) -> Epreuve:
    try:
        cell = run_cell(setup, saturated(setup), decoder, SEED, target_errors=10**9, max_shots=shots)
    except Exception as error:
        return Epreuve("E2", "Cohérence", NON_MESURABLE, "", {}, f"{type(error).__name__}: {error}"[:200])
    ratio, low, high = paired_ratio(cell.both, cell.only_informed, cell.only_tuned, cell.shots, seed=SEED)
    mesures = {"tirs": cell.shots, "erreurs réglé": cell.errors_tuned, "erreurs informé": cell.errors_informed,
               "informé / réglé": round(ratio, 3), "IC 95 %": [round(low, 3), round(high, 3)]}
    verdict = ECHOUEE if low > 1.0 else REUSSIE
    return Epreuve("E2", "Cohérence", verdict, "", mesures, "informé significativement pire que réglé" if verdict == ECHOUEE else "")


E3_SCENARIOS = ("ancilla chaude x100", "fuite ancilla 1r", "diaphonie ZZ 3p")


def e3_desaccord(decoder: str, target: int = 100, max_shots: int = 40_000) -> Epreuve:
    setup = Setup(5, 5, 0.002)
    by_name = {s.name: s for s in setup.scenarios()}
    mesures, worst = {}, 0.0
    for name in E3_SCENARIOS:
        try:
            cell = run_cell(setup, by_name[name], decoder, SEED, target, max_shots)
        except Exception as error:
            mesures[name] = f"{type(error).__name__}"
            continue
        ratio, low, high = cell.penalty()
        mesures[name] = {"pénalité": round(ratio, 2), "IC 95 %": [round(low, 2), round(high, 2)], "tirs": cell.shots}
        worst = max(worst, ratio)
    measured = [v for v in mesures.values() if isinstance(v, dict)]
    if not measured:
        return Epreuve("E3", "Désaccord", NON_MESURABLE, "", mesures)
    if len(measured) < len(E3_SCENARIOS):
        return Epreuve("E3", "Désaccord", NON_MESURABLE, "", mesures, f"pire pénalité mesurée {worst:.2f}")
    return Epreuve("E3", "Désaccord", REUSSIE, grade(worst, (1.5, 2.5, 4.0)), mesures, f"pire pénalité {worst:.2f}")


def e4_classement(decoder: str, shots: int = 20_000) -> Epreuve:
    setup = Setup(5, 5, 0.002)
    names = ["pymatching"] if decoder == "pymatching" else ["pymatching", decoder]
    mesures = {}
    for scenario in ("nominal", "diaphonie ZZ 3p"):
        result = duel(setup, scenario, names, shots, SEED)
        if decoder == "pymatching":
            mesures[scenario] = {"/ PyMatching": 1.0}
            continue
        ratio, low, high, _ = result.versus(decoder, "pymatching", SEED)
        mesures[scenario] = {"/ PyMatching": round(ratio, 2), "IC 95 %": [round(low, 2), round(high, 2)]}
    shift = mesures["diaphonie ZZ 3p"]["/ PyMatching"] / mesures["nominal"]["/ PyMatching"]
    return Epreuve("E4", "Classement", REUSSIE, grade(shift, (1.1, 1.5, 2.5)), mesures, f"glissement relatif à PyMatching x{shift:.2f}")


def e5_latence(decoder: str, shots: int = 1000) -> Epreuve:
    setup = Setup(5, 5, 0.002)
    mesures = {}
    for scenario in ("nominal", "tout x3"):
        summary, _, _ = measure(setup, scenario, decoder, shots, SEED)
        mesures[scenario] = {"p50 µs": round(summary.p50_us), "p99 µs": round(summary.p99_us), "max µs": round(summary.max_us), "plancher µs": round(summary.floor_us, 1)}
    tail = mesures["tout x3"]["p99 µs"] / max(mesures["nominal"]["p99 µs"], 1)
    return Epreuve("E5", "Latence", REUSSIE, grade(tail, (2.0, 5.0, 20.0)), mesures, f"p99 perturbé / p99 nominal x{tail:.1f}")


def profile(decoder: str, mode: str = "rapide") -> Profil:
    if decoder not in REGISTRY:
        raise ValueError(f"décodeur inconnu {decoder!r}")
    if mode == "gross":
        if decoder in MATCHING:
            note = "décodeur de couplage : le modèle du gross code n'est pas décomposable en graphe"
            return Profil(decoder, VERSION, mode, [Epreuve("E1", "Tenue", NON_APPLICABLE, "", {}, note), Epreuve("E2", "Cohérence", NON_APPLICABLE, "", {}, note)])
        return Profil(decoder, VERSION, mode, [e1_tenue(decoder, 20, GROSS), e2_coherence(decoder, 60, GROSS)])
    epreuves = [e1_tenue(decoder), e2_coherence(decoder)]
    if mode == "complet":
        epreuves += [e3_desaccord(decoder), e4_classement(decoder), e5_latence(decoder)]
    return Profil(decoder, VERSION, mode, epreuves)


def card(profil: Profil) -> str:
    lines = [f"### {profil.decodeur} — profil de robustesse QEC v{profil.version_profil} ({profil.mode})", "",
             "| Épreuve | Verdict | Note | Détail |", "|---|---|---|---|"]
    for e in profil.epreuves:
        lines.append(f"| {e.code} {e.nom} | {e.verdict} | {e.note or '—'} | {e.detail or '—'} |")
    return "\n".join(lines)


def badge(profil: Profil) -> str:
    """Badge SVG : « profil QEC v0.1 » puis la tenue et les notes."""
    notes = " ".join(f"{e.code}:{e.note or ('ok' if e.verdict == REUSSIE else '✗' if e.verdict == ECHOUEE else '?')}" for e in profil.epreuves)
    right = f"{profil.decodeur} {notes}"
    color = "#2E7D32" if profil.tenue else "#C62828"
    left_w, right_w = 118, 12 + 6.6 * len(right)
    width = left_w + right_w
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="20" role="img" aria-label="profil QEC v{profil.version_profil}: {right}">'
            f'<rect width="{left_w}" height="20" fill="#1B2A4A"/><rect x="{left_w}" width="{right_w:.0f}" height="20" fill="{color}"/>'
            f'<g fill="#fff" font-family="Helvetica,Arial,sans-serif" font-size="11">'
            f'<text x="8" y="14">profil QEC v{profil.version_profil}</text><text x="{left_w + 6}" y="14">{right}</text></g></svg>')


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Profil de robustesse QEC d'un décodeur.")
    parser.add_argument("decoders", nargs="+", choices=sorted(REGISTRY))
    parser.add_argument("--mode", choices=("rapide", "complet", "gross"), default="rapide")
    parser.add_argument("--out", type=Path, default=Path("out/profils"))
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    failed = False
    for decoder in args.decoders:
        profil = profile(decoder, args.mode)
        print(card(profil), flush=True)
        (args.out / f"{decoder}_{args.mode}.json").write_text(json.dumps(asdict(profil), ensure_ascii=False, indent=1), encoding="utf-8")
        (args.out / f"{decoder}_{args.mode}.svg").write_text(badge(profil), encoding="utf-8")
        failed |= not profil.tenue
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
