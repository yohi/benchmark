# Ollama System One Benchmark

A provider/model-agnostic benchmark harness for Ollama decision models exposed through `POST /v1/systemone`.

It is intentionally isolated under `ollama-systemone/` so the repository can host unrelated benchmark suites in other root directories later.

## What it measures

- warm latency: mean, p50, p90, p95, p99
- requests/second
- labeled decision accuracy
- confidence-threshold accuracy and coverage
- escalation rate: the fraction that would be sent to a stronger model
- raw answers/probabilities for later analysis
- basic host CPU/RAM observations
- environment metadata

The primary optimization target is **maximum free/local coverage subject to a quality constraint**, not maximum standalone local-model accuracy.

## Requirements

- Python 3.11+
- Ollama with System One support
- models already pulled locally

Clef and Clef Flash require Ollama 0.35.1 or later.

## Setup

The uv project lives under `ollama-systemone/`:

```bash
cd ollama-systemone
uv sync

ollama pull clef-flash
ollama pull clef
ollama pull nimble
ollama pull tev1:4b
```

## Quick start

```bash
uv run systemone-bench \
  --models clef-flash,clef,nimble,tev1:4b \
  --dataset datasets/smoke.jsonl \
  --warmup 3 \
  --iterations 20
```

During a run, progress is updated after every measured request with overall progress, model-local progress, pass, case, request latency, and model-local ETA. Warmup/model-load time is excluded from ETA.

Results are written to `results/<timestamp>-summary.json` and `results/<timestamp>-details.jsonl`.

For a CPU-only machine, start with `clef-flash` or `tev1:4b` before loading the 27B Clef model.

## Dataset format

One JSON object per line:

```json
{
  "id": "billing-refund",
  "state": {"ticket": "I was charged twice. Please refund the extra payment."},
  "questions": {
    "team": {
      "type": "choice",
      "instructions": "Which team should handle this ticket?",
      "criteria": {
        "billing": "Payments and refunds",
        "technical": "Bugs and integrations",
        "other": "None of the above"
      }
    }
  },
  "expected": {"team": "billing"}
}
```

`expected` is optional. Without it the harness still measures latency and stores decisions, but cannot calculate accuracy.

The harness accepts the System One question schema directly, so datasets may use `choice`, `noul`, and `score`.

## Quality-preserving offload

For each confidence threshold, the summary reports:

- **coverage**: labeled decisions accepted locally
- **accuracy**: accuracy within that accepted subset
- **escalation_rate**: decisions deferred to a stronger model

Example interpretation:

```text
threshold  coverage  accepted accuracy  escalation
0.90       0.78      0.97               0.22
0.98       0.43      0.995              0.57
```

If your paid-only baseline is 99.5%, the second threshold is the interesting candidate: it offloads 43% while matching the baseline in this illustrative example.

Do not treat System One `confidence` as a calibrated probability of correctness. Evaluate threshold behavior on your own golden dataset.

## Recommended benchmark procedure

1. Build a representative golden dataset from real decision types.
2. Run each model with the same dataset and warm-up policy.
3. Compare latency and raw accuracy.
4. Compare threshold accuracy/coverage curves.
5. Select a threshold only if the accepted subset meets your quality baseline.
6. Escalate everything else to the existing stronger model.

The included smoke dataset only validates the harness. It is not a meaningful model-quality benchmark.

### Engineering routing golden dataset

`datasets/engineering-routing-golden.jsonl` contains 50 labeled engineering tasks across seven routing classes: implementation, review, research, debug, planning, documentation, and deterministic work. It is intended as a first repeatable quality comparison dataset, not as a substitute for production-derived examples.

Run quality comparison with a single pass first because CPU-only decision models can be slow:

```bash
uv run systemone-bench \\
  --models clef-flash,nimble,tev1:4b \\
  --dataset datasets/engineering-routing-golden.jsonl \\
  --warmup 1 \\
  --iterations 1
```

