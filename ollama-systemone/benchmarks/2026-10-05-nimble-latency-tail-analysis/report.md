# Nimble latency-tail analysis — 2026-10-05

## Purpose

Investigate why the validated Nimble run showed a large gap between ordinary latency and p99:

```text
p50  = 15.22s
p95  = 16.64s
p99  = 31.88s
```

The goal was to distinguish a startup/prefix-concentrated effect from a persistent run-wide tail.

## Validation

Repository test suite after the heuristic refinement:

- **49 tests passed**
- 0 failures

## Overall latency

```text
requests = 350
median = 15222.7ms
p95 = 16637.4ms
p99 = 31875.7ms
max = 33552.6ms
```

## Prefix vs remainder

| Prefix | Prefix mean | Remainder mean | Ratio |
| --- | ---: | ---: | ---: |
| first 1 | 32480.0ms | 15682.9ms | 2.071× |
| first 5 | 29619.8ms | 15529.6ms | **1.907×** |
| first 10 | 27548.4ms | 15383.3ms | 1.791× |
| first 20 | 23693.4ms | 15248.3ms | 1.554× |
| first 50 | 18584.0ms | 15255.4ms | 1.218× |

The effect decays as the prefix grows, which is characteristic of a concentrated early-run phenomenon.

## Position buckets

The first 35-request bucket is the only one with a very large p95:

```text
  1-35  mean=20030.3ms median=15637.0ms p95=32389.2ms
 36-70  mean=15211.9ms median=15224.5ms p95=15607.9ms
 71-105 mean=15452.4ms median=15441.5ms p95=15970.3ms
106-140 mean=15274.7ms median=15231.5ms p95=15676.7ms
141-175 mean=15313.4ms median=15287.6ms p95=15804.6ms
176-210 mean=15257.0ms median=15218.4ms p95=15694.6ms
211-245 mean=15140.2ms median=15062.9ms p95=15700.6ms
246-280 mean=15081.1ms median=15058.1ms p95=15517.1ms
281-315 mean=15189.6ms median=15086.4ms p95=15701.2ms
316-350 mean=15358.4ms median=15178.7ms p95=15891.7ms
```

Buckets 2–10 remain close to the stable ~15s region.

## Late-tail diagnostic

Configured definition:

```text
late start = request 21
tail threshold = 1.5 × overall median = 22834.1ms
```

Observed:

```text
late-tail count = 0
```

No request after position 20 crosses the configured tail threshold.

## Refined diagnostic

The refined analyzer reports:

```text
Prefix-concentrated tail: True
Strongest early prefix: first 5
mean ratio: 1.907
First bucket median warmup-like: False
Top-outlier prefix concentration: 14/20
```

The first-bucket median flag remains false because a small number of very slow requests in positions 1–14 inflate p99 and prefix mean without moving the median of the much wider 1–35 bucket enough.

That is why the prefix-concentrated diagnostic is the primary classification.

## Interpretation

**The observed p99 problem is strongly prefix-concentrated, not a persistent run-wide tail.**

Evidence:

- first 5 requests average 1.907× the remainder
- first 20 average 1.554× the remainder
- 14 of the top 20 latency outliers occur before position 21
- zero configured tail events occur after position 20
- later bucket medians and p95 values stay close to steady-state

This supports a runtime-stabilization/startup hypothesis.

It does not prove the specific cause.

## Root-cause candidates still open

Possible causes include:

- model/runtime initialization continuing after the synthetic warmup request
- CPU frequency/governor ramp-up
- memory/page-cache effects
- scheduler or thermal state
- prompt/schema shape effects in the first scenario family
- another host/runtime initialization effect

## Decision

Do not change the validated routing policy.

Do not treat the 31.88s p99 as representative steady-state latency.

The next experiment should isolate runtime stabilization by varying warmup strategy and/or repeating the same workload after the model is already hot.

A good next comparison is:

1. unload model
2. warmup 1 request
3. run a short representative fixed sequence
4. unload model
5. warmup several representative requests
6. run the exact same fixed sequence
7. compare first-request, first-5, p50, p95, and late-tail behavior

Only after that should the benchmark warmup policy be changed.
