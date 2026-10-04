# Warmup stabilization study

## Purpose

The validated Nimble run showed a strongly prefix-concentrated latency tail:

- first 5 requests averaged 1.907× the remainder
- first 20 averaged 1.554× the remainder
- no >=1.5×-median tail event occurred after request 20

This experiment tests whether the **current generic synthetic warmup** is too weak to stabilize the runtime before measurement.

It compares two fixed warmup profiles while keeping the measured workload identical.

## Profiles

### `synthetic-1`

The current benchmark warmup behavior:

- one generic synthetic System One request
- two-choice warmup-specific schema

### `representative-7`

Seven distinct warmup requests:

- one for each routing class
- same seven-class `route` schema as the measured engineering workload
- distinct task text from every measured request

The seven warmups cover:

- implementation
- debug
- review
- research
- planning
- documentation
- deterministic

## Measured workload

`datasets/latency-warmup-fixed-workload.jsonl`

The measured workload contains **35 requests**:

- 7 routing classes × 5 cases each
- 5 scenario families
- one case for every scenario × label pair
- order interleaves both scenario family and label

The cases are intentionally reused from the already-consumed single-policy fresh dataset.

This is a **latency-only experiment**. The 35 cases are not new quality evidence and must not be described as a fresh holdout.

Warmup tasks use different text from measured tasks, preventing exact measured-request reuse as warmup.

## Trial order

Default: two repeats per profile.

The order alternates to reduce temporal drift:

```text
repeat 1:
  synthetic-1
  representative-7

repeat 2:
  representative-7
  synthetic-1
```

Every trial starts with an explicit model unload.

Therefore all four trials run the exact same measured 35-request sequence from a reset model state, while only warmup strategy changes.

## Run

```bash
uv run systemone-warmup-study \
  --model nimble \
  --dataset datasets/latency-warmup-fixed-workload.jsonl \
  --repeats 2
```

The command writes:

- `results/<RUN_ID>-warmup-study-details.jsonl`
- `results/<RUN_ID>-warmup-study.json`

## Primary comparison

The most important metrics are:

- first-request latency
- first-5 mean latency
- first-10 mean latency
- first-20 mean latency
- mean latency after request 20
- p50
- p95
- prefix-concentrated-tail trial count
- late-tail event count

A useful warmup strategy should improve the early-prefix metrics while leaving steady-state latency approximately unchanged.

## Interpretation

Evidence for better runtime stabilization would look like:

```text
representative first-5 << synthetic first-5
representative first-20 ratio closer to 1.0
representative prefix-tail trials fewer
after-20 latency approximately unchanged
```

If representative warmup improves both early and steady-state latency, the difference may include broader host/runtime state effects rather than only prefix stabilization.

If it does not improve the prefix, the earlier latency tail is less likely to be solved by simply increasing or making warmup requests more representative.

## Guardrails

This study does not prove a specific root cause such as:

- model loading
- CPU governor ramp-up
- page cache
- scheduler state

It only tests whether a stronger representative warmup changes the observed prefix behavior.

Do not modify the validated routing threshold from this experiment.

Do not treat the reused 35-case workload as independent quality validation.