The summary includes per-case latency, accuracy, and mean confidence so outlier tasks can be identified without manually processing the detail JSONL. For production routing decisions, replace or supplement this synthetic golden set with representative real tasks.

### Engineering routing validation dataset

`datasets/engineering-routing-validation.jsonl` is a separate 210-case holdout set: 30 tasks for each of the seven routing classes. Its task texts do not duplicate the 50-case development/golden set.

Use it to challenge a threshold selected on the smaller development set rather than tuning and reporting against the same examples:

```bash
uv run systemone-bench \
  --models nimble \
  --dataset datasets/engineering-routing-validation.jsonl \
  --warmup 1 \
  --iterations 1 \
  --cache-reset unload \
  --thresholds 0.40,0.45,0.50,0.55,0.58,0.60,0.65,0.70
```

The summary now also includes:

- `by_expected`: per-label decision count, raw accuracy, mean confidence, and threshold coverage/accuracy
- `confusion_matrix`: expected label → predicted-label counts

These fields are useful for detecting a threshold that looks safe globally but fails disproportionately on one routing class.

The validation set is still synthetic. A production decision should ultimately be checked against representative real tasks, and repeatedly tuning against this holdout turns it into another development set.

### Implementation-boundary adversarial set

`datasets/engineering-routing-implementation-boundary.jsonl` contains 125 implementation-adjacent stress cases across five labels:

- implementation
- debug
- planning
- review
- research

Each class has 25 cases. Non-implementation cases deliberately contain implementation vocabulary such as "implement", "code", "fix", "migration", or named implementation mechanisms while asking for a different primary action. Implementation cases use similar contexts but actually require production-code changes.

This set targets the confusion pattern observed in the 210-case validation run, where the two raw Nimble errors were:

- debug → implementation
- planning → implementation

Evaluate the current candidate policy **without retuning first**:

```bash
uv run systemone-bench \
  --models nimble \
  --dataset datasets/engineering-routing-implementation-boundary.jsonl \
  --warmup 1 \
  --iterations 1 \
  --cache-reset unload \
  --thresholds 0.55,0.60,0.65,0.70
```

The primary checkpoint is the previously selected candidate threshold `0.60`. Inspect:

- overall accepted accuracy and coverage
- `by_expected` for class-local failures
- `confusion_matrix` for implementation-boundary errors
- confidence of every raw error

If this run causes the threshold or routing policy to change, treat this adversarial set as development evidence from that point onward. Validate the revised policy on another fresh split before calling it validated.

### Production-derived fresh routing dataset

`datasets/engineering-routing-production-derived-fresh.jsonl` contains 140 tasks abstracted from real engineering request patterns rather than generated from the existing benchmark examples.

The set intentionally reflects the actual shape of interactive engineering work:

- Japanese-first requests mixed with English technical terms, logs, commands, and identifiers
- short requests and constraint-heavy requests
- requests with attached error/log context
- multi-intent requests where the primary requested action must be identified
- current-information research requests
- repository changes, reviews, planning, documentation, and deterministic operations

Class distribution is intentionally workload-shaped rather than balanced:

| Label | Cases |
| --- | ---: |
| implementation | 30 |
| debug | 25 |
| review | 20 |
| research | 20 |
| planning | 20 |
| documentation | 15 |
| deterministic | 10 |
| **total** | **140** |

The examples are abstracted from real request patterns and remove account identifiers, secrets, and private URLs. Metadata preserves only a coarse `source_family` and `task_shape`; it does not preserve the original conversation source.

This is a fresh evaluation set for the current candidate policy. Evaluate **threshold 0.60 without retuning first**:

```bash
uv run systemone-bench \
  --models nimble \
  --dataset datasets/engineering-routing-production-derived-fresh.jsonl \
  --warmup 1 \
  --iterations 1 \
  --cache-reset unload \
  --thresholds 0.55,0.60,0.65,0.70
```

