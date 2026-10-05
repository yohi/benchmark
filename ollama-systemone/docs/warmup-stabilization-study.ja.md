# Warmup Stabilization Study

## 目的

Validated Nimble RunではLatency TailがPrefixへ強く集中していた。

- First 5 Mean = Remainderの1.907倍
- First 20 Mean = 1.554倍
- Position 21以降の>=1.5×Median Tail Event = 0

今回の実験では、**Current Generic Synthetic WarmupがRuntime Stabilizationとして弱すぎるか**を検証する。

Measured Workloadは完全固定し、Warmup Strategyだけを変更する。

## Profile

### `synthetic-1`

現在のBenchmark Warmup。

- Generic Synthetic System One Request 1件
- Warmup専用の2-choice Schema

### `representative-7`

7種類のRepresentative Warmup Request。

- 7 Routing Classを1件ずつ
- Measured Engineering Workloadと同じ7-class `route` Schema
- Measured Requestとは異なるTask Text

対象Class:

- implementation
- debug
- review
- research
- planning
- documentation
- deterministic

## Measured Workload

`datasets/latency-warmup-fixed-workload.jsonl`

Measured Workloadは **35 Request**。

- 7 Routing Class × 各5件
- 5 Scenario Family
- Scenario × Labelの全35 Pairを1件ずつ
- Scenario FamilyとLabelの双方が連続で偏らない順序

Caseは既に消費済みのSingle-policy Fresh Datasetから意図的に再利用している。

これは **Latency-only Experiment**。

35件を新しいQuality EvidenceやFresh Holdoutとして扱ってはいけない。

Warmup Task TextはMeasured Taskと完全に別にし、Measured RequestそのものをWarmupに使わない。

## Trial Order

Defaultでは各Profileを2 Repeat。

Temporal Driftを減らすためOrderを交互にする。

```text
repeat 1:
  synthetic-1
  representative-7

repeat 2:
  representative-7
  synthetic-1
```

全Trialの開始前にModelを明示的にUnloadする。

したがって4 TrialすべてでMeasured 35 Request Sequenceは完全同一、差分はWarmup Strategyだけ。

## 実行

```bash
uv run systemone-warmup-study \
  --model nimble \
  --dataset datasets/latency-warmup-fixed-workload.jsonl \
  --repeats 2
```

Output:

- `results/<RUN_ID>-warmup-study-details.jsonl`
- `results/<RUN_ID>-warmup-study.json`

## Primary Comparison

優先して見るMetric:

- First Request Latency
- First-5 Mean
- First-10 Mean
- First-20 Mean
- Request 20以降のMean
- p50
- p95
- Prefix-concentrated-tail Trial Count
- Late-tail Event Count

有効なWarmup StrategyならEarly Prefixが改善し、Steady-stateは大きく変わらないことが望ましい。

## 解釈

Runtime Stabilization改善のEvidence例:

```text
representative first-5 << synthetic first-5
representative first-20 ratio が1.0へ近づく
representative prefix-tail trial数が減る
after-20 latencyはほぼ同じ
```

Representative WarmupでEarly / Steady-state双方が改善する場合、単純なPrefix Stabilization以外のHost / Runtime Stateも影響している可能性がある。

Prefixが改善しない場合、以前のTailはWarmup回数や代表性だけでは解消しない可能性が高まる。

## Guardrail

このStudyだけで以下のSpecific Root Causeを証明しない。

- Model Loading
- CPU Governor Ramp-up
- Page Cache
- Scheduler State

検証するのは「より強いRepresentative WarmupでPrefix Behaviorが変わるか」だけ。

このExperimentからValidated Routing Thresholdを変更しない。

再利用35 CaseをIndependent Quality Validationとして扱わない。


## Stronger Reset Follow-up

最初のWarmup Studyでは、Warmup ProfileよりChronological Effectが強かった。

```text
repeat 1:
  両ProfileでLarge Latency Spike

repeat 2:
  両ProfileともSteady-state付近
```

全TrialでModel Unloadを行っていたため、UnloadだけではLatencyへ影響する全StateをResetできていない可能性がある。

そのためCLIにより強いReset Boundaryを追加する。

```bash
uv run systemone-warmup-study \
  --model nimble \
  --dataset datasets/latency-warmup-fixed-workload.jsonl \
  --repeats 2 \
  --reset-mode restart \
  --restart-command "sudo systemctl restart ollama" \
  --restart-wait 2
```

`--reset-mode restart` では各Trialで以下を行う。

1. Configured Restart Commandを `subprocess.run(..., check=True)` で実行
2. Configured Delayを待つ
3. `/api/tags` をProbeしてOllama Readyを確認
4. Warmup Profileを実行
5. 同一35 Request Measured Workloadを実行

HostごとにService Managementが異なるためRestart CommandはConfigurable。

SubprocessはCurrent Terminalを継承するため、Interactive ShellからStudyを起動した場合は `sudo systemctl restart ollama` のPassword Promptをそのまま使用できる。Unattended Runでは別途Non-interactive Restart Mechanismを用意する。

最初のRestart ExperimentではPage Cache Drop、CPU Governor変更などを同時に行わない。変更するReset Boundaryは1つだけにする。

### Interpretation

Process Restartで以前のRepeat 1 / Repeat 2差が消えるなら、Ollama / RuntimeのProcess-local State関与が強くなる。

Chronological Effectが残るなら、次はCPU Frequency / Governor、Memory / Page Cache Residency、Scheduler、ThermalなどHost-level Stateを調べる。
