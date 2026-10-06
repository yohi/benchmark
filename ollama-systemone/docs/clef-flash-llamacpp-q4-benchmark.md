# Clef-Flash Q4_K_M local llama.cpp benchmark

## Purpose

Evaluate the public quantized local Clef-Flash build as a lower-latency CPU alternative to the previously measured Ollama Clef-Flash Q8_0 path.

Candidate:

```text
model source = ggml-org/Clef-Flash-GGUF
quantization = Q4_K_M
size = 6.49 GB
runtime = llama.cpp
API = /v1/systemone
```

This is the same Cloudflare Clef-Flash 9B model family, quantized for llama.cpp. It is not a smaller distilled model.

## Why this candidate

The previously tested local Clef-Flash path used a much larger Q8-style local footprint and was too slow for synchronous routing on the current CPU host.

Q4_K_M reduces model weight size substantially:

```text
Q4_K_M = 6.49 GB
Q8_0   = 9.66 GB
BF16    = 18.2 GB
```

On a CPU-bound workload, the lower memory bandwidth demand may materially reduce request latency.

This must be measured; no speedup is assumed in advance.

## Runtime requirement

Use a recent llama.cpp build that includes Clef/System One support.

The model card specifies that Clef-Flash is a decision model exposed through:

```text
POST /v1/systemone
```

and references llama.cpp support introduced by PR #29831.

## Install / start

Recommended current launcher:

```bash
curl -LsSf https://llama.app/install.sh | sh

llama serve \
  -hf ggml-org/Clef-Flash-GGUF:Q4_K_M \
  --no-mmproj \
  --host 127.0.0.1 \
  --port 8080
```

Equivalent prebuilt/source binary form:

```bash
llama-server \
  -hf ggml-org/Clef-Flash-GGUF:Q4_K_M \
  --no-mmproj \
  --host 127.0.0.1 \
  --port 8080
```

The llama.cpp server exposes:

```text
GET  /health
POST /v1/systemone
```

The committed provider config points at those endpoints:

```text
configs/decision-providers.llamacpp-clef-flash-q4.json
```

No model identifier is sent in the request because the server is already bound to the selected checkpoint.

### Why `--no-mmproj`

When `-hf` is used, recent llama.cpp builds automatically try to download a multimodal projector when model/repository metadata suggests one is available.

For Clef/System One text routing, the projector is not required. llama.cpp documents that image input is not supported for Clef in this endpoint path.

The current `ggml-org/Clef-Flash-GGUF` repository contains the BF16, Q8_0, and Q4_K_M model GGUFs but no `mmproj-*.gguf` file.

Therefore the benchmark launch command explicitly disables projector auto-download:

```text
--no-mmproj
```

If omitted, some current llama.cpp builds may attempt to fetch `mmproj-Clef-Flash-Q8_0.gguf` and fail before loading the Q4_K_M model.

## Manual download fallback

If llama.cpp's built-in Hugging Face downloader cannot establish a connection, download the GGUF separately with Hugging Face's official CLI and serve the local file.

Install/run the CLI without modifying the benchmark environment:

```bash
mkdir -p ~/.cache/clef-flash-q4

uvx --from huggingface_hub hf download \
  ggml-org/Clef-Flash-GGUF \
  Clef-Flash-Q4_K_M.gguf \
  --local-dir ~/.cache/clef-flash-q4
```

If the network is slow, increase the Hugging Face download timeout:

```bash
export HF_HUB_DOWNLOAD_TIMEOUT=60
```

Then start llama.cpp from the local file:

```bash
llama serve \
  -m ~/.cache/clef-flash-q4/Clef-Flash-Q4_K_M.gguf \
  --no-mmproj \
  --host 127.0.0.1 \
  --port 8080
```

This bypasses llama.cpp's model downloader entirely while keeping the inference runtime and benchmark conditions unchanged.

## Smoke

With llama.cpp running in another terminal:

```bash
uv run systemone-provider-bench \
  --providers configs/decision-providers.llamacpp-clef-flash-q4.json \
  --only clef-flash-llamacpp-q4-k-m \
  --dataset datasets/smoke.jsonl \
  --warmup 1 \
  --iterations 1
```

## Development comparison

Use the same already-consumed 350-case dataset used for the hosted Clef-Flash development comparison:

```bash
uv run systemone-provider-bench \
  --providers configs/decision-providers.llamacpp-clef-flash-q4.json \
  --only clef-flash-llamacpp-q4-k-m \
  --dataset datasets/engineering-routing-single-policy-risk-fresh.jsonl \
  --warmup 1 \
  --iterations 1 \
  --thresholds 0.50,0.60,0.70,0.80,0.90
```

This dataset is development evidence only.

## Offline quality analysis

If raw quality is competitive:

```bash
uv run systemone-selective \
  --details results/<RUN_ID>-provider-details.jsonl \
  --model clef-flash-llamacpp-q4-k-m \
  --bins 10 \
  --output results/<RUN_ID>-clef-flash-q4-selective.json
```

Then inspect a single candidate only after development evidence supports freezing one.

Do not assume the hosted Clef-Flash threshold 0.50 transfers unchanged across quantization/runtime. Quantization can alter confidence values even when class predictions remain stable.

## Primary comparison

Compare against the recorded hosted development run:

```text
hosted Clef-Flash development:
  raw accuracy = 350/350
  p50 = 187.732 ms
  p95 = 524.920 ms
  threshold 0.50 coverage = 99.43%
```

Also compare against the earlier local Clef-Flash/Ollama observation.

Primary decision axes:

1. raw routing accuracy
2. confidence/selective-risk behavior
3. p50/p95 latency
4. memory footprint
5. whether the local path is fast enough to justify replacing the validated hosted layer

## Decision guidance

A local Q4 result is interesting only if it preserves Clef-Flash quality while reducing local CPU latency enough to be operationally useful.

Suggested interpretation:

```text
< 1s p50 with strong quality:
  serious local candidate

1-3s p50 with strong quality:
  potentially useful as local/offline fallback

> 3s p50:
  unlikely to displace hosted Clef-Flash for interactive routing
```

These latency bands are engineering decision aids, not statistical validation thresholds.

## References

- https://huggingface.co/ggml-org/Clef-Flash-GGUF
- https://github.com/ggml-org/llama.cpp
- https://github.com/ggml-org/llama.cpp/pull/29831
