# Selective confidence analysis

## Purpose

`systemone-selective` evaluates whether a decision model's confidence is useful for **abstention**, not just whether one hand-picked threshold happened to work on one dataset.

This is the next step after repeated threshold policies failed to generalize across fresh engineering-routing sets.

The analyzer works only from existing `*-details.jsonl` files and does not rerun Ollama.

## Two questions

The analysis separates two different questions.

### 1. Calibration

Does a confidence value numerically resemble the probability that the prediction is correct?

Metrics:

- **mean confidence vs accuracy gap**
- **ECE** — expected calibration error using equal-width bins
- **MCE** — largest calibration-bin gap
- **Brier score** — mean squared error between confidence and correctness

Lower is better for ECE, MCE, and Brier.

Important: System One confidence is not assumed to be a calibrated probability. These metrics are diagnostics that test that assumption.

### 2. Selective classification

Even if confidence is not calibrated as a probability, does confidence at least rank safer decisions above risky decisions?

Metrics:

- **AURC** — area under the risk-coverage curve; lower is better
- **oracle AURC** — best possible ordering for the same number of errors
- **excess AURC** — observed AURC minus oracle AURC; zero is ideal
- **error-detection AUROC** — uses `1 - confidence` as an error score; higher is better
- **risk@coverage** — selective risk when accepting the highest-confidence 50%, 80%, 90%, 95%, and 100%

The analyzer also reports every raw error confidence and breakdowns by both predicted label and expected label.

## Usage

Compare multiple Nimble runs without rerunning the model:

```bash
uv run systemone-selective \
  --details \
    results/20261004-012101-details.jsonl \
    results/20261005-033733-details.jsonl \
    results/20261005-042132-details.jsonl \
    results/20261005-052440-details.jsonl \
  --model nimble \
  --bins 10 \
  --output results/nimble-selective-confidence.json
```

Each input file is analyzed independently. This is intentional: pooling a tuned development set and a fresh holdout can hide dataset-specific failure modes.

## How to interpret the current routing problem

A useful confidence signal should show all of the following across multiple independent runs:

1. errors tend to have lower confidence than correct decisions
2. error-detection AUROC is consistently well above random ranking
3. excess AURC stays low
4. selective risk falls as coverage is reduced
5. high-confidence errors are rare and do not migrate unpredictably between predicted labels

A model can have high raw accuracy while still being a poor selective classifier if occasional errors receive very high confidence.

That is exactly the failure mode this analyzer is intended to detect.

## Statistical caution

Engineering-routing datasets currently contain very few errors per run.

Therefore:

- ECE depends on binning and sample size
- AUROC can move sharply when only two or three errors exist
- per-label metrics can be especially noisy
- one apparently perfect risk@coverage result is not deployment evidence

Use the metrics to compare repeated independent runs and detect persistent structure, not to create another threshold from a single dataset.

## Decision rule for the next phase

Do not tune another routing threshold until the confidence analysis is reviewed.

If confidence consistently separates errors from correct predictions, a more principled abstention policy may still be viable.

If high-confidence errors continue to appear across unrelated predicted labels, compare another decision model or add a stronger uncertainty signal rather than accumulating label-specific thresholds.