Primary checkpoint:

- model: `nimble`
- threshold: `0.60`
- accepted accuracy first
- local coverage second
- per-class failures and confusion matrix
- raw-error confidence values

Do not lower or raise the threshold based on this run and then continue to call this dataset an untouched holdout. If the routing policy changes after inspecting this result, validate the revised policy on another fresh set.

### Class-aware policy fresh holdout

`datasets/engineering-routing-policy-fresh-holdout.jsonl` is the fresh validation set for the class-aware Nimble policy selected after the production-derived set became development evidence.

The policy is frozen before measurement:

```text
default threshold = 0.60
predicted planning threshold = 0.80
```

The holdout contains 140 cases, balanced at 20 cases for each routing class. The balance is intentional: this stage is testing generalization of a fixed policy, not estimating production workload frequency.

Run the benchmark:

```bash
uv run systemone-bench \
  --models nimble \
  --dataset datasets/engineering-routing-policy-fresh-holdout.jsonl \
  --warmup 1 \
  --iterations 1 \
  --cache-reset unload \
  --thresholds 0.60,0.80
```

Then evaluate exactly one fixed class-aware policy:

```bash
uv run systemone-policy \
  --details results/<RUN_ID>-details.jsonl \
  --model nimble \
  --default-threshold 0.60 \
  --label-grid planning=0.80 \
  --min-accepted-accuracy 1.0 \
  --output results/<RUN_ID>-fixed-policy.json
```

Primary gate: accepted accuracy at the frozen policy.

If the fixed policy accepts any incorrect decision, treat the candidate as falsified. Do not retune on this holdout and continue to call it fresh evidence.

See:

- `datasets/engineering-routing-policy-fresh-holdout.md`
- `datasets/engineering-routing-policy-fresh-holdout.ja.md`

### Single-policy 1% risk fresh holdout

`datasets/engineering-routing-single-policy-risk-fresh.jsonl` is a new untouched validation set for one policy frozen before measurement:

```text
model = nimble
threshold = 0.80
maximum accepted risk = 1%
confidence level = 95%
candidate count = 1
```

The dataset contains 350 balanced cases: 50 for each routing class.

It uses 25 paired engineering scenario families. Each family contributes two variants for every routing label, keeping technical context similar while changing the requested primary action.

The size is deliberate. For one predeclared threshold, a 95% one-sided exact binomial upper bound below 1% requires at least 299 accepted decisions when zero accepted errors are observed. A 350-case holdout can reach that requirement if fresh coverage at threshold 0.80 is at least about 85.4%.

Run the fresh benchmark:

```bash
uv run systemone-bench \
  --models nimble \
  --dataset datasets/engineering-routing-single-policy-risk-fresh.jsonl \
  --warmup 1 \
  --iterations 1 \
  --cache-reset unload \
  --thresholds 0.80
```

Then evaluate exactly one predeclared policy:

```bash
uv run systemone-risk-control \
  --details results/<RUN_ID>-details.jsonl \
  --model nimble \
  --thresholds 0.80 \
  --max-risk 0.01 \
  --confidence-level 0.95 \
  --output results/<RUN_ID>-single-policy-risk.json
```

Because `--thresholds` contains exactly one value, this validation does not search across threshold candidates.

Primary gate:

```text
one-sided exact upper accepted-risk bound <= 1%
```

A zero-error run with fewer than 299 accepted decisions is **inconclusive due to sample size**, not a pass.

See:

- `datasets/engineering-routing-single-policy-risk-fresh.md`
- `datasets/engineering-routing-single-policy-risk-fresh.ja.md`

## Cascade analysis

`systemone-cascade` reuses existing benchmark detail JSONL files, so threshold/cascade experiments do not rerun Ollama.

For example, if one detail file contains Tev1 and another contains Nimble/Clef Flash:

