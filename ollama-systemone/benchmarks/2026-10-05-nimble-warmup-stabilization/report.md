# Nimble warmup stabilization study — 2026-10-05

## Purpose

Test whether replacing the current single synthetic warmup with seven representative routing warmups removes the previously observed startup-shaped latency tail.

Measured workload is fixed and reused only for latency analysis.

## Validation

Repository tests:

```text
Ran 54 tests in 0.087s
OK
```

## Trial design

```text
trial 1: repeat 1 / synthetic-1
trial 2: repeat 1 / representative-7
trial 3: repeat 2 / representative-7
trial 4: repeat 2 / synthetic-1
```

Every trial begins with model unload and then runs the same 35 measured requests.

## Per-trial results

| Trial | Profile | First-5 | First-20 ratio | Median | p95 | Prefix tail |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | synthetic-1 | 15.80s | 1.047 | 15.47s | 20.73s | false |
| 2 | representative-7 | 17.69s | 1.063 | 15.31s | 26.04s | false |
| 3 | representative-7 | 15.40s | 1.000 | 15.28s | 15.73s | false |
| 4 | synthetic-1 | 15.29s | 1.007 | 15.00s | 15.50s | false |

## Profile aggregate

Representative / synthetic:

```text
first-1   0.974×  (-2.6%)
first-5   1.064×  (+6.4%)
first-10  1.078×  (+7.8%)
first-20  1.033×  (+3.3%)
after-20  1.027×  (+2.7%)
median    1.004×  (+0.4%)
p95       1.153×  (+15.3%)
```

## Result

**The representative-7 warmup does not improve the observed latency behavior.**

It is worse on first-5, first-10, first-20, after-20, and p95 in this study.

There is therefore no evidence to replace the current synthetic warmup with representative-7.

## More important finding: chronological repeat effect

The strongest pattern is not warmup profile.

Both trials in repeat 1 contain large spikes:

- synthetic-1 repeat 1 p95: 20.73s
- representative-7 repeat 1 p95: 26.04s

Both trials in repeat 2 are stable:

- representative-7 repeat 2 p95: 15.73s
- synthetic-1 repeat 2 p95: 15.50s

This occurs despite reversing profile order in repeat 2.

That means the observed stabilization follows **chronological study progress more strongly than warmup profile**.

## Interpretation

The current experiment falsifies the simple hypothesis:

> The prefix tail is caused primarily by using only one generic synthetic warmup request.

A stronger hypothesis now is:

> Model unload does not reset all state that affects early latency, and some process/host/runtime state continues to stabilize across trials.

Candidate state includes:

- Ollama process/runtime state
- CPU frequency/governor state
- page cache / memory residency
- allocator/runtime caches
- scheduler/thermal state
- other host-global state

This experiment cannot distinguish these causes.

## Decision

- Keep the validated routing policy unchanged.
- Keep the current benchmark warmup behavior unchanged.
- Do **not** adopt representative-7.
- Treat model-unload-only reset as insufficient for a causal warmup comparison.

## Next experiment

Use a stronger reset boundary between trials.

The cleanest next step is to compare the same profiles with **Ollama process/service restart before every trial**, using the same fixed measured workload and alternating profile order.

If restart removes the repeat-1/repeat-2 chronological effect, process-local runtime state is implicated.

If the effect remains, investigate host-level state such as CPU governor, page cache, scheduler, or thermal behavior.

Do not drop OS page cache or change CPU governor in the first follow-up experiment; change one reset boundary at a time.
