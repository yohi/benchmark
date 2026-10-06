# Clef-Flash Q4_K_M Local llama.cpp Benchmark

## Final status

**CLOSED / Interactive用途 STOP**

実測ではUntuned Q4_K_Mがp50 6.14s、`-t 24 -tb 24` ではp50 10.68sへ悪化した。

事前Stop Boundary `p50 > 3s` を満たしたため、350-case Full Developmentは意図的に実行せず調査終了。

最終判断は:

- `docs/systemone-decision-model-final-evaluation.ja.md`

## 目的

公開済みのClef-Flash GGUF Q4_K_Mを、CPU上の高速Local Decision Model候補として評価する。

```text
model source = ggml-org/Clef-Flash-GGUF
quantization = Q4_K_M
size = 6.49 GB
runtime = llama.cpp
API = /v1/systemone
```

これは小型Distill Modelではなく、Cloudflare Clef-Flash 9B系のQuantized版。

## なぜ試すか

既に測定したLocal Clef-Flash系はCPUで約17秒級で、同期Routingには遅すぎた。

ggml-org公開版:

```text
Q4_K_M = 6.49 GB
Q8_0   = 9.66 GB
BF16    = 18.2 GB
```

Q4_K_MはWeight Trafficを大幅に減らせるため、Memory Bandwidth依存が強いCPU InferenceではLatency改善が期待できる。

ただしSpeedupは実測前提。

## Runtime

Clef/System One対応済みの新しいllama.cppを使う。

Model CardではDecision Modelとして:

```text
POST /v1/systemone
```

を使用し、llama.cpp PR #29831によるSupportを要求している。

## Install / Start

```bash
curl -LsSf https://llama.app/install.sh | sh

llama serve \
  -hf ggml-org/Clef-Flash-GGUF:Q4_K_M \
  --no-mmproj \
  --host 127.0.0.1 \
  --port 8080
```

Prebuilt / Source Binaryなら:

```bash
llama-server \
  -hf ggml-org/Clef-Flash-GGUF:Q4_K_M \
  --no-mmproj \
  --host 127.0.0.1 \
  --port 8080
```

Provider Config:

```text
configs/decision-providers.llamacpp-clef-flash-q4.json
```

Server-bound CheckpointなのでRequest Bodyにはmodel fieldを送らない。

### `--no-mmproj` が必要な理由

`-hf` 使用時、現在のllama.cppはModel / Repository MetadataからMultimodal Projectorが存在すると判断するとmmprojを自動Downloadしようとする。

ClefのSystem One Text RoutingではProjectorは不要。llama.cpp公式docsでもClefのImage Inputは未対応。

現在の `ggml-org/Clef-Flash-GGUF` RepositoryにはBF16 / Q8_0 / Q4_K_M Model GGUFはあるが、`mmproj-*.gguf` は存在しない。

したがってLaunch時に:

```text
--no-mmproj
```

を明示する。

省略すると一部の現行llama.cpp Buildでは `mmproj-Clef-Flash-Q8_0.gguf` を自動取得しようとして、Q4_K_M Model Load前に失敗する。

## Manual Download Fallback

llama.cpp内蔵Hugging Face Downloaderが接続できない場合は、Hugging Face公式CLIでGGUFを先に取得し、Local Fileを直接serveする。

Benchmark環境を汚さずCLIを実行:

```bash
mkdir -p ~/.cache/clef-flash-q4

uvx --from huggingface_hub hf download \
  ggml-org/Clef-Flash-GGUF \
  Clef-Flash-Q4_K_M.gguf \
  --local-dir ~/.cache/clef-flash-q4
```

Slow Networkの場合:

```bash
export HF_HUB_DOWNLOAD_TIMEOUT=60
```

Download後。8080が既存Serviceで使用中の場合を避けるため、ここでは8081を使用する:

```bash
llama serve \
  -m ~/.cache/clef-flash-q4/Clef-Flash-Q4_K_M.gguf \
  --no-mmproj \
  --host 127.0.0.1 \
  --port 8081
```

Benchmark側へBase URLを指定:

```bash
export CLEF_LLAMA_BASE_URL='http://127.0.0.1:8081'
```

これでllama.cpp内蔵Downloaderを完全に回避しつつ、Inference Runtime / Benchmark条件は同一に保てる。

## Smoke

別Terminalでllama.cppを起動した状態で:

```bash
uv run systemone-provider-bench \
  --providers configs/decision-providers.llamacpp-clef-flash-q4.json \
  --only clef-flash-llamacpp-q4-k-m \
  --dataset datasets/smoke.jsonl \
  --warmup 1 \
  --iterations 1
```

## 350-case Development Comparison

Hosted Clef-Flash Developmentと同じ既使用Datasetを使う:

```bash
uv run systemone-provider-bench \
  --providers configs/decision-providers.llamacpp-clef-flash-q4.json \
  --only clef-flash-llamacpp-q4-k-m \
  --dataset datasets/engineering-routing-single-policy-risk-fresh.jsonl \
  --warmup 1 \
  --iterations 1 \
  --thresholds 0.50,0.60,0.70,0.80,0.90
```

これはDevelopment EvidenceでありFresh Validationではない。

## Offline Quality Analysis

Raw Qualityが十分なら:

```bash
uv run systemone-selective \
  --details results/<RUN_ID>-provider-details.jsonl \
  --model clef-flash-llamacpp-q4-k-m \
  --bins 10 \
  --output results/<RUN_ID>-clef-flash-q4-selective.json
```

Hosted Clef-Flashのthreshold 0.50をそのまま転用しない。

同じBase ModelでもQuantization / Runtime差でConfidence Scaleが変わり得るため、Q4専用にDevelopmentする。

## Primary Comparison

Hosted Development Record:

```text
raw accuracy = 350/350
p50 = 187.732 ms
p95 = 524.920 ms
threshold 0.50 coverage = 99.43%
```

比較軸:

1. Raw Routing Accuracy
2. Confidence / Selective-risk
3. p50 / p95 Latency
4. Memory Footprint
5. Hosted Layerを置き換えるほどLocal Pathが速いか

## Decision Guide

```text
p50 < 1s + 強いQuality:
  本命Local Candidate

p50 1-3s + 強いQuality:
  Local / Offline Fallbackとして有望

p50 > 3s:
  InteractiveではHosted Clef-Flashを置き換えにくい
```

Latency BandはEngineering Decision AidでありStatistical Validation Gateではない。

## References

- https://huggingface.co/ggml-org/Clef-Flash-GGUF
- https://github.com/ggml-org/llama.cpp
- https://github.com/ggml-org/llama.cpp/pull/29831
