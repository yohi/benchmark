# Cloudflare Clef-Flash hosted decision benchmark

## Objective

Evaluate Cloudflare-hosted Clef-Flash as the **free/cheap-cloud decision layer** after the local-model investigation converged on:

```text
Nimble .80
  validated quality reference
  ~15.2s local CPU median

Strands 2B
  ~3.5s local CPU median
  failed the 1% fresh risk gate
  stopped after threshold development

Laya multilingual
  ~0.36s local CPU median
  routing quality insufficient
  rejected
```

Clef-Flash is not being evaluated as another local CPU model. It is a hosted decision model intended for latency-critical routing.

## Cloudflare model

Workers AI model:

```text
@cf/cloudflare/clef-flash
```

Request model selector:

```text
clef-flash
```

Cloudflare documents Clef/Clef-Flash as System One compatible.

The native Workers AI REST endpoint is:

```text
POST https://api.cloudflare.com/client/v4/accounts/<ACCOUNT_ID>/ai/run/@cf/cloudflare/clef-flash
```

The Cloudflare REST API wraps model output in a top-level `result` envelope. The benchmark provider adapter therefore supports a configurable `response_path`.

## Secrets

Do not put an account ID or API token in Git.

The committed provider config uses environment expansion:

```text
configs/decision-providers.cloudflare.json
```

Required environment variables:

```bash
export CLOUDFLARE_ACCOUNT_ID='...'
export CLOUDFLARE_API_TOKEN='...'
```

For a custom API token, Cloudflare documents Workers AI Read and Workers AI Edit permissions for REST usage.

Unset environment variables cause the benchmark config loader to fail before making a request.

## Provider configuration

The committed configuration is equivalent to:

```json
{
  "name": "cloudflare-clef-flash",
  "url": "https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}/ai/run/@cf/cloudflare/clef-flash",
  "model": "clef-flash",
  "headers": {
    "Authorization": "Bearer ${CLOUDFLARE_API_TOKEN}"
  },
  "response_path": ["result"]
}
```

No Cloudflare SDK is installed.

## Pricing reference

As of 2026-10-06, Cloudflare lists:

```text
Clef-Flash:
  $0.09 / 1M input tokens
  8,182 Neurons / 1M input tokens

Workers AI free allocation:
  10,000 Neurons / day
```

The free allocation therefore corresponds to approximately:

```text
1.22M Clef-Flash input tokens / day
```

before accounting for any other Workers AI usage on the same account.

Do not assume the 350-case benchmark is free until the actual usage is measured.

The provider benchmark records the model's returned `usage` object and aggregates numeric usage fields per HTTP request.

## External latency reference

Cloudflare's own launch benchmark reports approximately:

```text
Clef-Flash median = 38.8ms
Clef-Flash p95    = 122.4ms
```

This is **not** the acceptance result for this project.

The project benchmark measures client-observed end-to-end HTTP latency from the actual machine and network path, including Internet/API overhead and any service queueing.

## Development dataset

Use:

```text
datasets/engineering-routing-single-policy-risk-fresh.jsonl
```

This 350-case dataset is already consumed evidence. It is appropriate for provider development/comparison but is no longer a fresh holdout.

Using the same development set as the earlier Nimble/Laya/Strands comparison makes quality results directly comparable.

## Smoke test

First verify authentication, REST envelope handling, and System One compatibility:

```bash
uv run systemone-provider-bench \
  --providers configs/decision-providers.cloudflare.json \
  --only cloudflare-clef-flash \
  --dataset datasets/smoke.jsonl \
  --warmup 1 \
  --iterations 1
```

Expected properties:

- HTTP request succeeds
- answers are read from Cloudflare's `result` envelope
- `choice` / `noul` answer parsing works
- latency is recorded
- returned usage is recorded when present

## Development comparison

After smoke succeeds:

```bash
uv run systemone-provider-bench \
  --providers configs/decision-providers.cloudflare.json \
  --only cloudflare-clef-flash \
  --dataset datasets/engineering-routing-single-policy-risk-fresh.jsonl \
  --warmup 1 \
  --iterations 1 \
  --thresholds 0.50,0.60,0.70,0.80,0.90
```

Primary development metrics:

1. raw routing accuracy
2. error distribution by routing class
3. confidence ranking / selective risk
4. coverage at zero or near-zero accepted errors
5. p50 / p95 / p99 client-observed latency
6. total input-token / Neuron usage and estimated cost

## Selective analysis

If raw quality is competitive:

```bash
uv run systemone-selective \
  --details results/<RUN_ID>-provider-details.jsonl \
  --model cloudflare-clef-flash \
  --bins 10 \
  --output results/<RUN_ID>-clef-flash-selective.json
```

Do not reuse the Nimble or Strands confidence threshold. Clef-Flash confidence must be treated as a separate scale.

## Threshold development

Only if raw/selective quality warrants continuation:

```bash
uv run systemone-risk-control \
  --details results/<RUN_ID>-provider-details.jsonl \
  --model cloudflare-clef-flash \
  --thresholds 0.50:0.99:0.01 \
  --max-risk 0.01 \
  --confidence-level 0.95 \
  --output results/<RUN_ID>-clef-flash-risk-development.json
```

This is development evidence, not validation.

If a candidate policy is selected, freeze it before creating a new untouched holdout.

## Development decision gate

Advance Clef-Flash to a fresh holdout only if:

```text
quality:
  plausible <=1% accepted-risk operating point

coverage:
  >=85% on development evidence

latency:
  materially below Strands' ~3.5s local p50

cost:
  benchmark usage is compatible with the intended free/cheap-cloud budget
```

The latency criterion is intentionally loose. A hosted candidate does not need to reproduce Cloudflare's vendor 38.8ms figure; it only needs to materially improve the actual routing path while preserving quality.

## Cost calculation

If the summary reports `input_tokens`:

```text
estimated USD
  = input_tokens / 1,000,000 * 0.09

estimated Neurons
  = input_tokens / 1,000,000 * 8,182

free-allocation share
  = estimated Neurons / 10,000
```

Use the Cloudflare dashboard as the authoritative account-level Neuron usage source because other Workers AI traffic may share the daily allocation.

## References

- https://developers.cloudflare.com/changelog/post/2026-10-01-clef-workers-ai/
- https://developers.cloudflare.com/workers-ai/get-started/rest-api/
- https://developers.cloudflare.com/workers-ai/platform/pricing/
- https://blog.cloudflare.com/clef-decision-models/
