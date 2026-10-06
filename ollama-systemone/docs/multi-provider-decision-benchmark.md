# Multi-provider decision-model comparison

## Goal

Compare local Jev/System One compatible decision providers on the exact same engineering-routing dataset without adding provider SDK dependencies to the benchmark project.

The benchmark talks only to HTTP `POST /v1/systemone` endpoints.

Initial candidates:

- Ollama Nimble 9B
- Laya multilingual
- Strands Decider 2B v21

The existing 350-case single-policy dataset is **development comparison evidence only** for this work. It was already consumed during Nimble validation and must not be reused as a fresh holdout for a newly selected provider/policy.

## Why HTTP adapters

Provider-specific runtimes have very different dependency stacks:

- Ollama: native local service
- Laya: PyTorch/Transformers encoder runtime
- Strands Decider: PyTorch/Transformers + custom decision head

Installing all of them in the benchmark environment would couple the harness to model runtimes and make dependency conflicts part of the measurement.

Instead:

```text
provider runtime
    ↓
POST /v1/systemone
    ↓
systemone-provider-bench
    ↓
common details JSONL
    ↓
systemone-selective / systemone-risk-control
```

The common details format preserves the `model` field using the provider alias, so existing offline analyzers can be reused unchanged.

## Provider configuration

Default example:

```text
configs/decision-providers.local.json
```

It defines:

```text
nimble
  http://127.0.0.1:11434/v1/systemone
  model=nimble

laya-multilingual
  http://127.0.0.1:8001/v1/systemone
  model=multilingual

strands-decider-2b-v21
  http://127.0.0.1:8002/v1/systemone
  checkpoint is bound by the server
```

A provider may include:

- `name`: benchmark alias; also written as `model` in details for offline analyzer compatibility
- `url`: System One endpoint
- `health_url`: optional readiness endpoint
- `model`: optional request model field
- `headers`: optional HTTP headers
- `request_fields`: optional provider-specific top-level request fields

Provider-specific fields cannot override `state`, `questions`, or `model`.

## Start Nimble

Use the existing Ollama installation:

```bash
ollama pull nimble
```

The example config expects:

```text
http://127.0.0.1:11434/v1/systemone
```

## Start Laya multilingual on CPU

Laya exposes a Jev-compatible `POST /v1/systemone` server.

Keep its runtime isolated from the benchmark environment.

Example:

```bash
python3 -m venv ~/.venvs/laya
source ~/.venvs/laya/bin/activate
pip install "laya[serve]"

LAYA_DEVICE=cpu \
LAYA_PORT=8001 \
LAYA_DEFAULT_MODEL=multilingual \
LAYA_MODELS=multilingual \
LAYA_PRELOAD=1 \
LAYA_THREADS=24 \
laya-serve
```

The benchmark config explicitly sends:

```json
{"model": "multilingual"}
```

so the comparison does not depend on Laya's automatic language router.

The current engineering dataset is Japanese-first with English technical terms, so the multilingual checkpoint is the appropriate initial Laya candidate.

Laya's confidence scale is not assumed to match Nimble's. Do not reuse Nimble's `0.80` threshold without validation.

## Start Strands Decider 2B v21 on CPU

Use a separate environment.

The current reference checkpoint documented by Strands is:

```text
StrandsAgents/strands-decider-2B-hobson-v21
```

The same v21 artifact is also published under the Amazon namespace.

Example:

```bash
python3.12 -m venv ~/.venvs/strands-decider
source ~/.venvs/strands-decider/bin/activate

pip install torch==2.7.1 \
  --index-url https://download.pytorch.org/whl/cpu
pip install "strands-decider[cpu]"

strands-decider serve \
  StrandsAgents/strands-decider-2B-hobson-v21 \
  --device cpu \
  --port 8002
```

If the installed PyPI release does not yet expose the `cpu` extra, follow the Strands upstream inference documentation and install the current source checkout; CPU serving itself is supported.

The server binds the checkpoint at startup, so the sample provider config intentionally omits a request `model` field.

## Smoke test

With all requested endpoints running:

