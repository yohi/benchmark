# Nimble single-policy 1% risk fresh validation — 2026-10-05

## Purpose

Validate one policy that was frozen before measurement:

```text
model = nimble
threshold = 0.80
maximum accepted risk = 1%
confidence level = 95%
candidate count = 1
```

This fresh holdout contains 350 new cases and does not search across threshold candidates.

## Validation

Repository tests:

- 42 passed
- 0 failed

Fresh benchmark run:

```text
run_id = 20261005-063902
decisions = 350
raw accuracy = 350/350 = 100%
```

At threshold 0.80:

- accepted: **349/350**
- coverage: **99.714%**
- accepted errors: **0**
- accepted accuracy: **100%**
- fallback: **1/350**

The only fallback was `risk-fresh-112-deterministic`, which was correctly classified but had confidence 0.734555.

## Canonical single-policy risk evaluation

Executed:

```text
candidates = 1
family alpha = 0.05
pointwise alpha = 0.05
zero-error sample requirement = 299 accepted decisions
```

Observed:

```text
threshold = 0.80
coverage = 0.9971
accepted = 349
errors = 0
empirical risk = 0.0000
upper risk bound = 0.0085
```

The one-sided exact 95% upper accepted-risk bound is therefore about **0.85%**, below the predeclared **1%** target.

## Verdict

**PASS**

The frozen single-policy candidate satisfies the predeclared fresh-holdout gate:

```text
upper accepted-risk bound <= 1%
```

No threshold tuning was performed on this holdout.

## Per-class result

All seven routing classes achieved 50/50 raw accuracy.

At threshold 0.80:

- debug: 50 accepted, 0 errors
- deterministic: 49 accepted, 0 errors
- documentation: 50 accepted, 0 errors
- implementation: 50 accepted, 0 errors
- planning: 50 accepted, 0 errors
- research: 50 accepted, 0 errors
- review: 50 accepted, 0 errors

## Interpretation

This is substantially stronger evidence than the earlier development-time threshold search because:

1. threshold 0.80 was selected before this dataset was measured
2. the accepted-risk target of 1% was also predeclared
3. the holdout contains enough accepted samples to make the 1% gate statistically testable
4. the canonical single-policy exact-binomial evaluation passes

This validates the policy under this fresh evaluation distribution.

It does **not** guarantee the same risk under future production distribution shift.

## Latency note

The quality gate passed, but latency remains a separate concern.

Observed benchmark latency:

- mean: 15.73 s
- p50: 15.22 s
- p95: 16.64 s
- p99: 31.88 s

The p99 tail should be investigated separately from the routing-quality decision.

## Decision

The frozen routing policy can now be treated as **fresh-holdout validated** for this benchmark definition:

```text
nimble
accept when confidence >= 0.80
otherwise escalate
```

Next work should focus on:

- production/online monitoring design
- latency-tail investigation
- additional independent evidence over time

Do not reuse this holdout to tune the threshold while continuing to treat it as fresh validation evidence.