```bash
uv run systemone-cascade \
  --details \
    results/20261003-140920-details.jsonl \
    results/20261003-142036-details.jsonl \
  --models tev1:4b,nimble \
  --thresholds 0.40:0.95:0.01,0.98,0.99 \
  --min-accepted-accuracy 1.0 \
  --output results/tev1-nimble-cascade.json
```

The analyzer evaluates every threshold combination in the requested grid. It reports:

- local coverage
- accuracy among locally accepted decisions
- paid/fallback escalation rate
- average and p95 local cascade latency
- local model calls per request
- acceptance and accuracy at each cascade stage
- best feasible single-model baselines for each selected model
- a coverage-ranked shortlist
- a global Pareto frontier across cascade configurations and single-model baselines, using local coverage, local latency, and model-call count
- collapsed threshold plateaus when multiple threshold combinations produce exactly the same routing decisions

The detail files must contain the same labeled decision set for every selected model. Duplicate model/case rows are rejected so separate repeated benchmark runs cannot be mixed accidentally.

Latency simulation currently requires one decision/question per benchmark HTTP request. This matches the engineering routing golden dataset. If a future dataset batches multiple questions into one System One request, the analyzer stops rather than double-counting that shared request latency.

To estimate end-to-end latency including a paid fallback, provide its assumed latency:

```bash
uv run systemone-cascade \
  --details results/tev-details.jsonl results/nimble-details.jsonl \
  --models tev1:4b,nimble \
  --thresholds 0.65:0.90:0.01 \
  --min-accepted-accuracy 1.0 \
  --fallback-latency-ms 3000
```

`accepted_accuracy` only measures decisions accepted by the local cascade. The analyzer does not assume that the paid fallback is correct unless its quality is evaluated separately.

## Predicted-label threshold policy analysis

`systemone-policy` reuses an existing benchmark detail JSONL and explores confidence thresholds keyed by the model's **predicted label**. It does not rerun Ollama.

This is useful when one global threshold is too coarse. For example, a production-derived evaluation may show that predictions of `planning` need a stricter acceptance threshold while other labels remain safe at the existing default.

The policy never uses the expected label at routing time. The expected/correct fields are used only to score an offline candidate policy.

Evaluate the existing global policy and explore a `planning` override:

```bash
uv run systemone-policy \
  --details results/20261005-042132-details.jsonl \
  --model nimble \
  --default-threshold 0.60 \
  --label-grid planning=0.60:0.90:0.01 \
  --min-accepted-accuracy 1.0 \
  --output results/20261005-042132-planning-policy.json
```

The analyzer reports:

- the baseline global-threshold policy
- every feasible predicted-label policy satisfying `--min-accepted-accuracy`
- local coverage and fallback rate
- accepted errors
- per-predicted-label acceptance/accuracy
- equivalent threshold plateaus that produce exactly the same accept/fallback decisions

Multiple labels can be explored by repeating `--label-grid`:

```bash
uv run systemone-policy \
  --details results/20261005-042132-details.jsonl \
  --model nimble \
  --default-threshold 0.60 \
  --label-grid planning=0.60:0.90:0.01 \
  --label-grid documentation=0.60:0.90:0.01 \
  --min-accepted-accuracy 1.0
```

The search is a Cartesian product across the supplied label grids and is bounded by `--max-combinations`.

### Methodology warning

Use this analyzer for **policy development**, not for silently converting the same evaluation set back into a holdout.

If a predicted-label threshold policy is selected using a detail file, that dataset has become development evidence for the revised policy. Validate the selected policy on another fresh dataset before treating it as deployment evidence.

## Selective confidence analysis

`systemone-selective` evaluates whether System One confidence is useful as an **abstention signal** across existing benchmark runs. It reuses detail JSONL files and does not rerun Ollama.

The analyzer deliberately separates two questions:

- **calibration**: does confidence numerically resemble probability of correctness?
- **selective classification**: even if it is not calibrated, does confidence rank safer decisions above errors?

