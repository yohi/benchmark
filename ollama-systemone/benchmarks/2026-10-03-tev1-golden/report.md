# Tev1 4B engineering-routing golden benchmark — 2026-10-03

## Purpose

Establish a reproducible local-routing baseline for Tev1 4B on the 50-case engineering-routing golden set after adding cache reset support.

## Result

- raw accuracy: **96% (48/50)**
- mean latency: **9.883 s**
- p95 latency: **10.046 s**
- throughput: **0.101 requests/s**

| Threshold | Local coverage | Accepted accuracy | Escalation |
| ---: | ---: | ---: | ---: |
| 0.70 | 50% | 100% | 50% |
| 0.75 | 38% | 100% | 62% |
| 0.80 | 26% | 100% | 74% |
| 0.85 | 20% | 100% | 80% |
| 0.90 | 14% | 100% | 86% |

The two raw errors had confidence 0.677913 and 0.550183, so both were rejected at threshold 0.70.

## Interpretation

Tev1 4B showed a useful low-latency local tier: at threshold 0.70 it accepted half of the golden set with no accepted errors in this sample.

This made Tev1 a plausible first-stage router, but the 50% escalation rate was still high enough to justify testing a stronger local model.

## Decision impact

This run became the fast-local baseline used in the later Tev1 → Nimble cascade analysis.

It should not be read as evidence that threshold 0.70 guarantees 100% accuracy outside this 50-case synthetic development set.
