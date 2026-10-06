# Cloudflare Clef-Flash single-policy 1% risk fresh validation

## Result

**PASS**

The predeclared Clef-Flash policy passed the fresh 1% accepted-risk validation gate.

## Frozen policy

The policy was fixed before observing this holdout:

```text
provider = cloudflare-clef-flash
model = clef-flash
endpoint model = @cf/cloudflare/clef-flash
threshold = 0.50
maximum accepted risk = 1%
confidence level = 95%
candidate count = 1
```

No threshold search was performed on this holdout.

## Repository validation

```text
Ran 88 tests in 0.194s
OK
```

The new holdout tests confirm:

- 350 balanced unique cases
- frozen policy metadata
- zero exact task overlap with prior routing datasets
- zero scenario-family overlap with the Nimble and Strands 350-case holdouts

## Fresh benchmark

Run ID:

```text
20261006-155459
```

Dataset:

```text
datasets/engineering-routing-clef-flash-risk-fresh.jsonl
```

Raw result:

```text
350 / 350 correct
raw accuracy = 100%
raw errors = 0
```

Every routing class was 50/50 correct.

## Latency

Client-observed end-to-end:

```text
mean = 289.348ms
p50  = 183.269ms
p90  = 512.616ms
p95  = 611.721ms
p99  = 1514.512ms
```

## Usage

Measured requests:

```text
350
```

Returned usage:

```text
input_tokens = 153,187
output_tokens = 0
```

## Canonical single-policy risk control

Exactly one candidate threshold was evaluated:

```text
threshold = 0.50
candidate count = 1
family alpha = 0.05
pointwise alpha = 0.05
zero-error sample requirement = 299 accepted decisions
```

Canonical result:

```text
coverage = 94.86%
accepted = 332 / 350
accepted errors = 0
empirical accepted risk = 0
one-sided exact 95% upper risk bound = 0.90%
```

Primary gate:

```text
0.90% <= 1.00%
PASS
```

## Interpretation

The provider benchmark summary carries a fixed `comparison_status = development-only` label, but that field does not describe the experiment design.

This run is fresh validation evidence because:

- the policy was frozen before this dataset was observed
- the dataset was newly constructed
- exact task overlap with prior routing sets was zero
- scenario-family overlap with the previous Nimble/Strands 350-case holdouts was zero
- only one threshold was evaluated

## Decision

Clef-Flash threshold 0.50 is now a **validated hosted decision-layer candidate for the current benchmark distribution**.

Current comparison:

```text
Nimble .80:
  validated local quality reference
  fresh coverage 99.71%
  accepted errors 0
  95% upper risk ~0.85%
  p50 ~15.2s

Clef-Flash .50:
  validated hosted decision-layer candidate
  fresh coverage 94.86%
  accepted errors 0
  95% upper risk 0.90%
  p50 183ms

Strands 2B:
  fresh validation failed
  stopped

Laya:
  routing quality rejected
```

## Scope of the claim

This validates the frozen policy against the benchmark distribution.

It is not proof against arbitrary production distribution shift. Production rollout should preserve:

- abstention/escalation at confidence <0.50
- telemetry for routing decisions and confidence
- a stronger fallback path
- periodic or incident-triggered re-evaluation if workload shape changes materially
