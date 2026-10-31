"""La réécriture du bruit change les probabilités voulues et rien d'autre."""

import pytest
import stim

from redteam.circuits import rotated_memory_si1000
from redteam.perturb import add_crosstalk, bias, rescale, sites, spectator_pairs, two_qubit_layers


def circuit(basis="z"):
    return rotated_memory_si1000(distance=3, rounds=3, p=0.001, basis=basis)


def probabilities(c, name):
    return {round(i.gate_args_copy()[0], 12) for i in c.flattened() if i.name == name}


def test_la_regle_identite_redonne_le_circuit_aplati_au_caractere_pres():
    c = circuit()
    assert str(rescale(c, lambda site, p: p)) == str(c.flattened())


def test_les_sites_sont_classes_par_type_et_par_round():
    kinds = {(s.kind, s.round) for _, _, s in sites(circuit()) if s is not None}
    assert ("reset", 0) in kinds
    assert {("measure", r) for r in range(4)} <= kinds
    assert {("depol2", r) for r in range(3)} <= kinds
    assert not any(kind == "depol2" and r >= 3 for kind, r in kinds)


def test_un_facteur_sur_la_mesure_ne_touche_que_la_mesure():
    out = rescale(circuit(), lambda site, p: p * 6 if site.kind == "measure" else p)
    assert probabilities(out, "X_ERROR") == {0.002, 0.03}
    assert probabilities(out, "DEPOLARIZE2") == {0.001}
    assert out.num_detectors == circuit().num_detectors


def test_un_qubit_chaud_scinde_l_instruction_et_garde_les_autres_cibles():
    out = rescale(circuit(), lambda site, p: p * 10 if 10 in site.qubits and site.kind == "depol2" else p)
    assert probabilities(out, "DEPOLARIZE2") == {0.001, 0.01}
    hot = [i for i in out.flattened() if i.name == "DEPOLARIZE2" and abs(i.gate_args_copy()[0] - 0.01) < 1e-12]
    assert all(10 in [t.value for t in i.targets_copy()] for i in hot)


def test_les_probabilites_sont_plafonnees_au_melange_complet():
    out = rescale(circuit(), lambda site, p: 1.0)
    assert probabilities(out, "X_ERROR") == {0.5}
    assert probabilities(out, "DEPOLARIZE1") == {0.75}
    assert probabilities(out, "DEPOLARIZE2") == {0.9375}


def test_une_probabilite_negative_est_refusee():
    with pytest.raises(ValueError):
        rescale(circuit(), lambda site, p: -1.0)


def test_les_paires_spectatrices_relient_deux_portes_differentes_voisines():
    flat = circuit().flattened()
    _, pairs = two_qubit_layers(flat)[0]
    spectators = spectator_pairs(flat, pairs)
    owner = {q: i for i, pair in enumerate(pairs) for q in pair}
    assert spectators
    assert all(owner[a] != owner[b] for a, b in spectators)


def test_la_diaphonie_ajoute_des_erreurs_correlees_sans_changer_les_detecteurs():
    c = circuit()
    out = add_crosstalk(c, 0.001, "ZZ")
    assert out.num_detectors == c.num_detectors
    assert sum(1 for i in out.flattened() if i.name == "E") > 0
    assert str(add_crosstalk(c, 0.0)) == str(c.flattened())


def test_la_diaphonie_refuse_un_pauli_inconnu():
    with pytest.raises(ValueError):
        add_crosstalk(circuit(), 0.001, "YY")


def test_le_biais_garde_la_probabilite_totale_et_pousse_vers_z():
    out = bias(circuit("x"), 100.0)
    channels = [i for i in out.flattened() if i.name == "PAULI_CHANNEL_1"]
    px, py, pz = channels[0].gate_args_copy()
    assert px + py + pz == pytest.approx(0.0001)
    assert pz / (px + py) == pytest.approx(100.0)
    two = [i for i in out.flattened() if i.name == "PAULI_CHANNEL_2"][0].gate_args_copy()
    assert sum(two) == pytest.approx(0.001)
    out.detector_error_model(approximate_disjoint_errors=True)


def test_le_biais_neutre_redonne_le_meme_modele_d_erreurs():
    c = circuit("x")
    reference = c.flattened().detector_error_model(approximate_disjoint_errors=True)
    neutral = bias(c, 0.5).detector_error_model(approximate_disjoint_errors=True)
    assert neutral.num_errors == reference.num_errors