Reported metrics include:

- mean confidence vs raw accuracy
- ECE and MCE
- Brier score
- AURC and oracle AURC
- excess AURC
- error-detection AUROC using `1 - confidence`
- risk at 50%, 80%, 90%, 95%, and 100% coverage
- raw error confidences
- breakdowns by predicted and expected label

Example across the current Nimble evidence chain:

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

Each detail file is analyzed independently instead of being pooled, so a tuned development set cannot hide a failure in a fresh holdout.

Do not interpret one ECE/AUROC value as deployment proof when a run contains only a few errors. The purpose is to check whether confidence behavior is stable across independent datasets before adding another routing threshold.

See:

- `docs/selective-confidence-analysis.md`
- `docs/selective-confidence-analysis.ja.md`

## Selective risk control

`systemone-risk-control` selects a development confidence threshold using a one-sided exact binomial upper bound on accepted error risk rather than by placing a cutoff just above the latest observed error confidence.

For a fixed threshold grid it:

- evaluates accepted errors and coverage
- computes a one-sided Clopper-Pearson upper risk bound
- applies Bonferroni correction across the threshold grid
- selects the maximum-coverage threshold satisfying the requested risk bound
- reports how many zero-error accepted samples would be required to certify the requested target

Example using the current four Nimble runs as development evidence:

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

With a 50-value threshold grid and 95% family-wise confidence, a 1% risk target requires at least 688 accepted decisions with zero observed accepted errors. The current development pool has fewer total decisions than that, so a strict target may be evidence-limited even before model quality is considered.

This method controls a development-sample statistical bound. It is **not** a distribution-shift guarantee and is not a full conformal-risk-control implementation.

Any selected threshold must be frozen before evaluation on another untouched fresh holdout.

See:

- `docs/selective-risk-control.md`
- `docs/selective-risk-control.ja.md`

## Latency-tail analysis

`systemone-latency-tail` analyzes request-order latency from an existing detail JSONL without rerunning Ollama.

Use it when p99 is much worse than p50/p95 and you need to distinguish an early startup-shaped tail from persistent runtime spikes or task-shape effects.

Example for the validated Nimble run:

```bash
uv run systemone-latency-tail \
  --details results/20261005-063902-details.jsonl \
  --model nimble \
  --prefixes 1,5,10,20,50 \
  --buckets 10 \
  --top 20 \
  --late-start 21 \
  --tail-multiplier 1.5 \
  --output results/20261005-063902-latency-tail.json
```

The analyzer reports:

- prefix vs remainder latency
- equal-position buckets
- top latency outliers
- expected/source/scenario-family breakdowns
- late-run tail counts relative to the overall median
- a heuristic `warmup-like` flag for an unusually slow first position bucket

The `warmup-like` flag is not causal proof. If the tail is prefix-concentrated, change the benchmark warmup strategy in a separate experiment. If large spikes persist later in the run, collect host/runtime telemetry before changing warmup behavior.

See:

- `docs/latency-tail-analysis.md`
- `docs/latency-tail-analysis.ja.md`

## Recording benchmark evidence

Raw run output under `results/` remains gitignored. Promote only decision-relevant runs into `benchmarks/`.

Each durable benchmark record should contain:

- `manifest.json` for exact run conditions and environment
- `metrics.json` for compact machine-readable comparison data
- `report.md` for interpretation, decision rationale, caveats, and next validation work

See `benchmarks/README.md` for the recording policy. The first promoted record is `benchmarks/2026-10-04-nimble-validation/`.

## Notes

A single System One request may contain multiple questions. Latency statistics are therefore calculated per HTTP request, while accuracy and confidence statistics are calculated per decision/question.

CPU percentage is intentionally recorded as lightweight observational metadata. For rigorous CPU energy/per-core profiling, use an external profiler alongside this harness.
