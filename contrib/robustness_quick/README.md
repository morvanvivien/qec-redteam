# Quick robustness checks for stim-based decoders

`test_robustness_quick.py` is the fast part (E1 and E2) of the QEC robustness profile v0.1 (`../../docs/profil-robustesse-v0.1.md`), written to be dropped into a decoder library's own test suite: stim, numpy and the decoder only, fixed seed, under a second for PyMatching.

`check_all_decoders.py` runs it on the nine decoders of this bench. Result on 30 September 2026 (`../../docs/brique-2/robustness_quick_9_decodeurs.txt`): ten configurations pass both checks (the nine of the bench but relay-bp, plus sinter's `pymatching-correlated` and `hypergraph_union_find`); relay-bp 0.2.2 fails both with `TypeError` (trmue/relay#43).

    python -m pytest -q test_robustness_quick.py
    PYTHONPATH=../.. python check_all_decoders.py
