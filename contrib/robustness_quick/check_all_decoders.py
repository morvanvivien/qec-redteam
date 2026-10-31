"""Runs the two quick checks on the nine decoders of the qec-redteam bench, to show what they catch.

    PYTHONPATH=../.. python check_all_decoders.py
"""

import test_robustness_quick as quick

from redteam.decoders import REGISTRY, build


def adapter(name):
    def make(dem):
        compiled = build(name, dem)
        return compiled.decode
    return make


for name in sorted(REGISTRY):
    quick.DECODERS[name] = adapter(name)
    results = []
    for check in (quick.test_e1_holds_up_on_a_randomized_ancilla, quick.test_e2_true_model_does_not_hurt):
        try:
            check(name)
            results.append("pass")
        except Exception as error:
            results.append(f"FAIL ({type(error).__name__}: {str(error)[:90]})")
    print(f"{name:15s} E1 {results[0]:60s} E2 {results[1]}", flush=True)
