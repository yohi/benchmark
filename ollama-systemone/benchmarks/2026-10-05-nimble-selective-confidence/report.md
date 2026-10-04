# Nimble selective confidence analysis — 2026-10-05

## Purpose

Determine whether Nimble confidence is useful for abstention after absolute and predicted-label-specific thresholds failed to generalize across fresh routing datasets.

Four existing runs were analyzed independently. Ollama was not rerun.

## Validation

The repository test suite passed:

- 30 tests
- 0 failures

## Results

| Run | N | Accuracy | Mean conf | ECE | Brier | Excess AURC | Error AUROC | Max error conf |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 20261004-012101 | 210 | 0.9905 | 0.9054 | 0.0890 | 0.0167 | 0.0000 | 0.9952 | 0.542108 |
| 20261005-033733 | 125 | 0.9840 | 0.8728 | 0.1112 | 0.0372 | 0.0005 | 0.9675 | 0.541419 |
| 20261005-042132 | 140 | 0.9786 | 0.9064 | 0.0722 | 0.0254 | 0.0007 | 0.9659 | 0.740743 |
| 20261005-052440 | 140 | 0.9786 | 0.9317 | 0.0626 | 0.0158 | 0.0003 | 0.9878 | 0.790712 |

All four runs reached **100% accepted accuracy at 90% coverage** when decisions were ordered from highest to lowest confidence.

At 95% coverage:
- 210-case validation remained error-free
- the other three runs each admitted one error

## Calibration

Nimble is consistently under-confident on these datasets.

Mean confidence is below raw accuracy in every run, with a signed gap of approximately -0.047 to -0.111. ECE remains material at 0.063–0.111.

Therefore the raw confidence value should not be interpreted as a calibrated probability of correctness.

## Selective ranking

The ranking behavior is substantially stronger than the calibration behavior.

- error-detection AUROC: **0.9659–0.9952**
- excess AURC: **0.0000–0.0007**
- zero errors in the highest-confidence 90% subset of every run

This means confidence is consistently useful for ranking safer decisions ahead of errors in the current evidence chain.

## Why previous thresholds failed

The maximum observed error confidence moved upward as the datasets became more realistic:

```text
0.542108
0.541419
0.740743
0.790712
```

A threshold chosen just above the previous error boundary therefore did not survive distribution shift.

The evidence supports a distinction:

- **absolute threshold stability:** weak
- **relative confidence ranking:** strong

## Decision

Do not continue adding predicted-label-specific thresholds.

Do not discard confidence either.

The next experiment should evaluate a more principled abstention mechanism that uses the strong ranking signal without assuming a universal confidence cutoff.

Possible next directions include:
- calibration on development evidence followed by frozen fresh validation
- coverage-targeted abstention
- selective/conformal risk control
- comparison with another decision model using the same metrics

Any policy derived from these four runs must be treated as development evidence and tested on another untouched fresh set.

## Statistical caution

Each run contains only two or three errors.

As a result:
- AUROC uncertainty is wide despite the high point estimates
- ECE depends on binning and sample size
- per-label metrics are especially unstable

The repeated cross-run pattern is meaningful evidence, but not deployment proof.
