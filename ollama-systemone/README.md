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
- a Pareto frontier across local coverage, local latency, and model-call count
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

## Notes

A single System One request may contain multiple questions. Latency statistics are therefore calculated per HTTP request, while accuracy and confidence statistics are calculated per decision/question.

CPU percentage is intentionally recorded as lightweight observational metadata. For rigorous CPU energy/per-core profiling, use an external profiler alongside this harness.
