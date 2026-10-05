# Request Telemetry / Sparse-spike Analysis

## 目的

Process Restart Warmup Studyによって以前のChronological / Prefix Artifactの大部分は消えたが、19〜30秒程度のSparse Outlierは残った。

このFollow-upではWarmupを再調整しない。

Measured RequestごとにLightweight Host / Runtime Contextを記録し、Sparse Latency Spikeと観測可能なRuntime Stateに相関があるかを見る。

## Opt-in Telemetry

Request TelemetryはDefault Off。

Diagnostic Runでのみ有効化する。

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

Telemetry SamplingはMeasured HTTP Request Timerの外側。

```text
Before Telemetry Capture
↓
Request Timer Start
↓
POST /v1/systemone
↓
Request Timer Stop
↓
After Telemetry Capture
```

したがってTelemetry収集時間そのものは `latency_ms` に含まれない。

ただしTelemetry Captureが後続Host Stateへわずかに影響する可能性はあるため、Headline Latency比較ではなくDiagnostic Run専用とする。

## Recorded Field

### CPU Frequency

Request Before / After:

- Available CPUのCurrent MHz Mean
- Min
- Max

### System Load

Before / After:

- 1-minute Load Average
- 5-minute
- 15-minute

### Temperature

`psutil.sensors_temperatures()` が利用可能な場合:

- Maximum Sensor Temperature
- Chip / Label単位Reading

未対応環境ではRunを失敗させずTemperatureをUnavailableとして扱う。

### Ollama Process State

Arbitrary Command-line SubstringではなくProcess / Executable NameでOllama Processを識別する。

これにより `ollama-systemone` のようなRepository PathによるFalse Positiveを避ける。

Before / After:

- Ollama PID
- Process Create Time
- Aggregate RSS
- Aggregate CPU Time

Derived:

- Measured Request区間のOllama CPU Percent
- Ollama RSS Delta
- Request中にOllama Process Identity Setが変化したか

CPU PercentはAggregate Multi-core CPU Timeなので100%を超えることがある。

### System Memory

- Request Before / AfterのAvailable Bytes

## Sparse-spike Analyzer

Warmup Study Details JSONLをOffline Analyzeする。

```bash
uv run systemone-spike-analysis \
  --details results/<RUN_ID>-warmup-study-details.jsonl \
  --spike-multiplier 1.25 \
  --top 20 \
  --output results/<RUN_ID>-spike-analysis.json
```

Default Spike Definition:

```text
latency >= 1.25 × median latency
```

Median約15.2秒ならThresholdは約19秒となり、Restart Studyで残ったResidual Spike Rangeと一致する。

## Analyzer Output

各Telemetry Metricについて以下を出す。

- Usable Observation Count
- Mean / Median / Min / Max
- LatencyとのPearson Correlation
- Spike Group Summary
- Non-spike Group Summary

またHigh-latency RequestをTelemetry ValuesとProcess Identity Change Flag付きで列挙する。

## Interpretation Guardrail

CorrelationはExploratory EvidenceでありCausal Proofではない。

- High Loadは原因ではなく結果の可能性がある
- TemperatureはSlow-movingでIndividual Request原因を示さない可能性がある
- CPU FrequencyはSnapshotでありFull Traceではない
- RSSはLatency原因ではなくModel / Runtime Allocationを反映している可能性がある
- Spike件数が少ない場合Correlationは不安定

Analyzerは、次にどのControlled Follow-upを行う価値があるか決めるために使う。

例:

- Spikeが一貫してLow CPU Frequencyと一致 → Governor / Frequency調査
- Process Identity Changeと一致 → Runtime / Runner Lifecycle調査
- High Temperatureと一致 → Thermal Throttling調査
- Telemetry MetricでSpikeを分離できない → 推測でHost TuningせずProfiler / Runtime Traceを検討

## Scope

このFollow-upでは以下を変更しない。

- Validated Nimble Threshold
- Default Benchmark Warmup
- Controlled Latency ExperimentでのProcess Restart Reset Boundary
- Quality Evidence

Fixed 35 Request WorkloadはLatency-only Evidenceのまま。
