# Nimble warmup study with Ollama process restart — 2026-10-05

## Purpose

Strengthen the trial reset boundary from model unload to full Ollama process/service restart while keeping the warmup profiles and measured workload unchanged.

The prior unload-reset study showed a strong chronological effect that dominated warmup profile.

## Validation

Repository test suite:

```text
Ran 57 tests in 0.072s
OK
```

## Reset

Each trial used:

```text
sudo systemctl restart ollama
restart wait = 2s
/api/tags readiness probe
```

Then the selected warmup profile and the same fixed 35-request measured workload were executed.

## Per-trial results

| Trial | Repeat | Profile | First-5 | First-20 ratio | Median | p95 | Prefix tail |
| --- | ---: | --- | ---: | ---: | ---: | ---: | --- |
| 1 | 1 | synthetic-1 | 15.74s | 0.974 | 15.20s | 16.95s | false |
| 2 | 1 | representative-7 | 18.42s | 1.039 | 15.21s | 17.38s | false |
| 3 | 2 | representative-7 | 15.30s | 0.983 | 15.24s | 15.83s | false |
| 4 | 2 | synthetic-1 | 15.38s | 1.017 | 15.29s | 16.41s | false |

No trial reproduced the original strong prefix-concentrated tail.

## Warmup profile comparison under restart

Representative / synthetic:

```text
first-1   1.431×
first-5   1.083×
first-10  1.036×
first-20  1.008×
after-20  0.992×
median    0.999×
p95       0.996×
```

The large first-request ratio is caused by the representative repeat-1 first measured request at 29.62s.

From first-20 onward, median, p95, and after-20 latency are effectively equivalent between profiles.

Therefore the process-restart experiment again provides no reason to adopt representative-7.

## Reset-boundary comparison

The important result is how much the repeat-1 / repeat-2 p95 gap changed.

### Synthetic profile

Unload reset:

```text
repeat 1 p95 = 20.73s
repeat 2 p95 = 15.50s
repeat 1 / repeat 2 = 1.337×
difference = +33.7%
```

Process restart:

```text
repeat 1 p95 = 16.95s
repeat 2 p95 = 16.41s
repeat 1 / repeat 2 = 1.033×
difference = +3.3%
```

The absolute repeat gap shrank by approximately **89.7%**.

### Representative profile

Unload reset:

```text
repeat 1 p95 = 26.04s
repeat 2 p95 = 15.73s
repeat 1 / repeat 2 = 1.655×
difference = +65.5%
```

Process restart:

```text
repeat 1 p95 = 17.38s
repeat 2 p95 = 15.83s
repeat 1 / repeat 2 = 1.099×
difference = +9.9%
```

The absolute repeat gap shrank by approximately **84.9%**.

## Interpretation

**Ollama process/service restart substantially attenuates the chronological latency effect.**

This strongly implicates process-local Ollama/runtime state as a major contributor to the earlier instability.

The evidence is stronger than simply observing lower p95:

- the same profiles were used
- the same fixed 35-request sequence was used
- profile order was still reversed across repeats
- the only intended experimental change was reset boundary
- both profile-specific repeat gaps contracted dramatically

The original strong prefix-concentrated tail also did not reappear under restart.

## Residual behavior

Restart does not make latency perfectly deterministic.

Examples still include isolated spikes:

- representative repeat 1, first measured request: 29.62s
- synthetic repeat 1, request 26: 25.37s
- representative repeat 1, request 29: 19.03s
- synthetic repeat 2, request 19: 19.31s

These are sparse rather than a sustained prefix pattern.

Therefore process-local state explains a large part of the earlier chronological effect, but not necessarily all latency variance.

## Decision

- Do not adopt representative-7.
- Keep the validated Nimble routing threshold unchanged.
- For latency experiments that need comparable cold-start/reset conditions, prefer **process restart** over model unload.
- Do not reinterpret the fixed 35-case workload as fresh quality evidence.
- Do not treat process restart as necessary for normal production routing; it is an experimental reset boundary.

## Next step

The original warmup question is sufficiently answered:

> more representative warmup is not the fix; stronger process reset removes most of the chronological artifact.

Further latency investigation should now focus on **sparse residual spikes**, not prefix warmup.

Before changing CPU governor or dropping page cache, add lightweight host/runtime telemetry around each request, such as:

- CPU frequency summary
- system load
- process CPU/RSS
- temperature if available
- Ollama process identity/start time

This can determine whether the remaining 19–30s outliers correlate with host state.

Given the routing objective, this follow-up is optional unless ~15s steady-state latency or rare spikes remain operationally unacceptable.
