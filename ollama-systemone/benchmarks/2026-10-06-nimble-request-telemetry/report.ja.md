# Nimble Request Telemetry Sparse-spike Analysis — 2026-10-06

## 目的

Process RestartでBroad Startup / Chronological Artifactを除去した後に残っていた19〜31秒程度のSparse Outlierが、Host / Runtime Stateと相関するかを検証する。

このRun前にTelemetry Collectorを修正し、Ollama Daemonだけでなく全Descendant Runner Processを集計するようにした。

## Validation

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

Maximum Latency:

```text
15807.8ms
```

4 TrialすべてSpike 0。

| Trial | Requests | Median | Spikes |
| --- | ---: | ---: | ---: |
| 1 | 35 | 15.06s | 0 |
| 2 | 35 | 15.05s | 0 |
| 3 | 35 | 15.08s | 0 |
| 4 | 35 | 15.09s | 0 |

## Corrected Process-tree Telemetry

Collectorは以下を集計する。

- Ollama Daemon
- 全Descendant Process
- Aggregate CPU Time
- Aggregate RSS
- PID / Create Time Identity
- Named / Descendant Process Count

以前の不自然に低いProcess CPU Attributionはこれで修正された。

Corrected RunのMean Aggregate Ollama CPU Utilization:

```text
約398.7%
```

Multi-core CPU Inferenceとして妥当な値。

## Correlation

Corrected Stable Runでは強いLatency Correlationを示すMetricはない。

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

すべてWeak Correlation。

Spike 0件なのでSpike Group / Non-spike Group比較は成立しない。

## Interpretation

以前観測した19〜31秒のSparse Outlierは、**Corrected Telemetry Runでは安定再現しなかった**。

したがって以下を変更するEvidenceはない。

- CPU Governor
- Frequency Policy
- Thermal Policy
- Memory / Page Cache
- Ollama Process Lifecycle

これらの要因が将来Spikeを起こさないという意味ではない。

今回の結論は、

> Sparse Spikeを再現できなかったためHost / Runtime Telemetryとの因果Evidenceは得られず、Host Tuningへ進む根拠もない。

## Prior Evidenceとの関係

Evidence Chainは3つに分離できる。

1. **Model-unload Reset下のStrong Startup / Chronological Tail**
   - Reproducible
   - Process Restartで大幅減衰
   - Process-local Runtime State関与が強い

2. **Representative-7 vs Synthetic-1**
   - Consistent Advantageなし
   - 採用しない

3. **Process Restart後のSparse Residual Outlier**
   - Earlier Runでは出現
   - Corrected 140-request Telemetry Runでは非再現
   - Cause Inconclusive

## Decision

- Nimble Threshold 0.80維持
- Current / Default Warmup維持
- Representative-7は採用しない
- Controlled Latency ExperimentではProcess RestartをReset Boundaryとして使う
- CPU Governor / Page Cache / Thermal / Scheduler設定は変更しない
- Request Telemetry / Spike Analyzerは将来の再現時に使える状態で残す

## Next Step

Immediate Latency Experimentは不要。

Operational Workloadで>1.25×Median Outlierが反復する場合のみ、Host設定を変える前にTelemetry AnalyzerでEvidenceを取る。

Current Benchmark ObjectiveについてはLatency InvestigationをCloseしてよい。
