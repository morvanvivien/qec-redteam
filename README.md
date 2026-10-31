# qec-redteam

An independent red team for public quantum error correction decoders. It looks for realistic noise under which a decoder breaks, reports it to the maintainer with a script anyone can replay, and keeps a public record of what it found, what it got wrong and what held up.

No robustness standard for decoders exists yet, and this project does not claim to be one.

## Findings

| Registry | Target | What happens | Reported |
|---|---|---|---|
| QEC-2026-004 | relay-bp 0.2.2 (IBM), stim module | Edge probabilities are summed instead of combined; as soon as one qubit is saturated, every decode raises an exception | [trmue/relay#43](https://github.com/trmue/relay/issues/43), the author replied "I think you are correct" |
| QEC-2026-005 | relay-bp 0.2.2, Rust core | Priors of exactly 1/2 form a stopping set, so corrections violate the syndrome. On d = 5 leaks, logical error rate 12.84 %; a 20-line patch brings it to 1.24 % | same issue |
| QEC-2026-016 | relay-bp 0.2.2 on the gross code [[144,12,12]] | One leaked qubit: 74 errors in 150 shots and 150 convergence failures in 150. With capped priors: 0 errors in 150 | same issue |
| QEC-2026-015 | sinter (Stim), fusion-blossom adapter | Parallel edges are never merged: up to 3.4 times the logical error rate under biased noise, 6.3 times on the XZZX code | [quantumlib/Stim#1116](https://github.com/quantumlib/Stim/issues/1116) |
| QEC-2026-003 | ldpc 2.4.1, BP+OSD and BP+LSD | Out-of-bounds write in the OSD combination sweep whenever k < order; on BP+LSD this happens on ordinary decodes | [ldpc#105](https://github.com/quantumgizmos/ldpc/issues/105) (reported by a third party, cause and fix added here), [fix in ldpc#116](https://github.com/quantumgizmos/ldpc/pull/116) |
| QEC-2026-002 | decoder-bench | `--store_unique False` has no effect: `argparse` with `type=bool` | [decoder-bench#2](https://github.com/satvikmaurya/decoder-bench/issues/2) |
| QEC-2026-001 | decoder-bench | Published rates are per unique syndrome: 1.22 times the Monte Carlo rate at p = 0.001, 1.83 times at p = 0.0005. The author's thesis documents this as a deliberate choice | [decoder-bench#3](https://github.com/satvikmaurya/decoder-bench/issues/3) |

Findings that are not defects are recorded too. For example, nine decoders show no collapse under homogeneous mistuning, drift, a hot coupler or Z bias. An uncalibrated ZZ crosstalk at d = 5 reverses a ranking: tesseract goes from between 0.62 and 0.70 to between 1.29 and 1.53 times the errors of PyMatching, and mwpf from 0.76 to between 2.4 and 2.9 times. Once informed of the crosstalk they lead again, so this is a sensitivity to calibration, not a bug.

## What we got wrong

The [registry](docs/registre.md) lists 23 entries, including 5 false positives and 3 errors in our own method, on the same footing as the defects. That is what makes the rest checkable.

## Replay

```
python -m venv .venv
.venv/bin/python -m pip install -r requirements-decoders.txt
.venv/bin/python -m pytest -q
```

Each confirmed defect has a replay command in [docs/registre.json](docs/registre.json) (`rejeu` field), with its evidence files. The [replay workflow](.github/workflows/replay.yml) runs all of them on a clean machine. `relay-bp` and `tesseract-decoder` have no Windows wheel, so use Linux.

The detailed registry and reports are in French for now; [docs/utilisation.md](docs/utilisation.md) lists the other commands.

## How this works

- The maintainer hears first. Publication comes at least 30 days after the report.
- A finding is replayed from zero, with a fixed seed, before it is reported. Corrections go in the same thread.
- Where a project excludes AI-generated code, as Stim does, it gets measurements and a description, not a patch.

## AI assistance

The code, the analysis and the English in this repository and in the linked reports were written with AI assistance (Claude). Every figure comes from a committed script and results file, so it can be checked without trusting either the author or the tool.

## License

MIT, see [LICENSE](LICENSE). Files under `third_party/` keep their own licenses.
