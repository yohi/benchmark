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


## Stronger reset follow-up

The first warmup study showed a chronological effect that dominated the warmup profile:

```text
repeat 1:
  both profiles contained large latency spikes

repeat 2:
  both profiles were close to steady state
```

Because every trial used model unload, this suggests that unload does not reset all latency-relevant state.

The CLI therefore supports a stronger reset boundary:

```bash
uv run systemone-warmup-study \
  --model nimble \
  --dataset datasets/latency-warmup-fixed-workload.jsonl \
  --repeats 2 \
  --reset-mode restart \
  --restart-command "sudo systemctl restart ollama" \
  --restart-wait 2
```

With `--reset-mode restart`, every trial:

1. executes the configured restart command with `subprocess.run(..., check=True)`
2. waits the configured delay
3. probes `/api/tags` until Ollama is ready
4. executes the selected warmup profile
5. runs the same fixed 35-request measured workload

The restart command is configurable because service management may differ by host.

Use a non-interactive command. For systemd setups, `sudo systemctl restart ollama` is appropriate only when the current user already has non-interactive permission for that command.

Do not combine this first restart experiment with page-cache dropping, CPU-governor changes, or other host-level resets. The purpose is to change exactly one reset boundary.

### Interpretation

If the earlier repeat-1 / repeat-2 chronological difference disappears under process restart, process-local Ollama/runtime state is implicated.

If the chronological effect remains, move the next investigation to host-level state such as CPU frequency/governor, memory/page-cache residency, scheduler behavior, or thermal state.
