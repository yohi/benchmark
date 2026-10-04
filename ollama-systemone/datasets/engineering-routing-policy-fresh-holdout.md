# Class-aware policy fresh holdout

## Purpose

This dataset is the fresh validation set for the class-aware Nimble routing policy selected after the previous 140-case production-derived set became development evidence.

The policy is frozen **before** this dataset is measured:

```text
default threshold = 0.60
predicted planning threshold = 0.80
```

The goal is not to search for a better threshold on this dataset. The goal is to test whether that already-selected policy generalizes.

## Dataset

`engineering-routing-policy-fresh-holdout.jsonl` contains 140 cases, balanced across all seven routing labels:

| Label | Cases |
| --- | ---: |
| implementation | 20 |
| debug | 20 |
| review | 20 |
| research | 20 |
| planning | 20 |
| documentation | 20 |
| deterministic | 20 |
| **total** | **140** |

Unlike the previous workload-shaped production-derived set, this holdout is intentionally balanced so one weak class cannot be hidden by class frequency.

## Freshness

The tasks are abstracted from distinct real engineering request patterns and have zero exact task-text overlap with:

- the 50-case golden/development set
- the 210-case validation set
- the 125-case implementation-boundary adversarial set
- the 140-case production-derived development set

The set includes new request families such as:

- subagent context isolation and fix-loop convergence
- checkpoint/replay safety
- agent observability and OpenTelemetry
- MCP schema/versioning
- idempotency and ORM query performance
- Python concurrency and compatibility migration
- CI runner/cache behavior
- benchmark methodology and selective classification

## Evaluation protocol

First run the model benchmark without changing the policy:

```bash
uv run systemone-bench \
  --models nimble \
  --dataset datasets/engineering-routing-policy-fresh-holdout.jsonl \
  --warmup 1 \
  --iterations 1 \
  --cache-reset unload \
  --thresholds 0.60,0.80
```

Then evaluate the **single frozen class-aware policy**, not a search grid:

```bash
uv run systemone-policy \
  --details results/<RUN_ID>-details.jsonl \
  --model nimble \
  --default-threshold 0.60 \
  --label-grid planning=0.80 \
  --min-accepted-accuracy 1.0 \
  --output results/<RUN_ID>-fixed-policy.json
```

The `planning=0.80` label grid has exactly one value, so the analyzer evaluates one candidate policy.

## Pass/fail interpretation

Primary gate:

- accepted accuracy at the frozen class-aware policy

Secondary metrics:

- local coverage
- fallback rate
- per-predicted-label acceptance
- raw-error confidence
- confusion matrix

If the frozen policy accepts an incorrect decision, this holdout has falsified the candidate.

Do **not** change 0.60 or 0.80 after seeing this result and still describe the same dataset as fresh validation evidence. Any revised policy must be tested on another fresh set.
