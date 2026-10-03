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

During a run, progress is updated after every measured request with model, pass, case, request latency, percentage, and ETA.

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

## Notes

A single System One request may contain multiple questions. Latency statistics are therefore calculated per HTTP request, while accuracy and confidence statistics are calculated per decision/question.

CPU percentage is intentionally recorded as lightweight observational metadata. For rigorous CPU energy/per-core profiling, use an external profiler alongside this harness.
