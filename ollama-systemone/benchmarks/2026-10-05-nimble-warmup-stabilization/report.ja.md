# Nimble Warmup Stabilization Study — 2026-10-05

## 目的

Current Synthetic Warmup 1件をRepresentative Routing Warmup 7件へ変更すると、以前観測したStartup-shaped Latency Tailが消えるかを検証する。

Measured WorkloadはLatency Analysis専用の固定再利用Dataset。

## Validation

Repository Test:

```text
Ran 54 tests in 0.087s
OK
```

## Trial Design

```text
trial 1: repeat 1 / synthetic-1
trial 2: repeat 1 / representative-7
trial 3: repeat 2 / representative-7
trial 4: repeat 2 / synthetic-1
```

各Trial前にModel Unloadし、同一35 Requestを測定する。

## Per-trial Result

| Trial | Profile | First-5 | First-20 Ratio | Median | p95 | Prefix Tail |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | synthetic-1 | 15.80s | 1.047 | 15.47s | 20.73s | false |
| 2 | representative-7 | 17.69s | 1.063 | 15.31s | 26.04s | false |
| 3 | representative-7 | 15.40s | 1.000 | 15.28s | 15.73s | false |
| 4 | synthetic-1 | 15.29s | 1.007 | 15.00s | 15.50s | false |

## Profile Aggregate

Representative / Synthetic:

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

**Representative-7 Warmupによる改善Evidenceはない。**

このStudyではFirst-5 / First-10 / First-20 / After-20 / p95がむしろ悪化した。

したがってCurrent Synthetic WarmupをRepresentative-7へ変更する根拠はない。

## より重要なFinding: Chronological Repeat Effect

最も強いPatternはWarmup Profileではない。

Repeat 1の両Trialに大きなSpikeがある。

- synthetic-1 repeat 1 p95: 20.73s
- representative-7 repeat 1 p95: 26.04s

Repeat 2の両Trialは安定。

- representative-7 repeat 2 p95: 15.73s
- synthetic-1 repeat 2 p95: 15.50s

Repeat 2ではProfile Orderを反転しているにもかかわらず、このPatternが残る。

つまりStabilizationは **Warmup ProfileよりStudyのChronological Progressに強く追従している**。

## 解釈

以下のSimple HypothesisはFalsified。

> Prefix Tailの主因はGeneric Synthetic Warmupが1件しかないことである。

次のHypothesisが強い。

> Model UnloadではEarly Latencyへ影響する全StateをResetできず、Process / Host / Runtime Stateの一部がTrialを跨いでStabilizeしている。

Candidate:

- Ollama Process / Runtime State
- CPU Frequency / Governor
- Page Cache / Memory Residency
- Allocator / Runtime Cache
- Scheduler / Thermal State
- その他Host-global State

このExperimentだけではどれかを特定できない。

## Decision

- Validated Routing Policyは変更しない
- Current Benchmark Warmup Behaviorも変更しない
- Representative-7を採用しない
- Model-unload-only ResetはCausal Warmup Comparisonとして不十分と判断

## Next Experiment

Trial間のReset Boundaryを強くする。

最小の次Stepは、**各Trial前にOllama Process / ServiceをRestart**し、同じFixed Measured Workload・交互Profile Orderで再比較すること。

RestartでRepeat 1 / Repeat 2のChronological Effectが消えるならProcess-local Runtime Stateの関与が強まる。

残るならCPU Governor / Page Cache / Scheduler / ThermalなどHost-level Stateを次に調べる。

最初のFollow-upではOS Page Cache DropやCPU Governor変更を同時に行わない。1回に1つのReset Boundaryだけを変える。
