Thanks for decoder-bench. Shared traces and a common noise model are very useful, and the PyMatching numbers were easy to reproduce.

I know that sampling only unique syndromes is a deliberate choice (the dissertation appendix explains it). This issue is about how the resulting number is labelled: `logical_error_rate` measured on a deduplicated trace is higher than the Monte Carlo logical error rate once p is low, and the README does not say so. If that is intended, a note in the README would already help.

### Setup

Rotated surface code, d=7, 7 rounds, memory Z, SI1000, PyMatching. Circuits rebuilt with your `noise.py`; they are byte-identical to the `circuit` field of the Zenodo traces. stim 1.16.0, pymatching 2.4.0.

### The traces hold one copy of each syndrome

Zenodo traces compared with a fresh sample of 1,000,000 shots of the same circuit:

| p | records in trace | all-zero syndromes in trace | unique syndromes in 1M fresh shots | all-zero syndromes in 1M fresh shots |
|---|---|---|---|---|
| 0.0009 | 856,892 | 1 | 857,383 | 26,207 |
| 0.001 | 898,240 | 1 | 897,615 | 17,293 |
| 0.003 | 999,993 | 1 | 999,994 | 6 |
| 0.005 | 1,000,000 | 0 | 1,000,000 | 0 |

### Effect on the logical error rate

Per shot. Published values are from `results/benchmark_results.csv` (5,000,000 records). z is a two-proportion z-score against the published value.

| p | published | fresh Monte Carlo | z | fresh shots, first 5M unique syndromes only | z |
|---|---|---|---|---|---|
| 0.005 | 0.0499594 | 0.0500146 (250,073 / 5,000,000) | +0.4 | 0.0500146 | +0.4 |
| 0.003 | 0.0079552 | 0.0079372 (47,623 / 6,000,000) | −0.3 | 0.0079448 | −0.2 |
| 0.001 | 1.264e-4 | 1.040e-4 (5,201 / 50,000,000) | −4.6 | 1.172e-4 | −1.3 |
| 0.0005 | 1.06e-5 | 0.578e-5 (289 / 50,000,000) | −4.1 | 1.38e-5 | +1.4 |

Where deduplication has no effect (p ≥ 0.003) plain Monte Carlo reproduces your numbers. Where it does, Monte Carlo is lower, and keeping only unique syndromes reproduces them. The published value is about 21% above Monte Carlo at p=0.001 (ratio 1.22 ± 0.05) and about 83% above at p=0.0005 (ratio 1.83 ± 0.27).

The reason is that a syndrome does not determine the observable: the same syndrome can come from errors in different logical classes. Frequent, easy syndromes are counted once instead of thousands of times, so the rare hard ones weigh more.

Decoding time shifts the same way. Mean syndrome weight is 9.08 in the trace against 8.36 in Monte Carlo at p=0.001, and PyMatching's time per shot on the 1M-shot Zenodo traces is 8% higher at p=0.001 and 11% higher at p=0.0009 than on fresh samples of the same size. No difference at p=0.003.

### Suggestions

Both keep unique-syndrome traces.

- Say in the README that traces are deduplicated and that `logical_error_rate` is a rate per unique syndrome, not comparable to Monte Carlo rates from the literature.
- Store two integer arrays next to each unique syndrome: how many times it was sampled, and how many of those had the observable flipped. The trace stays compact, every decoder still sees the same set of problems, and the exact Monte Carlo rate can be recovered by weighting.

### Reproduction

<details>
<summary>39-line script, about 4 minutes on one core</summary>

```python
# Run from the decoder-bench repository root. Needs stim, pymatching, numpy.
import numpy as np
import pymatching
import stim

from decoder_bench.common.noise import NoiseModel


def measure(p, d=7, target_unique=5_000_000):
    noiseless = stim.Circuit.generated("surface_code:rotated_memory_z", rounds=d, distance=d)
    circuit = NoiseModel.SI1000(p).noisy_circuit(noiseless)
    matcher = pymatching.Matching.from_stim_circuit(circuit)

    seen = set()
    shots = errors = unique = unique_errors = 0
    iteration = 0
    while unique < target_unique:
        sampler = circuit.compile_detector_sampler(seed=iteration + 42)
        dets, obs = sampler.sample(shots=1_000_000, separate_observables=True, bit_packed=True)
        predictions = matcher.decode_batch(dets, bit_packed_shots=True, bit_packed_predictions=True)
        failed = np.any(predictions != obs, axis=1)

        shots += len(dets)
        errors += int(failed.sum())
        for row, row_failed in zip(dets, failed):
            key = row.tobytes()
            if key in seen or unique == target_unique:
                continue
            seen.add(key)
            unique += 1
            unique_errors += int(row_failed)
        iteration += 1

    print(f"p={p}: Monte Carlo {errors}/{shots} = {errors / shots:.4g}, "
          f"unique syndromes only {unique_errors}/{unique} = {unique_errors / unique:.4g}")


for p in (0.005, 0.003, 0.001, 0.0005):
    measure(p)
```

Output on my machine:

```
p=0.005: Monte Carlo 250073/5000000 = 0.05001, unique syndromes only 250073/5000000 = 0.05001
p=0.003: Monte Carlo 47623/6000000 = 0.007937, unique syndromes only 39724/5000000 = 0.007945
p=0.001: Monte Carlo 598/6000000 = 9.967e-05, unique syndromes only 586/5000000 = 0.0001172
p=0.0005: Monte Carlo 71/12000000 = 5.917e-06, unique syndromes only 69/5000000 = 1.38e-05
```

</details>

The script measures both rates on the same shots. In the table, the Monte Carlo rows at p=0.001 and p=0.0005 come from a larger run of the same circuits (50M shots each, `sinter.collect` with the `pymatching` decoder) to tighten the error bars. Related: #2 (the `--store_unique` flag).
