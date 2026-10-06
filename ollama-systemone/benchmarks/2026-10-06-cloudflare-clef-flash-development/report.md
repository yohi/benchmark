# Cloudflare Clef-Flash development benchmark

## Result

**ADVANCE TO FRESH VALIDATION**

Cloudflare-hosted Clef-Flash produced a perfect raw routing result on the already-consumed 350-case development set and passed the single-policy 1% accepted-risk development gate at threshold 0.50.

## Repository validation

```text
Ran 84 tests in 0.085s
OK
```

The hosted-provider adapter, environment expansion, response-envelope handling, usage aggregation, and all pre-existing benchmark tests pass.

## Benchmark

Run ID:

```text
20261006-154141
```

Dataset:

```text
datasets/engineering-routing-single-policy-risk-fresh.jsonl
```

This dataset is development evidence for Clef-Flash because it had already been consumed earlier in the benchmark chain.

## Raw quality

```text
350 / 350 correct
raw accuracy = 100%
raw errors = 0
```

Every routing class was 50/50 correct.

## Latency

Client-observed end-to-end latency:

```text
mean = 236.971ms
p50  = 187.732ms
p90  = 359.081ms
p95  = 524.920ms
p99  = 881.126ms
```

This includes network/API overhead and is the relevant latency for the actual hosted routing path.

## Usage

Measured requests:

```text
350
```

Returned usage:

```text
input_tokens = 151,404
output_tokens = 0
```

## Selective-confidence analysis

```text
accuracy = 1.0000
mean confidence = 0.8160
ECE = 0.1840
Brier = 0.0426
AURC = 0
errors = 0
error AUROC = n/a
```

Because there were no errors, confidence-based error ranking cannot be evaluated on this development run.

Absolute confidence is underconfident relative to the observed 100% accuracy, but calibration is secondary here because the raw classifier made no mistakes.

## Frozen threshold candidate

Single-policy risk control was run with exactly one threshold:

```text
threshold = 0.50
candidate count = 1
max accepted risk = 1%
confidence = 95%
```

Canonical result:

```text
coverage = 99.43%
accepted = 348 / 350
accepted errors = 0
empirical risk = 0
95% one-sided exact upper risk bound = 0.86%
```

Therefore:

```text
0.86% <= 1.00%
development PASS
```

## Decision

Freeze the next candidate before observing a new holdout:

```text
provider = cloudflare-clef-flash
model = clef-flash
threshold = 0.50
max accepted risk = 1%
confidence = 95%
candidate count = 1
```

Do not retune this threshold after seeing the next fresh holdout.

## Next step

Create a new untouched 350-case holdout with:

- 50 cases per routing class
- 25 engineering scenario families
- no exact task overlap with prior routing datasets
- no scenario-family overlap with the prior Nimble or Strands 350-case holdouts
- Clef-Flash policy metadata frozen before measurement

Then run Clef-Flash exactly once at threshold 0.50 and evaluate the same single-policy 1% risk gate.
