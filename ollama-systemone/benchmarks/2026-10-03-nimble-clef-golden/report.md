# Nimble vs Clef Flash engineering-routing golden benchmark — 2026-10-03

## Purpose

Compare stronger local System One candidates against the Tev1 baseline on the same 50-case engineering-routing golden set.

## Result

| Model | Raw accuracy | Mean latency | p95 latency | Coverage @ 0.70 | Accepted accuracy @ 0.70 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Nimble | **98%** | 19.985 s | 21.457 s | **94%** | **100%** |
| Clef Flash | 96% | 21.003 s | 21.216 s | 54% | 100% |

Nimble made one raw error:

- `semantic-28-debug`, confidence 0.442549

Clef Flash made two raw errors:

- `semantic-06-implementation`, confidence 0.414685
- `semantic-45-deterministic`, confidence 0.538367

## Interpretation

Nimble substantially increased safe local coverage while staying in roughly the same latency class as Clef Flash.

At threshold 0.70, Nimble accepted 47/50 decisions with no accepted errors, whereas Clef Flash accepted only 27/50 with no accepted errors.

On this dataset, Clef Flash was therefore dominated by Nimble for the intended routing use case.

## Decision impact

Nimble became the primary strong-local candidate. The next question shifted from “which local model?” to “is Tev1 → Nimble cascading worth the additional complexity compared with Nimble alone?”

The 50-case set remained a development set; threshold selection still required a separate holdout.
