# Selective risk control

## Purpose

`systemone-risk-control` chooses a confidence threshold from development evidence by controlling an upper confidence bound on the accepted error rate.

This is intentionally different from choosing a threshold just above the highest observed error confidence.

The analyzer:

1. evaluates a fixed confidence-threshold grid
2. counts accepted decisions and accepted errors at each threshold
3. computes a one-sided exact Clopper-Pearson upper bound on accepted error risk
4. applies a Bonferroni correction across the full threshold grid
5. selects the maximum-coverage threshold whose corrected upper bound is at or below the requested risk target

The selected threshold is a development candidate only. It must be frozen before evaluation on a new untouched fresh holdout.

## Why this is the next experiment

Across four Nimble runs, confidence ranking was strong:

- error-detection AUROC: 0.9659–0.9952
- excess AURC: 0.0000–0.0007
- top 90% by confidence contained zero errors in every run

But the maximum observed error confidence moved from about 0.54 to about 0.79.

That means ranking is useful while a hand-picked absolute cutoff is unstable.

Risk control tests whether a cutoff selected from a statistical error-risk bound generalizes better than a cutoff fitted to the previous maximum error.

## Statistical method

For each fixed threshold candidate:

- accept rows where `confidence >= threshold`
- let `n` be the number accepted
- let `k` be the number of accepted errors
- estimate empirical accepted risk as `k / n`
- compute a one-sided exact binomial upper confidence bound

Because multiple thresholds are searched on the same development evidence, the family alpha is divided by the number of threshold candidates using Bonferroni correction.

Example:

```text
confidence level = 0.95
threshold candidates = 50
family alpha = 0.05
pointwise alpha = 0.001
```

The selected threshold must satisfy:

```text
simultaneous upper accepted-risk bound <= requested max risk
```

while maximizing development coverage.

## Sample-size requirement

A strict risk target may be impossible to certify even with zero observed accepted errors.

For zero errors, the exact one-sided upper bound is:

```text
1 - alpha^(1/n)
```

The CLI reports the minimum number of zero-error accepted decisions required to certify the requested target after multiple-testing correction.

For example, with:

```text
max risk = 1%
family confidence = 95%
50 threshold candidates
pointwise alpha = 0.001
```

at least **688 zero-error accepted decisions** are required.

This prevents "no feasible policy" from being misread as model failure when the available development evidence is simply too small.

## Usage

Use the four existing Nimble runs as development evidence:

```bash
uv run systemone-risk-control \
  --details \
    results/20261004-012101-details.jsonl \
    results/20261005-033733-details.jsonl \
    results/20261005-042132-details.jsonl \
    results/20261005-052440-details.jsonl \
  --model nimble \
  --thresholds 0.50:0.99:0.01 \
  --max-risk 0.01 \
  --confidence-level 0.95 \
  --output results/nimble-risk-control-1pct.json
```

A second diagnostic run at a less strict target can show where the current evidence becomes sufficient:

```bash
uv run systemone-risk-control \
  --details \
    results/20261004-012101-details.jsonl \
    results/20261005-033733-details.jsonl \
    results/20261005-042132-details.jsonl \
    results/20261005-052440-details.jsonl \
  --model nimble \
  --thresholds 0.50:0.99:0.01 \
  --max-risk 0.015 \
  --confidence-level 0.95 \
  --output results/nimble-risk-control-1p5pct.json
```

Do not choose the final target after inspecting which one gives the most attractive coverage. The target risk is a product/safety requirement, not a tuning parameter.

## Output

The analyzer reports:

- candidate threshold count
- family and pointwise alpha
- minimum zero-error accepted sample size for the requested risk target
- empirical accepted risk at every threshold
- simultaneous one-sided upper risk bound at every threshold
- maximum-coverage feasible threshold, if one exists
- per-file empirical diagnostics at the selected threshold

## Scope and limitations

This is **not** a distribution-shift guarantee.

The statistical bound assumes the development examples are i.i.d./exchangeable for the fixed threshold rules being evaluated.

Bonferroni correction protects the threshold search over the configured fixed grid on that development evidence. It does not guarantee the same risk under a future workload distribution.

Therefore:

- do not call the selected threshold deployment-validated
- freeze it before looking at a new fresh holdout
- if the fresh holdout falsifies it, do not retune on that same holdout and call it fresh again
- production monitoring remains necessary even after fresh validation

This is also not a full conformal-risk-control implementation. It is the minimal exact-binomial risk-control experiment to determine whether a statistically selected threshold is worth pursuing before adding more machinery.
