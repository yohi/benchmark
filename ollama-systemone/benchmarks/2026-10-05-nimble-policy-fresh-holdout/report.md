# Nimble class-aware policy fresh holdout — 2026-10-05

## Purpose

Validate the previously selected class-aware Nimble policy on a new balanced fresh holdout.

The policy was frozen before this run:

```text
default threshold = 0.60
predicted planning threshold = 0.80
```

## Test validation

The repository test suite passed locally:

- 21 tests passed
- 0 failures

This includes the new holdout schema/balance/frozen-policy/non-overlap tests and all existing benchmark/policy tests.

## Benchmark result

Run ID: `20261005-052440`

Raw accuracy: **97.86% (137/140)**.

Global threshold diagnostics:

| Threshold | Coverage | Accepted accuracy | Escalation |
| ---: | ---: | ---: | ---: |
| 0.60 | 98.57% | 99.28% | 1.43% |
| 0.80 | 93.57% | 100% | 6.43% |

These global thresholds are diagnostic only. The actual candidate policy is class-aware.

## Raw errors

Three raw errors were observed:

| Case | Expected | Predicted | Confidence | Frozen policy |
| --- | --- | --- | ---: | --- |
| `fresh-037-debug` | debug | review | 0.432299 | fallback |
| `fresh-116-documentation` | documentation | implementation | **0.790712** | **accept (wrong)** |
| `fresh-120-documentation` | documentation | implementation | 0.585526 | fallback |

The decisive failure is `fresh-116-documentation`.

The candidate policy only raises the threshold when the model predicts `planning`. This error predicts `implementation`, so the default threshold 0.60 applies. Confidence 0.790712 therefore causes an incorrect local accept.

## Policy verdict

**FAIL — the frozen class-aware candidate is falsified by this fresh holdout.**

The previous development hypothesis solved the observed `planning`-prediction failures, but a new high-confidence `documentation → implementation` failure appears here.

The current evidence therefore does not support deployment of:

```text
default = 0.60
planning = 0.80
```

## Derived fixed-policy metrics

The fixed-policy CLI has not yet been run for this holdout, but the benchmark summary is sufficient to determine the outcome.

At global threshold 0.60, 138 decisions are accepted with one accepted error. The planning-specific 0.80 override additionally rejects one correct planning prediction at confidence 0.631908.

Therefore the frozen policy is expected to produce:

- local accepted: 137/140
- local coverage: **97.86%**
- accepted correct: 136
- accepted accuracy: **99.27%**
- fallback: 3/140 = **2.14%**
- accepted errors: **1**

Run `systemone-policy` to create the canonical fixed-policy output artifact, but the pass/fail conclusion cannot change.

## Interpretation

The main lesson is that the risk is not limited to one predicted label.

Earlier production-derived development evidence exposed two high-confidence errors predicting `planning`. The planning-specific threshold removed those errors on the development set.

This fresh holdout exposes a different failure boundary:

```text
documentation → implementation @ 0.790712
```

That means a policy shaped only around the previously observed planning errors is too narrow.

## Methodology status

This holdout remains valid fresh validation evidence for the frozen 0.60/0.80 policy and has falsified it.

Do not tune a new implementation threshold directly on this holdout and then reuse the same set as validation evidence.

A revised policy may use this run as development evidence, but it must be validated on another fresh set.
