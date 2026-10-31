"""relay-bp's CheckMatrices with the two fixes we propose, for measurement only.

1. Edge priors combine independent mechanisms: p = (1 - prod(1 - 2 p_i)) / 2,
   instead of the sum p_1 + p_2 + ...
2. The decided-error biases are plain 1-D ndarrays (np.asarray(...).ravel()),
   and the observables bias uses the observables matrix (as on main).

The installed package is not modified: `patch()` swaps the class used by
SinterDecoder_RelayBP inside this process only.
"""

import numpy as np
import relay_bp.stim.sinter.decoders as decoders
from relay_bp.stim.sinter.check_matrices import CheckMatrices


def combine(hyperedge_to_edge, priors: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore"):
        log_bias = np.log(np.clip(1.0 - 2.0 * priors, 0.0, None))
    total = hyperedge_to_edge @ log_bias
    return (1.0 - np.exp(total)) / 2.0


def prune_as_ndarray(matrices: CheckMatrices, threshold: float) -> CheckMatrices:
    """The published pruning, with 1-D ndarray biases and the observables matrix for the observables bias."""
    to_one = np.argwhere(matrices.error_priors >= 1.0 - threshold).reshape(-1)
    pruned = CheckMatrices.prune_decided_errors(matrices, threshold)
    if len(to_one):
        pruned.syndrome_bias = np.asarray(matrices.check_matrix[:, to_one].sum(axis=1)).ravel().astype(np.uint8) % 2
        pruned.observables_bias = np.asarray(matrices.observables_matrix[:, to_one].sum(axis=1)).ravel().astype(np.uint8) % 2
    return pruned


class CombinedCheckMatrices(CheckMatrices):
    @classmethod
    def from_dem(cls, dem, decomposed_hyperedges=None, prune_decided_errors=True, threshold=0.0):
        m = super().from_dem(dem, decomposed_hyperedges, prune_decided_errors=False, threshold=threshold)
        from beliefmatching import detector_error_model_to_check_matrices

        raw = detector_error_model_to_check_matrices(dem, allow_undecomposed_hyperedges=True)
        if m.check_matrix.shape == raw.edge_check_matrix.shape and (m.check_matrix != raw.edge_check_matrix).nnz == 0:
            m = cls(check_matrix=m.check_matrix, observables_matrix=m.observables_matrix,
                    error_priors=combine(raw.hyperedge_to_edge_matrix, raw.priors).astype(np.float64))
        else:
            m = cls(check_matrix=m.check_matrix, observables_matrix=m.observables_matrix, error_priors=m.error_priors)
        return m.prune_decided_errors(threshold) if prune_decided_errors else m

    def prune_decided_errors(self, threshold: float = 0.0):
        return prune_as_ndarray(self, threshold)


def patch() -> None:
    decoders.CheckMatrices = CombinedCheckMatrices


class CrashFixOnlyCheckMatrices(CheckMatrices):
    """Summed priors kept as published; only the ndarray and observables-matrix fixes."""

    def prune_decided_errors(self, threshold: float = 0.0):
        return prune_as_ndarray(self, threshold)


def patch_crash_fix_only() -> None:
    decoders.CheckMatrices = CrashFixOnlyCheckMatrices


HALF_CAP = 0.5 - 1e-5


class ClampedCheckMatrices(CombinedCheckMatrices):
    """Combined priors, then clamped just below 1/2.

    Min-sum only propagates signs and minimum magnitudes: a prior of exactly 1/2
    (log ratio 0) carries no sign and silences every check it touches, whereas
    1/2 - 1e-5 keeps a sign and decodes normally. Clamping removes that
    discontinuity; for priors already below the cap it changes nothing.
    """

    @classmethod
    def from_dem(cls, dem, decomposed_hyperedges=None, prune_decided_errors=True, threshold=0.0):
        m = super().from_dem(dem, decomposed_hyperedges, prune_decided_errors=False, threshold=threshold)
        m = cls(check_matrix=m.check_matrix, observables_matrix=m.observables_matrix, error_priors=np.minimum(m.error_priors, HALF_CAP))
        return m.prune_decided_errors(threshold) if prune_decided_errors else m


def patch_clamped() -> None:
    decoders.CheckMatrices = ClampedCheckMatrices
