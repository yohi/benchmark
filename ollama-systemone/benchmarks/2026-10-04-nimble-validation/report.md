# Nimble engineering-routing validation — 2026-10-04

## Purpose

Validate whether the Nimble confidence threshold observed on the 50-case development/golden set generalizes to a separate 210-case holdout set.

This run is a **validation record**, not a tuning set. The threshold candidates were selected before this run from the smaller development set.

## Run

- run ID: `20261004-012101`
- model: `nimble`
- dataset: `datasets/engineering-routing-validation.jsonl`
- cases: 210
- split: 30 cases each for implementation, review, research, debug, planning, documentation, deterministic
- warmup: 1 synthetic request
- iterations: 1
- cache reset: `unload`

```bash
uv run systemone-bench \
  --models nimble \
  --dataset datasets/engineering-routing-validation.jsonl \
  --warmup 1 \
  --iterations 1 \
  --cache-reset unload \
  --thresholds 0.40,0.45,0.50,0.55,0.58,0.60,0.65,0.70
```

## Environment

- platform: Linux 7.0.0-34-generic x86_64, glibc 2.43
- Python: 3.14.7
- logical CPUs: 24
- physical CPUs: 24
- memory: 60.81 GiB

## Result

Raw classification accuracy was **99.05% (208/210)**.

| Threshold | Local coverage | Accepted accuracy | Escalation | Accepted |
| ---: | ---: | ---: | ---: | ---: |
| 0.40 | 99.52% | 99.52% | 0.48% | 209 |
| 0.45 | 99.52% | 99.52% | 0.48% | 209 |
| 0.50 | 98.57% | 99.52% | 1.43% | 207 |
| **0.55** | **98.10%** | **100%** | **1.90%** | **206** |
| 0.58 | 98.10% | 100% | 1.90% | 206 |
| **0.60** | **97.62%** | **100%** | **2.38%** | **205** |
| 0.65 | 97.14% | 100% | 2.86% | 204 |
| 0.70 | 96.19% | 100% | 3.81% | 202 |

Latency:

- mean: 20.750 s
- p50: 21.199 s
- p95: 21.465 s
- p99: 21.623 s
- throughput: 0.048 requests/s

## Errors

Two raw errors were observed:

| Case | Expected | Predicted | Confidence |
| --- | --- | --- | ---: |
| `validation-098-debug` | debug | implementation | 0.542108 |
| `validation-140-planning` | planning | implementation | 0.277578 |

Both errors are rejected by a threshold of 0.55 or higher.

The observed confusion pattern is therefore concentrated on **debug → implementation** and **planning → implementation** boundaries.

## Per-class quality

Raw accuracy:

- implementation: 30/30
- review: 30/30
- research: 30/30
- debug: 29/30
- planning: 29/30
- documentation: 30/30
- deterministic: 30/30

At threshold 0.60, every locally accepted decision was correct in this holdout. Coverage remained high across all classes; the rejected cases were concentrated around lower-confidence review/research/debug/planning examples.

## Decision

**Current deployment candidate: Nimble with confidence threshold 0.60.**

Rationale:

1. The 50-case development set suggested a safe threshold plateau near 0.45–0.58.
2. The separate 210-case holdout reproduced the confidence-gating behavior.
3. Threshold 0.55 is the lowest tested threshold with zero accepted errors on the holdout.
4. Threshold 0.60 gives a small additional margin above the highest observed error confidence (0.542108) while sacrificing only one additional local acceptance compared with 0.55.
5. Nimble alone provides 97.62% local coverage at this threshold, so the earlier Tev1 → Nimble cascade is not currently justified by coverage.

This does **not** establish a universal 100% accuracy guarantee. It records that no accepted errors were observed in this 210-case synthetic holdout at threshold 0.60.

## Next validation target

Build a separate adversarial boundary set focused on cases that can plausibly be confused with implementation work, especially:

- debug vs implementation
- planning vs implementation
- review vs implementation
- research vs implementation

Do not tune against this holdout repeatedly; once it influences further threshold changes, treat it as development evidence and validate the revised policy on another fresh split.

## Artifacts

- `manifest.json`: run configuration/environment and links to local raw artifacts
- `metrics.json`: compact machine-readable metrics used in this report
- local raw summary: `results/20261004-012101-summary.json` (gitignored)
- local raw details: `results/20261004-012101-details.jsonl` (gitignored)
