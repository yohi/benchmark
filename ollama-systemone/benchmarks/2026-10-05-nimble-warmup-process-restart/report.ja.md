# Nimble Warmup Study — Ollama Process Restart — 2026-10-05

## 目的

Trial Reset BoundaryをModel UnloadからOllama Process / Service Restartへ強化し、Warmup ProfileとMeasured Workloadを変更せず再比較する。

以前のUnload-reset StudyではWarmup ProfileよりChronological Effectが支配的だった。

## Validation

Repository Test Suite:

```text
Ran 57 tests in 0.072s
OK
```

## Reset

各Trialで以下を実施。

```text
sudo systemctl restart ollama
restart wait = 2s
/api/tags readiness probe
```

その後、Selected Warmup Profileと同一Fixed 35 Requestを実行した。

## Per-trial Result

| Trial | Repeat | Profile | First-5 | First-20 Ratio | Median | p95 | Prefix Tail |
| --- | ---: | --- | ---: | ---: | ---: | ---: | --- |
| 1 | 1 | synthetic-1 | 15.74s | 0.974 | 15.20s | 16.95s | false |
| 2 | 1 | representative-7 | 18.42s | 1.039 | 15.21s | 17.38s | false |
| 3 | 2 | representative-7 | 15.30s | 0.983 | 15.24s | 15.83s | false |
| 4 | 2 | synthetic-1 | 15.38s | 1.017 | 15.29s | 16.41s | false |

OriginalのStrong Prefix-concentrated TailはどのTrialでも再現しなかった。

## Restart下のWarmup Profile比較

Representative / Synthetic:

```text
first-1   1.431×
first-5   1.083×
first-10  1.036×
first-20  1.008×
after-20  0.992×
median    0.999×
p95       0.996×
```

First-1の大差はRepresentative Repeat 1の最初のMeasured Requestが29.62sだったため。

First-20以降、Median / p95 / After-20はProfile間で実質同等。

したがってProcess Restart StudyでもRepresentative-7を採用する根拠はない。

## Reset Boundary比較

重要なのはRepeat 1 / Repeat 2のp95差がどれだけ縮小したか。

### Synthetic

Unload Reset:

```text
repeat 1 p95 = 20.73s
repeat 2 p95 = 15.50s
repeat 1 / repeat 2 = 1.337×
difference = +33.7%
```

Process Restart:

```text
repeat 1 p95 = 16.95s
repeat 2 p95 = 16.41s
repeat 1 / repeat 2 = 1.033×
difference = +3.3%
```

Absolute Repeat Gapは約 **89.7%縮小**。

### Representative

Unload Reset:

```text
repeat 1 p95 = 26.04s
repeat 2 p95 = 15.73s
repeat 1 / repeat 2 = 1.655×
difference = +65.5%
```

Process Restart:

```text
repeat 1 p95 = 17.38s
repeat 2 p95 = 15.83s
repeat 1 / repeat 2 = 1.099×
difference = +9.9%
```

Absolute Repeat Gapは約 **84.9%縮小**。

## 解釈

**Ollama Process / Service RestartによりChronological Latency Effectは大幅に減衰した。**

以前の不安定性にはProcess-local Ollama / Runtime Stateが大きく関与していた可能性が高い。

単にp95が下がっただけではない。

- Same Warmup Profiles
- Same Fixed 35 Request Sequence
- Repeat間のProfile Order Reversalも維持
- Intended Experimental ChangeはReset Boundaryのみ
- 両ProfileでRepeat Gapが大幅縮小

OriginalのStrong Prefix TailもRestart下では再現しなかった。

## Residual Behavior

RestartしてもLatencyは完全Deterministicではない。

Sparse Spike例:

- Representative Repeat 1, First Measured Request: 29.62s
- Synthetic Repeat 1, Request 26: 25.37s
- Representative Repeat 1, Request 29: 19.03s
- Synthetic Repeat 2, Request 19: 19.31s

ただし以前のようなSustained Prefix Patternではなく、Sparse Outlier。

したがってProcess-local Stateが以前のChronological Effectの大部分を説明する一方、全Varianceまで説明したとは限らない。

## Decision

- Representative-7は採用しない
- Validated Nimble Routing Thresholdは変更しない
- ComparableなCold-start / Reset Conditionが必要なLatency ExperimentではModel Unloadより **Process Restart** を優先する
- Fixed 35 CaseをFresh Quality Evidenceとして扱わない
- Normal Production RoutingでProcess Restartが必要という意味ではない。これはExperimental Reset Boundary

## Next Step

Original Warmup Questionは十分回答できた。

> Representative Warmupを増やすことがFixではなく、Stronger Process ResetによりChronological Artifactの大半が消える。

今後Latencyを続けるなら、Prefix Warmupではなく **Sparse Residual Spike** を対象にする。

CPU Governor変更やPage Cache Dropの前に、RequestごとのLightweight Host / Runtime Telemetryを追加する。

候補:

- CPU Frequency Summary
- System Load
- Process CPU / RSS
- Temperature（取得可能なら）
- Ollama Process Identity / Start Time

残る19–30s OutlierがHost Stateと相関するかを確認する。

Routing Objectiveを考えると、~15s Steady-stateまたはRare SpikeがOperationally許容できるなら、このFollow-upはOptional。
