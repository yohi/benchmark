# Latency-tail analysis

## Purpose

`systemone-latency-tail` analyzes request-order latency behavior from an existing System One `*-details.jsonl` file.

It is intended for cases where overall p99 is much worse than p50/p95 and we need to distinguish:

- startup/prefix concentration
- persistent late-run tail
- class or scenario dependence
- isolated runtime spikes

The analyzer is offline and does not rerun Ollama.

## What it reports

### Prefix vs remainder

Compares the first N measured requests against the remainder for configurable prefix sizes.

Default prefixes:

```text
1, 5, 10, 20, 50
```

This is useful for identifying a startup-shaped pattern where early requests remain slower even after the explicit benchmark warmup request has completed.

### Position buckets

Splits measured request order into equal buckets and reports:

- mean latency
- median latency
- p90/p95/p99
- min/max

This shows whether latency stabilizes after an early region or remains variable throughout the run.

### Top outliers

Reports the highest-latency requests with:

- request position
- case ID
- expected/predicted label
- confidence
- source/scenario metadata when present
- CPU before/after observations
- memory delta

### Group breakdowns

Reports latency summaries by:

- expected label
- source family
- scenario family

This can identify a semantic/task-shape effect that happens to coincide with request order.

### Late-tail diagnostic

Counts requests after a chosen position whose latency is at least a configurable multiple of the overall median.

Default:

```text
start position = 21
tail threshold = 1.5 × overall median
```

This distinguishes an early prefix tail from persistent late-run spikes.

## Example

Analyze the single-policy fresh validation run:

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

## Interpretation guardrails

The analyzer detects correlations with request order and metadata.

It does **not** prove the root cause of a slow prefix.

For example, a warmup-like first bucket can be caused by:

- model/runtime initialization continuing after the explicit synthetic warmup request
- CPU frequency/governor behavior
- memory/page-cache effects
- thermal or scheduler state
- prompt-shape differences in early dataset rows
- other host/runtime effects

The current heuristic marks the first position bucket as `warmup-like` when its median is at least 25% slower than the median of later bucket medians.

That flag is a triage signal only.

If the tail is strongly prefix-concentrated, the next experiment should change benchmark warmup strategy or run a repeated identical workload to determine whether the effect is runtime stabilization rather than task semantics.

If large spikes remain late in the run, collect host/runtime telemetry around those requests before changing warmup policy.
