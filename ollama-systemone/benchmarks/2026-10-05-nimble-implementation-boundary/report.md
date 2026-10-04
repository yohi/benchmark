# Nimble implementation-boundary adversarial benchmark — 2026-10-05

## Purpose

Stress the current Nimble routing policy on implementation-adjacent tasks after the 210-case holdout exposed raw errors toward the `implementation` class.

This dataset intentionally uses implementation vocabulary in debug, planning, review, and research tasks, while also including real implementation requests.

The candidate policy was fixed before this run:

- model: `nimble`
- confidence threshold: **0.60**

## Run

- run ID: `20261005-033733`
- dataset: `datasets/engineering-routing-implementation-boundary.jsonl`
- cases: 125
- classes: implementation, debug, planning, review, research
- cases per class: 25
- warmup: 1
- iterations: 1
- cache reset: `unload`

```bash
uv run systemone-bench \
  --models nimble \
  --dataset datasets/engineering-routing-implementation-boundary.jsonl \
  --warmup 1 \
  --iterations 1 \
  --cache-reset unload \
  --thresholds 0.55,0.60,0.65,0.70
```

## Result

Raw accuracy: **98.4% (123/125)**.

| Threshold | Local coverage | Accepted accuracy | Escalation | Accepted |
| ---: | ---: | ---: | ---: | ---: |
| 0.55 | 94.4% | 100% | 5.6% | 118 |
| **0.60** | **92.0%** | **100%** | **8.0%** | **115** |
| 0.65 | 89.6% | 100% | 10.4% | 112 |
| 0.70 | 86.4% | 100% | 13.6% | 108 |

At the pre-selected threshold 0.60, all 115 locally accepted decisions were correct in this adversarial set.

## Raw errors

Two raw errors were observed:

| Case | Expected | Predicted | Confidence |
| --- | --- | --- | ---: |
| `boundary-018-debug` | debug | review | 0.541419 |
| `boundary-097-research` | research | review | 0.513124 |

Both are rejected by threshold 0.60.

Importantly, **no case was incorrectly routed to implementation**.

## Per-class result at threshold 0.60

| Expected class | Raw accuracy | Local coverage | Accepted accuracy |
| --- | ---: | ---: | ---: |
| implementation | 100% | 88% | 100% |
| debug | 96% | 92% | 100% |
| planning | 100% | 100% | 100% |
| review | 100% | 100% | 100% |
| research | 96% | 80% | 100% |

The intended implementation-boundary failure mode did not reproduce. The two observed errors instead moved toward `review`, and both had confidence below 0.55.

## Decision

**Keep Nimble threshold 0.60 as the current candidate policy.**

Threshold 0.55 also produced 100% accepted accuracy and higher local coverage in this run, but lowering the threshold based on this adversarial set would convert the fresh stress test into tuning evidence.

Therefore this run strengthens the existing 0.60 policy rather than justifying retuning it downward.

## Latency note

Observed latency:

- mean: 11.806 s
- p50: 10.556 s
- p95: 22.983 s
- p99: 23.219 s

The distribution is visibly non-uniform: some early requests are around 23 s while many later requests are around 10.5 s.

This run used `--cache-reset unload`, which resets before the model benchmark, not before every measured request. The benchmark therefore does **not** establish per-request cold latency, and this latency result should not be compared naively with the earlier 210-case validation run.

The quality result is the primary evidence from this run.

## Next step

The current evidence chain is now:

1. 50-case development set identified Nimble as the stronger local candidate.
2. 210-case holdout supported threshold 0.60.
3. 125-case implementation-boundary adversarial set preserved 100% accepted accuracy at threshold 0.60 and produced zero implementation-attractor errors.

Before production use, the strongest next validation would be a fresh, production-derived set with naturally noisy and multi-intent requests rather than another synthetic threshold-tuning set.
