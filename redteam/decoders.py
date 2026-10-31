"""Décodeurs publics derrière une interface unique : DEM en entrée, prédictions en sortie.

Chaque entrée du registre construit, à partir d'un modèle d'erreurs de
détecteurs (DEM), un objet `decode(dets) -> predictions` sur des tableaux
booléens (tirs, détecteurs) -> (tirs, observables).

Paramètres : ceux de decoder-bench quand il teste la bibliothèque (ldpc,
relay-bp, mwpf), sinon les défauts documentés par l'auteur.

Garde-fou ldpc (constat 002, issue ldpc #105) : le balayage combinatoire
d'OSD écrit hors limites quand l'ordre dépasse la dimension k. BP+OSD n'est
construit que si l'ordre est strictement inférieur à k de la matrice entière ;
BP+LSD tourne en `lsd_0`, ordre 0, qui ne produit aucune paire quel que soit
le cluster.
"""

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import stim

OSD_ORDER = 10
BP_MAX_ITER = 100


def dem_for(circuit: stim.Circuit) -> stim.DetectorErrorModel:
    """DEM tel que sinter le construit : erreurs décomposées quand c'est possible."""
    return circuit.detector_error_model(
        decompose_errors=True,
        approximate_disjoint_errors=True,
        ignore_decomposition_failures=True,
    )


class Compiled:
    def decode(self, dets: np.ndarray) -> np.ndarray:
        raise NotImplementedError


@dataclass
class SinterCompiled(Compiled):
    compiled: object
    num_detectors: int
    num_observables: int

    def decode(self, dets: np.ndarray) -> np.ndarray:
        packed = np.packbits(dets.astype(np.uint8), axis=1, bitorder="little")
        out = self.compiled.decode_shots_bit_packed(bit_packed_detection_event_data=packed)
        return np.unpackbits(out, axis=1, bitorder="little", count=self.num_observables).astype(bool)


def _sinter(decoder: object) -> Callable[[stim.DetectorErrorModel], Compiled]:
    def build(dem: stim.DetectorErrorModel) -> Compiled:
        return SinterCompiled(decoder.compile_decoder_for_dem(dem=dem), dem.num_detectors, dem.num_observables)
    return build


@dataclass
class MatrixCompiled(Compiled):
    """Décodeur de ldpc qui rend une correction ; l'observable s'en déduit."""

    decoder: object
    observables: object

    def decode(self, dets: np.ndarray) -> np.ndarray:
        out = np.zeros((dets.shape[0], self.observables.shape[0]), dtype=bool)
        for shot, syndrome in enumerate(dets.astype(np.uint8)):
            correction = self.decoder.decode(syndrome)
            out[shot] = (self.observables @ correction) % 2
        return out


def _matrices(dem: stim.DetectorErrorModel):
    from beliefmatching import detector_error_model_to_check_matrices

    return detector_error_model_to_check_matrices(dem, allow_undecomposed_hyperedges=True)


def osd_dimension(check_matrix) -> int:
    """k = nombre de colonnes moins le rang, la borne des candidats d'OSD."""
    from ldpc.mod2 import rank

    return check_matrix.shape[1] - rank(check_matrix)


def build_bposd(dem: stim.DetectorErrorModel, order: int = OSD_ORDER) -> Compiled:
    from ldpc import BpOsdDecoder

    m = _matrices(dem)
    k = osd_dimension(m.check_matrix)
    if order >= k:
        raise ValueError(f"ordre OSD {order} >= k = {k} : écriture hors limites (ldpc #105), refusé")
    decoder = BpOsdDecoder(
        m.check_matrix, error_channel=list(m.priors), max_iter=BP_MAX_ITER,
        bp_method="minimum_sum", osd_method="osd_cs", osd_order=order,
    )
    return MatrixCompiled(decoder, m.observables_matrix)


def build_bplsd(dem: stim.DetectorErrorModel) -> Compiled:
    from ldpc import BpLsdDecoder

    m = _matrices(dem)
    decoder = BpLsdDecoder(
        m.check_matrix, error_channel=list(m.priors), max_iter=BP_MAX_ITER,
        bp_method="minimum_sum", lsd_method="lsd_0", lsd_order=0,
    )
    return MatrixCompiled(decoder, m.observables_matrix)


@dataclass
class BatchCompiled(Compiled):
    decoder: object

    def decode(self, dets: np.ndarray) -> np.ndarray:
        return np.asarray(self.decoder.decode_batch(dets.astype(np.uint8))).astype(bool)


def build_stimbposd(dem: stim.DetectorErrorModel) -> Compiled:
    from stimbposd import BPOSD

    # Défauts de l'auteur : osd_cs d'ordre 60 ; même garde-fou que ldpc.
    k = osd_dimension(_matrices(dem).check_matrix)
    if 60 >= k:
        raise ValueError(f"ordre OSD 60 >= k = {k} : écriture hors limites (ldpc #105), refusé")
    return BatchCompiled(BPOSD(dem))


def build_beliefmatching(dem: stim.DetectorErrorModel) -> Compiled:
    from beliefmatching import BeliefMatching

    return BatchCompiled(BeliefMatching(dem))


def _builtin(name: str) -> Callable[[stim.DetectorErrorModel], Compiled]:
    def build(dem: stim.DetectorErrorModel) -> Compiled:
        from sinter._decoding._decoding_all_built_in_decoders import BUILT_IN_DECODERS

        return _sinter(BUILT_IN_DECODERS[name])(dem)
    return build


def build_relay(dem: stim.DetectorErrorModel) -> Compiled:
    from relay_bp.stim.sinter.decoders import SinterDecoder_RelayBP

    decoder = SinterDecoder_RelayBP(
        gamma0=0.1, pre_iter=80, num_sets=60, set_max_iter=60,
        gamma_dist_interval=(-0.24, 0.66), stop_nconv=3,
    )
    return _sinter(decoder)(dem)


def build_tesseract(dem: stim.DetectorErrorModel) -> Compiled:
    from tesseract_decoder import make_tesseract_sinter_decoders_dict

    return _sinter(make_tesseract_sinter_decoders_dict()["tesseract"])(dem)


REGISTRY: dict[str, Callable[[stim.DetectorErrorModel], Compiled]] = {
    "pymatching": _builtin("pymatching"),
    "fusion-blossom": _builtin("fusion_blossom"),
    "mwpf": _builtin("mw_parity_factor"),
    "bposd": build_bposd,
    "bplsd": build_bplsd,
    "stimbposd": build_stimbposd,
    "beliefmatching": build_beliefmatching,
    "relay-bp": build_relay,
    "tesseract": build_tesseract,
}

FAST = ("pymatching", "fusion-blossom", "beliefmatching", "bplsd", "bposd")


def build(name: str, dem: stim.DetectorErrorModel) -> Compiled:
    if name not in REGISTRY:
        raise ValueError(f"décodeur inconnu {name!r}, connus : {sorted(REGISTRY)}")
    return REGISTRY[name](dem)
