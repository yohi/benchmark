# Tev1 → Nimble cascade analysis — 2026-10-04

## Purpose

Determine whether a two-stage local cascade improves safe local coverage enough to justify its latency and complexity compared with a single Nimble stage.

The analysis reused the two 50-case golden-set detail files and did not rerun Ollama.

## Result

| Configuration | Local coverage | Accepted accuracy | Avg local latency | p95 local latency | Local calls/request |
| --- | ---: | ---: | ---: | ---: | ---: |
| Tev1 → Nimble | 96% | 100% | **19.339 s** | 31.300 s | 1.48 |
| Nimble alone | 96% | 100% | 19.986 s | **21.457 s** | **1.00** |
| Tev1 alone | 52% | 100% | **9.883 s** | **10.046 s** | **1.00** |

Best observed cascade plateau:

- Tev1 threshold: 0.68
- Nimble threshold: 0.45..0.78
- local coverage: 96%
- fallback: 4%

Best observed Nimble-only plateau under the 100% accepted-accuracy constraint:

- threshold: 0.45..0.58
- local coverage: 96%
- fallback: 4%

## Interpretation

The cascade reduced mean local latency by only about 0.65 seconds compared with Nimble alone, while:

- increasing p95 latency from about 21.5 s to 31.3 s
- increasing average local model calls from 1.00 to 1.48
- providing no coverage improvement
- providing no fallback-rate improvement

Tev1 alone remained useful as a fast, lower-coverage option, but adding it ahead of Nimble did not materially improve the quality-preserving offload objective.

## Decision impact

Prefer **Nimble alone** over the Tev1 → Nimble cascade for the next validation stage.

This conclusion was based on the 50-case development set and therefore required holdout validation before selecting a deployment threshold. That follow-up is recorded in `../2026-10-04-nimble-validation/`.
