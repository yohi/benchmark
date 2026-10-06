# Request telemetry and sparse-spike analysis

## Purpose

The process-restart warmup study removed most of the previous chronological/prefix artifact, but sparse outliers remained.

Examples included requests around 19–30 seconds while steady-state latency was around 15 seconds.

This follow-up does **not** tune warmup behavior again.

Instead, it records lightweight host/runtime context around each measured request and analyzes whether sparse latency spikes correlate with observable runtime state.

## Opt-in telemetry

Request telemetry is disabled by default.

Enable it only for a diagnostic run:

```bash
uv run systemone-warmup-study \
  --model nimble \
  --dataset datasets/latency-warmup-fixed-workload.jsonl \
  --repeats 2 \
  --reset-mode restart \
  --restart-command "sudo systemctl restart ollama" \
  --restart-wait 2 \
  --request-telemetry
```

Telemetry sampling is outside the measured HTTP request timer:

```text
capture before telemetry
↓
start request timer
↓
POST /v1/systemone
↓
stop request timer
↓
capture after telemetry
```

Therefore telemetry collection time itself is not included in `latency_ms`.

However, telemetry collection can still perturb later host state slightly. This is why it is opt-in and should be used for diagnostic runs rather than headline latency comparisons.

## Recorded fields

### CPU frequency

Before and after each measured request:

- mean current MHz across available CPUs
- minimum current MHz
- maximum current MHz

### System load

Before and after:

- 1-minute load average
- 5-minute load average
- 15-minute load average

### Temperature

When supported by `psutil.sensors_temperatures()`:

- maximum observed sensor temperature
- individual chip/label readings

Unsupported platforms record no temperature value rather than failing the run.

### Ollama process state

The collector identifies processes by process/executable name, not by arbitrary command-line substring.

This avoids false positives from repository paths such as `ollama-systemone`.

Before and after each request it records the Ollama daemon **and all of its descendant processes**, regardless of descendant executable name:

- matching/descendant PIDs
- parent PIDs
- process create times
- aggregate RSS
- aggregate CPU time

This process-tree aggregation is required because model runner work may execute in child processes rather than in the daemon itself.

Derived values:

- Ollama CPU percent over the measured request interval
- Ollama RSS delta
- whether the Ollama process identity set changed during the request

CPU percent may exceed 100% because it represents aggregate multi-core CPU time.

### System memory

- available bytes before/after request

## Sparse-spike analyzer

Use the emitted warmup-study details JSONL:

```bash
uv run systemone-spike-analysis \
  --details results/<RUN_ID>-warmup-study-details.jsonl \
  --spike-multiplier 1.25 \
  --top 20 \
  --output results/<RUN_ID>-spike-analysis.json
```

Default spike definition:

```text
latency >= 1.25 × median latency
```

For a ~15.2s median this corresponds to roughly 19s, matching the residual-spike range observed in the restart study.

## Analyzer output

For each telemetry metric it reports:

- number of usable observations
- mean / median / min / max
- Pearson correlation with latency
- spike-group summary
- non-spike-group summary

It also lists the highest-latency requests with their telemetry values and process-identity-change flag.

## Interpretation guardrails

Correlation is exploratory evidence, not causal proof.

In particular:

- a high load value can be consequence rather than cause
- temperature changes slowly and may not explain an individual request
- CPU frequency is a sampled snapshot, not a full frequency trace
- RSS can reflect model/runtime allocation rather than latency cause
- a small number of spikes makes correlation unstable

Use the analyzer primarily to decide which hypothesis deserves a controlled follow-up.

Examples:

- spikes consistently coincide with low CPU frequency → investigate governor/frequency behavior
- spikes coincide with process identity changes → investigate runtime/runner lifecycle
- spikes coincide with high temperature → investigate thermal throttling
- no telemetry metric separates spikes → avoid speculative host tuning and consider deeper profiler/runtime tracing

## Scope

This follow-up does not change:

- the validated Nimble threshold
- default benchmark warmup behavior
- the preferred process-restart reset boundary for controlled latency experiments
- quality evidence

The fixed 35-request workload remains latency-only evidence.


## Validation note for the first telemetry run

The first telemetry-enabled run (`20261005-215311`) produced implausibly low derived Ollama CPU utilization (~0.18–0.26%).

System-level fields from that run remain usable for preliminary exploration, but the Ollama CPU/RSS attribution must be treated as incomplete.

The collector was corrected to aggregate the Ollama daemon plus all descendants. Re-run the telemetry study after this correction before drawing conclusions from Ollama process CPU/RSS metrics.
