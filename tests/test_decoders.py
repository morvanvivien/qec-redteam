"""Chaque décodeur du registre décode un petit code de surface mieux que le hasard."""

import numpy as np
import pytest

from redteam.circuits import rotated_memory_si1000
from redteam.decoders import REGISTRY, build, build_bposd, dem_for, osd_dimension, _matrices


@pytest.fixture(scope="module")
def samples():
    circuit = rotated_memory_si1000(distance=3, rounds=3, p=0.002)
    dets, obs = circuit.compile_detector_sampler(seed=7).sample(300, separate_observables=True)
    return dem_for(circuit), dets, obs


# relay-bp et tesseract-decoder n'ont pas de roue Windows : absents, leurs tests sont sautés, pas échoués.
MODULES = {"relay-bp": "relay_bp", "tesseract": "tesseract_decoder"}


@pytest.mark.parametrize("name", sorted(REGISTRY))
def test_le_decodeur_rend_des_predictions_de_bonne_forme_et_utiles(name, samples):
    if name in MODULES:
        pytest.importorskip(MODULES[name])
    dem, dets, obs = samples
    predictions = build(name, dem).decode(dets)
    assert predictions.shape == obs.shape
    assert predictions.dtype == bool
    errors = np.any(predictions != obs, axis=1).sum()
    trivial = np.any(obs, axis=1).sum()
    assert errors < trivial


def test_un_syndrome_nul_donne_une_prediction_nulle(samples):
    dem, dets, _ = samples
    zero = np.zeros((1, dets.shape[1]), dtype=bool)
    for name in ("pymatching", "bposd", "bplsd"):
        assert not build(name, dem).decode(zero).any()


def test_le_garde_fou_ldpc_105_refuse_un_ordre_trop_grand(samples):
    dem = samples[0]
    k = osd_dimension(_matrices(dem).check_matrix)
    assert k > 10
    with pytest.raises(ValueError, match="ldpc #105"):
        build_bposd(dem, order=k)


def test_un_nom_inconnu_est_refuse(samples):
    with pytest.raises(ValueError):
        build("inconnu", samples[0])
