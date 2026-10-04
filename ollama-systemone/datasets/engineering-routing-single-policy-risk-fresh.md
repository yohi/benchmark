# Single-policy 1% risk fresh holdout

## Purpose

This dataset is a new untouched validation set for one policy frozen before measurement:

```text
model = nimble
confidence threshold = 0.80
maximum accepted risk = 1%
confidence level = 95%
candidate policies = 1
```

Unlike the previous development-time threshold search, this validation run does **not** search a threshold grid.

The purpose is to answer one question:

> Does the predeclared threshold 0.80 satisfy the 1% accepted-risk requirement on new evidence?

## Why 350 cases

For a single predeclared policy, there is no multiple-testing penalty across threshold candidates.

At 95% confidence, a one-sided exact binomial upper bound below 1% requires at least **299 accepted decisions when zero accepted errors are observed**.

The previous development pool accepted 88.29% of decisions at threshold 0.80.

A 350-case holdout therefore provides enough capacity to exceed 299 accepted decisions if fresh coverage remains at least about 85.4%.

This is a sample-size design constraint, not a promise that the policy will pass.

## Dataset design

`engineering-routing-single-policy-risk-fresh.jsonl` contains **350 cases**:

| Label | Cases |
| --- | ---: |
| implementation | 50 |
| debug | 50 |
| review | 50 |
| research | 50 |
| planning | 50 |
| documentation | 50 |
| deterministic | 50 |
| **total** | **350** |

The dataset uses 25 engineering scenario families. Each family contributes two variants for every routing label.

Examples of scenario families include:

- coding-agent context isolation
- retry/convergence control
- checkpoint/replay safety
- MCP schema compatibility
- OpenTelemetry agent tracing
- Git worktree isolation
- Django idempotency
- DRF query performance
- Python TaskGroup error handling
- Pydantic migration
- PostgreSQL locks
- Redis leases
- AWS Lambda latency
- Step Functions retry behavior
- ECS/ALB latency
- Cloudflare Worker CPU budget
- GitHub Actions matrix handling
- Bitbucket cache behavior
- Nexus index snapshots
- Justice artifact provenance
- OCTG provider routing
- benchmark confidence analysis
- uv entrypoint behavior
- Pyright monorepo resolution
- API schema compatibility

The paired-action structure intentionally keeps technical context similar while changing the requested primary action. This stresses routing boundaries without copying prior task text.

## Frozen policy metadata

Every row records:

```json
{
  "model": "nimble",
  "threshold": 0.80,
  "max_accepted_risk": 0.01,
  "confidence_level": 0.95,
  "candidate_count": 1,
  "multiple_testing_correction": "none-single-predeclared-policy"
}
```

Do not change these values after seeing model output and continue to call this dataset fresh validation evidence.

## Evaluation protocol

### 1. Generate fresh Nimble decisions

```bash
uv run systemone-bench \
  --models nimble \
  --dataset datasets/engineering-routing-single-policy-risk-fresh.jsonl \
  --warmup 1 \
  --iterations 1 \
  --cache-reset unload \
  --thresholds 0.80
```

### 2. Evaluate exactly one predeclared policy

```bash
uv run systemone-risk-control \
  --details results/<RUN_ID>-details.jsonl \
  --model nimble \
  --thresholds 0.80 \
  --max-risk 0.01 \
  --confidence-level 0.95 \
  --output results/<RUN_ID>-single-policy-risk.json
```

Because the threshold grid contains exactly one value, the candidate count is one. The pointwise alpha equals the family alpha and there is no threshold-search multiple-testing penalty.

## Pass / fail

Primary statistical gate:

```text
one-sided exact upper accepted-risk bound <= 1%
```

A zero-error result still requires at least 299 accepted decisions.

Therefore:

- **PASS**: upper risk bound <= 1%
- **FAIL — accepted risk**: bound > 1% because accepted errors are observed or risk remains too high
- **INCONCLUSIVE — sample size**: zero accepted errors but too few accepted decisions to place the upper bound at or below 1%

Coverage is secondary. Do not loosen the 1% target to improve coverage after observing this holdout.

## Methodology

This is a single-policy validation experiment, not another policy-development search.

If threshold 0.80 fails:

- preserve the failure as validation evidence
- do not retune on this dataset and call it fresh again
- move the dataset into development evidence only if a later policy explicitly uses it

If threshold 0.80 passes:

- this is stronger evidence than the previous development analysis
- it is still not a guarantee against future production distribution shift
- production monitoring and further independent evidence remain appropriate
