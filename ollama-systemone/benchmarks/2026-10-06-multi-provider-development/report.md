# Multi-provider decision-model development comparison — 2026-10-06

## Purpose

Evaluate whether a smaller local decision model can replace Nimble for engineering routing while preserving quality and materially reducing CPU latency.

This comparison uses the already-consumed 350-case routing set as **development evidence**. It is not a fresh validation for a newly selected provider policy.

## Validation

Repository test suite:

```text
Ran 77 tests in 0.050s
OK
```

## Laya multilingual

Run ID:

```text
20261006-141753
```

Latency:

```text
mean 371ms
p50  359ms
p95  499ms
p99  644ms
```

Raw routing accuracy:

```text
41.14%
```

Per-class accuracy exposed severe failures:

```text
implementation   6%
review           0%
deterministic   26%
documentation   46%
planning        56%
debug           74%
research        80%
```

Confidence filtering does not recover a quality-preserving operating point.

At threshold 0.70:

```text
coverage = 8.57%
accepted accuracy = 73.33%
```

At threshold 0.90:

```text
coverage = 3.43%
accepted accuracy = 58.33%
```

### Decision

Reject Laya multilingual for this routing task.

Its CPU latency is excellent, but routing quality and confidence ranking are insufficient.

## Strands Decider 2B v21

Run ID:

```text
20261006-142040
```

Latency:

```text
mean 3.59s
p50  3.51s
p95  4.27s
p99  4.98s
```

Raw routing accuracy:

```text
349 / 350 = 99.714%
```

The only raw error was:

```text
debug -> implementation
```

Every other routing class was 50/50 correct.

Threshold behavior:

| threshold | coverage | accepted accuracy | accepted |
| ---: | ---: | ---: | ---: |
| 0.50 | 98.29% | 100% | 344 |
| 0.60 | 94.57% | 100% | 331 |
| 0.70 | 84.00% | 100% | 294 |
| 0.80 | 57.71% | 100% | 202 |
| 0.90 | 36.57% | 100% | 128 |

At threshold 0.50 the one raw error is successfully rejected.

For 344 accepted decisions and zero accepted errors, the one-sided exact 95% zero-error upper risk bound is approximately:

```text
0.867%
```

This is below the 1% target **on this development set**.

It is not a validation pass because threshold 0.50 is being selected after inspecting the development evidence.

## Comparison with validated Nimble

Validated Nimble policy:

```text
threshold = 0.80
accepted = 349 / 350
accepted errors = 0
coverage = 99.714%
steady-state median ≈ 15.2s
```

Strands development candidate:

```text
threshold = 0.50
accepted = 344 / 350
accepted errors = 0
coverage = 98.286%
p50 = 3.51s
```

Approximate latency speedup:

```text
15.2s / 3.51s ≈ 4.3×
```

So Strands gives up about 1.43 percentage points of local coverage in this development sample while reducing median latency by roughly 77%.

## Interpretation

The candidates separate cleanly:

### Laya

- latency: excellent
- quality: unacceptable
- confidence gating: does not rescue the model
- status: reject

### Strands

- latency: much faster than Nimble
- raw accuracy: near-perfect
- single observed error has low enough confidence to be rejected at 0.50
- coverage at 0.50 remains very high
- status: advance

## Candidate policy for fresh validation

The development evidence supports freezing the next candidate as:

```text
provider = Strands Decider 2B v21
checkpoint = StrandsAgents/strands-decider-2B-hobson-v21
threshold = 0.50
maximum accepted risk = 1%
confidence level = 95%
candidate count = 1
```

This policy must be frozen before seeing a new holdout.

## Next step

Create a new untouched fresh routing holdout.

The fresh set should be large enough that zero accepted errors can certify the 1% target at 95% confidence.

For a single predeclared policy, at least 299 accepted decisions are required when zero accepted errors occur.

Because development coverage at threshold 0.50 is ~98.3%, a 350-case fresh set remains an appropriate size.

Do not tune threshold 0.50 on the new holdout.

## Decision

- keep validated Nimble as the current production-quality reference
- reject Laya multilingual
- advance Strands Decider 2B v21 as the replacement candidate
- freeze threshold 0.50 for the next fresh-validation stage
- create a new fresh holdout before calling Strands validated
