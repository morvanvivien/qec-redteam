"""Minimal reproduction: relay-bp's min-sum core decodes an empty syndrome into a wrong correction
when some error priors are exactly 1/2.

A prior of 1/2 gives a log prior ratio of exactly 0. The hard decision in
`crates/relay_bp/src/bp/min_sum.rs` is `posterior <= 0`, so a zero posterior is
decided as "error". With three such columns on one check, the empty syndrome is
decoded as [1, 1, 1], which does not even satisfy the syndrome; the decoder
reports failure after running every relay set.

Second part, a regression check for the proposed fix (`posterior < 0`): random
sparse check matrices, random syndromes, priors strictly inside (0, 1/2),
decodings printed as a digest so that two builds can be compared.

Only numpy, scipy and relay-bp are used.
"""

import hashlib

import numpy as np
import relay_bp
from scipy.sparse import csr_matrix

RELAY = dict(gamma0=0.1, pre_iter=80, num_sets=60, set_max_iter=60, gamma_dist_interval=(-0.24, 0.66), stop_nconv=3)


def minimal() -> None:
    check = csr_matrix(np.array([[1, 1, 1]], dtype=np.uint8))
    for priors in ([0.5, 0.5, 0.5], [0.49999, 0.49999, 0.49999], [0.5, 0.5, 0.01]):
        for name, cls, kwargs in (("MinSumBPDecoderF32", relay_bp.MinSumBPDecoderF32, {"max_iter": 20}), ("RelayDecoderF32", relay_bp.RelayDecoderF32, RELAY)):
            result = cls(check, error_priors=np.array(priors), **kwargs).decode_detailed(np.zeros(1, dtype=np.uint8))
            decoding = np.asarray(result.decoding)
            print(f"{name:19s} priors {priors}: empty syndrome -> {decoding.tolist()}, syndrome of it {((check @ decoding) % 2).tolist()}, success {result.success}, iterations {result.iterations}")


def regression(trials: int = 300, seed: int = 0) -> str:
    rng = np.random.default_rng(seed)
    digest = hashlib.sha256()
    for _ in range(trials):
        rows, cols = rng.integers(4, 12), rng.integers(8, 24)
        check = (rng.random((rows, cols)) < 0.25).astype(np.uint8)
        check[rng.integers(rows), :] |= 0  # keep shape
        priors = rng.uniform(1e-4, 0.45, cols)
        syndrome = (check @ (rng.random(cols) < priors).astype(np.uint8)) % 2
        decoder = relay_bp.RelayDecoderF32(csr_matrix(check), error_priors=priors, **RELAY)
        digest.update(np.asarray(decoder.decode(syndrome.astype(np.uint8)), dtype=np.uint8).tobytes())
    return digest.hexdigest()


if __name__ == "__main__":
    minimal()
    print(f"regression digest (300 random problems, priors in (0, 0.45)): {regression()}")