```bash
uv run systemone-provider-bench \
  --providers configs/decision-providers.local.json \
  --dataset datasets/smoke.jsonl \
  --warmup 1 \
  --iterations 1
```

Or target one provider:

```bash
uv run systemone-provider-bench \
  --providers configs/decision-providers.local.json \
  --only laya-multilingual \
  --dataset datasets/smoke.jsonl
```

## Development comparison

Run the already-consumed 350-case set:

```bash
uv run systemone-provider-bench \
  --providers configs/decision-providers.local.json \
  --dataset datasets/engineering-routing-single-policy-risk-fresh.jsonl \
  --warmup 1 \
  --iterations 1 \
  --thresholds 0.50,0.60,0.70,0.80,0.90
```

For the cleanest latency comparison, run providers **one at a time** using `--only`, with other candidate servers stopped. This avoids memory residency and background runtime effects from the other candidates.

Quality comparison may use a single multi-provider run because every provider receives the same cases, but headline latency should come from isolated runs.

## Output

```text
results/<RUN_ID>-provider-details.jsonl
results/<RUN_ID>-provider-summary.json
```

Summary per provider includes:

- request count
- mean / p50 / p90 / p95 / p99 latency
- requests per second
- raw accuracy
- mean confidence
- threshold coverage / accepted accuracy / escalation
- expected-label accuracy
- confusion matrix

Details include both:

```text
model=<provider alias>
provider=<provider alias>
provider_model=<request model or null>
```

This makes the details directly reusable by existing analyzers.

## Selective-confidence analysis

Do **not** compare provider confidence values numerically as if they share calibration.

Analyze each provider independently:

```bash
uv run systemone-selective \
  --details results/<RUN_ID>-provider-details.jsonl \
  --model laya-multilingual \
  --bins 10 \
  --output results/<RUN_ID>-laya-selective.json

uv run systemone-selective \
  --details results/<RUN_ID>-provider-details.jsonl \
  --model strands-decider-2b-v21 \
  --bins 10 \
  --output results/<RUN_ID>-strands-selective.json
```

Primary development questions:

1. raw routing accuracy
2. whether confidence ranks errors below correct decisions
3. coverage at zero or near-zero accepted errors
4. latency

Absolute confidence calibration is secondary to safe selective ranking for this router.

## Risk-control development

Thresholds must be developed separately per provider.

For example:

```bash
uv run systemone-risk-control \
  --details results/<RUN_ID>-provider-details.jsonl \
  --model laya-multilingual \
  --thresholds 0.50:0.99:0.01 \
  --max-risk 0.01 \
  --confidence-level 0.95 \
  --output results/<RUN_ID>-laya-risk-development.json
```

This is development only. Searching a threshold grid on these 350 cases consumes them for that provider policy.

## Selection rule

Do not pick the fastest model unconditionally.

A candidate advances only if it provides a plausible quality-preserving operating point.

Recommended order:

```text
1. raw accuracy
2. selective ranking / accepted errors
3. achievable local coverage
4. latency
5. operational complexity
```

A model that is 100x faster but cannot isolate its errors through confidence is not a replacement for Nimble's validated routing policy.

## Fresh validation after selection

After selecting one provider and freezing its threshold/policy:

1. create a new routing holdout not seen during provider selection
2. predeclare:
   - provider/checkpoint
   - threshold
   - maximum accepted risk
   - confidence level
3. run exactly that policy once
4. apply the existing one-sided risk-control gate

Only this new holdout can upgrade the candidate from "development winner" to "validated replacement."

## Expected decision paths

The experiment can lead to three useful outcomes.

### Small local model wins quality and latency

```text
rules
  ↓
Laya or Strands
  ↓ uncertain
cloud decision model / stronger LLM
```

This is the desired outcome.

### Small model is fast but confidence cannot isolate errors

Keep Nimble as the quality reference and do not replace it merely for latency.

A small model may still be useful as an earlier stage only if a subsequent cascade analysis proves that the extra stage reduces total latency/cost without reducing accepted quality.

### No local candidate preserves quality

Use a fast hosted decision model such as Clef-Flash in the free/cheap-cloud layer and retain local deterministic rules ahead of it.

That is a separate experiment from this CPU-local comparison.
