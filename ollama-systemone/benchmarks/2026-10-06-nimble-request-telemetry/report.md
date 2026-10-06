# Nimble request telemetry sparse-spike analysis — 2026-10-06

## Purpose

After process restart removed the broad startup/chronological latency artifact, investigate whether the remaining sparse 19–31s outliers correlate with host/runtime state.

The telemetry collector was corrected before this run to aggregate the Ollama daemon plus all descendant runner processes.

## Validation

Repository tests:

```text
Ran 69 tests in 0.078s
OK
```

## Run

```text
run_id = 20261005-232328
requests = 140
median = 15072.0ms
spike threshold = 18840.0ms
spike multiplier = 1.25
spikes = 0
spike rate = 0.000
```

Maximum observed latency:

```text
15807.8ms
```

All four trials had zero spikes.

| Trial | Requests | Median | Spikes |
| --- | ---: | ---: | ---: |
| 1 | 35 | 15.06s | 0 |
| 2 | 35 | 15.05s | 0 |
| 3 | 35 | 15.08s | 0 |
| 4 | 35 | 15.09s | 0 |

## Corrected process-tree telemetry

The collector now aggregates:
- Ollama daemon
- every descendant process
- aggregate CPU time
- aggregate RSS
- PID/create-time identity
- named-vs-descendant process counts

This corrected the earlier implausibly low process CPU attribution.

Observed mean aggregate Ollama CPU utilization over requests was approximately:

```text
398.7%
```

which is credible for multi-core CPU inference.

## Correlation result

No telemetry metric showed a strong relationship with latency in this corrected stable run.

```text
cpu_freq_before_mhz            r = +0.046
cpu_freq_after_mhz             r = -0.114
load1_before                   r = -0.031
load1_after                    r = -0.065
temperature_before_c           r = -0.217
temperature_after_c            r = -0.016
ollama_rss_before_bytes        r = -0.055
ollama_rss_after_bytes         r = -0.054
system_available_before_bytes  r = +0.115
ollama_cpu_percent             r = +0.063
ollama_process_count_before    r = +0.024
descendant_count_before        r = +0.024
```

These are all weak correlations.

Because there are zero spikes, there is no spike group to compare against non-spikes.

## Interpretation

The earlier sparse 19–31s outliers are **not stable enough to reproduce under the corrected telemetry run**.

This means the evidence does not support changing:
- CPU governor
- frequency policy
- thermal policy
- memory/page-cache behavior
- Ollama process lifecycle settings

The correct conclusion is not that these factors can never cause spikes.

The conclusion is:

> this experiment did not reproduce the sparse spikes, so there is no controlled evidence tying them to host/runtime telemetry and no basis for host tuning.

## Relationship to prior evidence

The evidence chain now separates three effects:

1. **Strong startup/chronological tail under model-unload reset**
   - reproducible
   - greatly attenuated by process restart
   - process-local runtime state implicated

2. **Representative-7 vs synthetic-1 warmup**
   - no consistent advantage
   - not adopted

3. **Sparse residual outliers after process restart**
   - appeared in some earlier runs
   - did not reproduce in the corrected 140-request telemetry run
   - cause remains inconclusive

## Decision

- Keep Nimble threshold 0.80 unchanged.
- Keep current/default warmup unchanged.
- Do not adopt representative-7.
- Use process restart when a controlled reset boundary is required for latency experiments.
- Do **not** change CPU governor, page cache, thermal controls, or scheduler settings.
- Keep request telemetry and spike analysis tooling available for a future naturally reproduced spike run.

## Next step

No immediate latency experiment is required.

If operational workloads later show repeated >1.25× median outliers, rerun the telemetry analyzer on that evidence before changing host settings.

Until then, the latency investigation can be considered closed for the current benchmark objective.
