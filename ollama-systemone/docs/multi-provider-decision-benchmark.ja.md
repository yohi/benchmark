# Multi-provider Decision Model比較

## 目的

同一Engineering Routing Datasetで、Jev / System One互換Decision Providerを比較する。

Benchmark ProjectへLaya / Strands固有SDKやHeavy Runtime Dependencyは入れない。

BenchmarkはHTTP `POST /v1/systemone` のみを使う。

初期候補:

- Ollama Nimble 9B
- Laya Multilingual
- Strands Decider 2B v21

既存350-case `engineering-routing-single-policy-risk-fresh.jsonl` は、Nimble Validationですでに消費済み。

したがって今回このDatasetは **Provider選定用Development Evidence** としてのみ使う。

ここでProvider / Thresholdを選んだ後、新しいFresh HoldoutでValidationする。

## HTTP Adapterにする理由

Runtime Stackが異なる。

```text
Ollama
Laya + PyTorch / Transformers
Strands + PyTorch / Transformers + Custom Head
```

すべてをBenchmark venvへ入れるとDependency ConflictやRuntime差がBenchmark Harnessへ侵入する。

そこで、

```text
Provider Runtime
    ↓
POST /v1/systemone
    ↓
systemone-provider-bench
    ↓
Common Details JSONL
    ↓
systemone-selective
systemone-risk-control
```

とする。

Detailsの `model` FieldにはProvider Aliasを入れるため、既存Offline Analyzerを変更せず利用できる。

## Provider Config

```text
configs/decision-providers.local.json
```

Default Example:

```text
nimble
  127.0.0.1:11434
  model=nimble

laya-multilingual
  127.0.0.1:8001
  model=multilingual

strands-decider-2b-v21
  127.0.0.1:8002
  Server起動時にCheckpoint固定
```

## Laya Multilingual CPU Server

Benchmark Environmentとは別venvにする。

```bash
python3 -m venv ~/.venvs/laya
source ~/.venvs/laya/bin/activate
pip install "laya[serve]"

LAYA_DEVICE=cpu \
LAYA_PORT=8001 \
LAYA_DEFAULT_MODEL=multilingual \
LAYA_MODELS=multilingual \
LAYA_PRELOAD=1 \
LAYA_THREADS=24 \
laya-serve
```

Benchmark Requestでは `model=multilingual` を明示し、Auto Language Routerに依存しない。

今回のDatasetはJapanese-first + English Technical Termsなので、最初のLaya CandidateはMultilingual Checkpointとする。

Nimbleの `confidence >= 0.80` をLayaへ流用してはいけない。Confidence ScaleはProviderごとに別物としてValidationする。

## Strands Decider 2B v21 CPU Server

別venvで起動。

Current Reference Checkpoint:

```text
StrandsAgents/strands-decider-2B-hobson-v21
```

Example:

```bash
python3.12 -m venv ~/.venvs/strands-decider
source ~/.venvs/strands-decider/bin/activate

pip install torch==2.7.1 \
  --index-url https://download.pytorch.org/whl/cpu
pip install "strands-decider[cpu]"

strands-decider serve \
  StrandsAgents/strands-decider-2B-hobson-v21 \
  --device cpu \
  --port 8002
```

PyPI Versionがまだ `cpu` Extraを公開していない場合は、Strands UpstreamのInference Guideに従ってCurrent Source CheckoutをInstallする。

CPU Serve自体はSupported。

CheckpointはServer Start時にBindされるためSample ConfigではRequest `model` を送らない。

## Smoke

```bash
uv run systemone-provider-bench \
  --providers configs/decision-providers.local.json \
  --dataset datasets/smoke.jsonl \
  --warmup 1 \
  --iterations 1
```

Single Provider:

```bash
uv run systemone-provider-bench \
  --providers configs/decision-providers.local.json \
  --only laya-multilingual \
  --dataset datasets/smoke.jsonl
```

## 350-case Development Comparison

```bash
uv run systemone-provider-bench \
  --providers configs/decision-providers.local.json \
  --dataset datasets/engineering-routing-single-policy-risk-fresh.jsonl \
  --warmup 1 \
  --iterations 1 \
  --thresholds 0.50,0.60,0.70,0.80,0.90
```

Latency Headlineを取る場合はProviderを同時常駐させず、`--only` で**1 Providerずつ**測る。

他Provider RuntimeのMemory ResidencyやBackground StateをLatencyへ混ぜないため。

Quality比較だけなら同じRunで全Providerへ同じCaseを流してよい。

## Output

```text
results/<RUN_ID>-provider-details.jsonl
results/<RUN_ID>-provider-summary.json
```

Providerごとに:

- mean / p50 / p90 / p95 / p99
- RPS
- Raw Accuracy
- Mean Confidence
- Threshold Coverage / Accepted Accuracy / Escalation
- Expected Label別Accuracy
- Confusion Matrix

を出す。

## Selective Confidence

Provider Confidenceを同じ尺度として直接比較しない。

各Providerを独立評価する。

```bash
uv run systemone-selective \
  --details results/<RUN_ID>-provider-details.jsonl \
  --model laya-multilingual \
  --bins 10 \
  --output results/<RUN_ID>-laya-selective.json

uv run systemone-selective \
  --details results/<RUN_ID>-provider-details.jsonl \
  --model strands-decider-2b-v21 \
  --bins 10 \
  --output results/<RUN_ID>-strands-selective.json
```

優先順位:

```text
Raw Accuracy
↓
ConfidenceがErrorを低位へRankできるか
↓
Zero / Near-zero Accepted ErrorでCoverageが取れるか
↓
Latency
```

## Risk-control Development

Threshold SearchはProvider別。

```bash
uv run systemone-risk-control \
  --details results/<RUN_ID>-provider-details.jsonl \
  --model laya-multilingual \
  --thresholds 0.50:0.99:0.01 \
  --max-risk 0.01 \
  --confidence-level 0.95 \
  --output results/<RUN_ID>-laya-risk-development.json
```

この350件でThresholdをSearchした時点で、そのProvider PolicyについてこのDatasetはDevelopment Evidence。

Fresh Validationには使わない。

## Selection Rule

最速モデルを無条件採用しない。

```text
1 Raw Accuracy
2 Selective Ranking / Accepted Error
3 Coverage
4 Latency
5 Operational Complexity
```

100倍速くてもErrorをConfidenceで分離できなければ、Validated Nimble Policyの置換にはならない。

## Provider選定後

WinnerとPolicyをFreezeしてから新しいFresh Holdoutを作る。

Predeclare:

- Provider / Checkpoint
- Threshold
- Maximum Accepted Risk
- Confidence Level

そのPolicyを一度だけ評価し、既存Risk-control Gateを適用する。

ここを通って初めて "Validated Nimble Replacement" とする。

## 想定する最終形

Small Local Candidateが成功:

```text
deterministic rules
      ↓
Laya / Strands
      ↓ uncertain
free/cheap cloud decision
      ↓
stronger LLM
```

Small CandidateがFastだがQuality不足なら、速度だけを理由にNimbleを置換しない。

必要ならCascadeとして別途評価する。

Local Candidateが全滅なら、Cloudflare Clef-Flash等のHosted Decision ModelをLayer 2として評価する。
