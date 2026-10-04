# Nimble selective risk control — 2026-10-05

## Purpose

Test whether a statistically bounded threshold-selection procedure is more appropriate than repeatedly fitting confidence cutoffs to the latest observed error.

The four existing Nimble runs are treated as development evidence. They contain 615 decisions in total.

## Method

A fixed 50-value threshold grid from 0.50 through 0.99 was evaluated.

For every threshold:

- accept decisions with confidence at or above the threshold
- count accepted errors
- compute the empirical accepted risk
- compute a one-sided exact Clopper-Pearson upper bound
- apply Bonferroni correction across all 50 threshold candidates

Family-wise confidence level: 95%.

Therefore:

```text
family alpha = 0.05
pointwise alpha = 0.001
```

## Test validation

The full repository test suite passed:

- 39 tests
- 0 failures

## 1% accepted-risk target

The exact zero-error sample requirement after correction is **688 accepted decisions**.

The current development pool contains only **615 total decisions**.

Result:

```text
feasible policy = none
```

This is primarily an **evidence-volume limitation**, not evidence that Nimble necessarily cannot satisfy a 1% risk requirement.

At threshold 0.80:

- coverage: 88.29%
- accepted: 543
- errors: 0
- empirical risk: 0%
- simultaneous upper risk bound: 1.26%

The observed zero-error performance is good, but the corrected upper bound remains above 1%.

## 1.5% diagnostic target

The zero-error sample requirement becomes **458 accepted decisions**.

At this diagnostic target, the maximum-coverage feasible policy is:

```text
threshold = 0.80
```

Development metrics:

- coverage: **88.29%**
- accepted: **543 / 615**
- accepted errors: **0**
- empirical risk: **0%**
- simultaneous upper risk bound: **1.26%**

Per-run diagnostics at threshold 0.80:

| Run | Coverage | Accepted | Errors |
| --- | ---: | ---: | ---: |
| 20261004-012101 | 90.95% | 191 | 0 |
| 20261005-033733 | 78.40% | 98 | 0 |
| 20261005-042132 | 87.86% | 123 | 0 |
| 20261005-052440 | 93.57% | 131 | 0 |

No run contributes an accepted error at threshold 0.80.

## Interpretation

The 1% run answers an important question: the current dataset is too small to certify such a strict simultaneous bound with a 50-threshold search.

The 1.5% diagnostic run shows that the methodology itself is not vacuous. With a slightly looser target, the current evidence supports a high-coverage zero-error development policy.

However, **1.5% was not predeclared as a product or safety requirement**.

Therefore threshold 0.80 is not frozen as a deployment candidate from this result.

## Decision

Do not choose the acceptable risk target after inspecting coverage.

The next decision must be external to this optimization:

- if the requirement is 1%, collect more independent development evidence or reduce the predeclared candidate family
- if an independently justified requirement is at least 1.26%, threshold 0.80 can be frozen as a candidate and taken to a new untouched fresh holdout

## Limitations

This result is a development-sample statistical bound under i.i.d./exchangeability assumptions.

It is not:

- a guarantee under distribution shift
- deployment validation
- a replacement for a new fresh holdout
- full conformal risk control

Production monitoring would still be necessary after validation.
