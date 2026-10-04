# Nimble Latency-tail Analysis — 2026-10-05

## 目的

Validated Nimble Runで通常Latencyとp99の差が大きかった原因を切り分ける。

```text
p50  = 15.22s
p95  = 16.64s
p99  = 31.88s
```

Startup / Prefix集中なのか、Run全体で継続するPersistent Tailなのかを確認する。

## Validation

Heuristic修正後のRepository Test Suite:

- **49 tests passed**
- 0 failures

## Overall Latency

```text
requests = 350
median = 15222.7ms
p95 = 16637.4ms
p99 = 31875.7ms
max = 33552.6ms
```

## Prefix vs Remainder

| Prefix | Prefix Mean | Remainder Mean | Ratio |
| --- | ---: | ---: | ---: |
| first 1 | 32480.0ms | 15682.9ms | 2.071× |
| first 5 | 29619.8ms | 15529.6ms | **1.907×** |
| first 10 | 27548.4ms | 15383.3ms | 1.791× |
| first 20 | 23693.4ms | 15248.3ms | 1.554× |
| first 50 | 18584.0ms | 15255.4ms | 1.218× |

Prefixを広げるほどRatioが下がっており、Early-runへ集中した現象の形になっている。

## Position Bucket

大きなp95を持つのは最初の35 Request Bucketだけ。

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

Bucket 2〜10はほぼ15s台へ安定している。

## Late-tail Diagnostic

Configured Definition:

```text
late start = request 21
tail threshold = 1.5 × overall median = 22834.1ms
```

Observed:

```text
late-tail count = 0
```

Position 21以降にはConfigured Tail Thresholdを超えるRequestが存在しない。

## Refined Diagnostic

修正版Analyzer:

```text
Prefix-concentrated tail: True
Strongest early prefix: first 5
mean ratio: 1.907
First bucket median warmup-like: False
Top-outlier prefix concentration: 14/20
```

First-bucket Median FlagがFalseなのは、Position 1〜14の少数の極端なSlow Requestがp99 / Prefix Meanを押し上げる一方、1〜35全体のMedianまでは大きく動かさないため。

そのためPrimary ClassificationはPrefix-concentrated Diagnosticを使う。

## 解釈

**Observed p99問題はPersistent Run-wide Tailではなく、強くPrefixへ集中している。**

Evidence:

- First 5 Mean = Remainderの1.907×
- First 20 Mean = 1.554×
- Top 20 Outlierのうち14件がPosition 21より前
- Position 21以降のConfigured Tail Event = 0
- Later Bucket Median / p95はSteady-state付近で安定

Runtime Stabilization / Startup Hypothesisを強く支持する。

ただしSpecific Root Causeの証明ではない。

## 未解決のRoot Cause候補

- Synthetic Warmup後にも続くModel / Runtime Initialization
- CPU Frequency / Governor Ramp-up
- Memory / Page Cache
- Scheduler / Thermal State
- First Scenario Family特有のPrompt / Schema Shape
- その他Host / Runtime Initialization

## Decision

Validated Routing Policyは変更しない。

31.88s p99をSteady-state Latencyとして扱わない。

次はWarmup Strategyを変えるか、ModelがHotな状態で同一WorkloadをRepeatしてRuntime Stabilizationを分離する。

次の比較例:

1. Model unload
2. Warmup 1 Request
3. Short Representative Fixed Sequence
4. Model unload
5. Representative Warmupを複数Request
6. 同じFixed Sequence
7. First Request / First 5 / p50 / p95 / Late-tailを比較

この結果を見てからBenchmark Warmup Policyを変更する。
