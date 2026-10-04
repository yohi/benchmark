# Latency-tail Analysis

## 目的

`systemone-latency-tail` は、既存のSystem One `*-details.jsonl` からRequest順序とLatency TailをOffline分析する。

Overall p99だけがp50/p95より大幅に悪い場合に、以下を切り分ける。

- Startup / Prefix集中
- Run後半にも残るPersistent Tail
- Class / Scenario依存
- 散発的Runtime Spike

Ollamaの再実行は不要。

## 出力

### Prefix vs Remainder

最初のN Requestと残りを比較する。

Default:

```text
1, 5, 10, 20, 50
```

Explicit Warmupが完了した後でも、Measured Request序盤だけ遅いかを確認できる。

### Position Bucket

Request実行順を等分し、各Bucketについて以下を出す。

- Mean
- Median
- p90 / p95 / p99
- Min / Max

Early Region後に安定するのか、Run全体でTailが続くのかを見る。

### Top Outlier

High-latency Requestについて以下を出力する。

- Request Position
- Case ID
- Expected / Prediction
- Confidence
- Source / Scenario Metadata
- CPU Before / After
- Memory Delta

### Group Breakdown

以下の単位でLatency Summaryを比較する。

- Expected Label
- Source Family
- Scenario Family

Request順序とSemantic Task Shapeが偶然重なっていないかを確認する。

### Late-tail Diagnostic

指定Position以降で、Overall Medianの一定倍以上のLatencyを持つRequest数を数える。

Default:

```text
start position = 21
tail threshold = 1.5 × overall median
```

これによりPrefix TailとPersistent Late Tailを分ける。

## 実行例

Single-policy Fresh Validation Runを分析する。

```bash
uv run systemone-latency-tail \
  --details results/20261005-063902-details.jsonl \
  --model nimble \
  --prefixes 1,5,10,20,50 \
  --buckets 10 \
  --top 20 \
  --late-start 21 \
  --tail-multiplier 1.5 \
  --output results/20261005-063902-latency-tail.json
```

## 解釈上の注意

このAnalyzerが検出するのはRequest Order / Metadataとの相関であり、Root Causeの証明ではない。

例えばFirst BucketがWarmup-likeでも、原因候補は複数ある。

- Explicit Synthetic Warmup後にも続くModel / Runtime Initialization
- CPU Frequency / Governor
- Memory / Page Cache
- Thermal / Scheduler State
- Dataset序盤だけ異なるPrompt Shape
- その他Host / Runtime Effect

Current HeuristicではFirst Position Bucket MedianがLater Bucket Medianの中央値より25%以上遅い場合に `warmup-like` とする。

これはTriage SignalであってCausal Proofではない。

Tailが強くPrefixへ集中しているなら、次はWarmup Strategyを変えるか、同一Workload RepeatでRuntime StabilizationかTask Semanticsかを切り分ける。

Run後半にもLarge Spikeが残るなら、Warmup Policy変更より先にHost / Runtime Telemetryを追加すべき。
