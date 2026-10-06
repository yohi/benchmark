# Strands threshold development after failed fresh validation

## Status

The previous fresh validation for:

```text
provider = strands-decider-2b-v21
checkpoint = StrandsAgents/strands-decider-2B-hobson-v21
threshold = 0.50
max accepted risk = 1%
confidence = 95%
```

failed on `engineering-routing-strands-risk-fresh.jsonl`.

Therefore that dataset is no longer fresh validation evidence for any revised Strands policy. It may now be used as **development evidence**.

## Objective

Perform exactly one threshold-development sweep:

```text
0.50 .. 0.99 step 0.01
```

The goal is not to manufacture a passing result.

The goal is to determine whether Strands still has a practically useful operating point that:

1. satisfies the existing 1% accepted-risk target at 95% confidence on development evidence, and
2. retains enough local coverage to justify another untouched fresh holdout.

## Command

Use the already-generated fresh-run details as development input:

```bash
uv run systemone-risk-control \
  --details results/20261006-145352-provider-details.jsonl \
  --model strands-decider-2b-v21 \
  --thresholds 0.50:0.99:0.01 \
  --max-risk 0.01 \
  --confidence-level 0.95 \
  --output results/20261006-145352-strands-threshold-development.json
```

## Decision rule

Advance Strands only if the selected feasible threshold has:

```text
upper accepted-risk bound <= 1%
accepted errors = 0 or otherwise still statistically feasible
coverage >= 85%
```

Why 85%:

- Nimble validated coverage is ~99.7%
- Strands exists to trade a modest amount of coverage for ~4.3x lower latency
- if Strands must escalate more than ~15% of requests, the operational benefit is likely too small to justify another validation cycle

This 85% cutoff is a development decision criterion, not a statistical guarantee.

## Outcomes

### A. Feasible and coverage >= 85%

Freeze:

- checkpoint
- selected threshold
- max risk 1%
- confidence 95%
- candidate count 1

Then create a new untouched 350-case holdout and validate exactly once.

### B. Feasible but coverage < 85%

Stop Strands investigation.

The model is fast but requires too much escalation to be a compelling replacement for Nimble.

### C. No feasible threshold

Stop Strands investigation.

Move to the hosted fast-decision path, starting with Cloudflare Clef-Flash.

## Guardrail

Do not change the 1% risk target.

Do not call the threshold-development result validation evidence.

Any revised Strands policy requires a new untouched holdout.


## Completed result

The development sweep is complete.

Key boundary:

```text
threshold 0.68:
  coverage 85.43%
  accepted 299
  errors 1
  single-policy 95% upper risk ≈ 1.577%

threshold 0.73:
  first zero-error threshold
  coverage 80.00%
  accepted 280
  single-policy 95% upper risk ≈ 1.064%
```

Therefore no observed threshold satisfies both:

```text
coverage >= 85%
single-policy 95% upper risk <= 1%
```

Decision:

```text
STOP Strands
Do not create another Strands fresh holdout
Move to hosted Clef-Flash evaluation
```

Durable evidence:

- `benchmarks/2026-10-06-strands-threshold-development/`
