# Cloudflare Clef-Flash Hosted Decision Benchmark

## 目的

Local Model調査を以下でCloseした後の、**Free / Cheap-cloud Decision Layer**候補としてCloudflare-hosted Clef-Flashを評価する。

```text
Nimble .80
  Validated Quality Reference
  Local CPU median 約15.2s

Strands 2B
  Local CPU median 約3.5s
  Fresh 1% Risk Gate FAIL
  Threshold Development後STOP

Laya Multilingual
  Local CPU median 約0.36s
  Routing Quality不足
  Reject
```

Clef-FlashはLocal CPU代替としてではなく、Latency-criticalなHosted Decision Modelとして評価する。

## Cloudflare Model

Workers AI:

```text
@cf/cloudflare/clef-flash
```

Request Model Selector:

```text
clef-flash
```

CloudflareはClef / Clef-FlashをSystem One互換として公開している。

Native REST endpoint:

```text
POST https://api.cloudflare.com/client/v4/accounts/<ACCOUNT_ID>/ai/run/@cf/cloudflare/clef-flash
```

Cloudflare REST ResponseではModel OutputがTop-level `result` 配下に入るため、Provider Adapterへ `response_path` を追加する。

## Secret管理

Account ID / API TokenをGitへ保存しない。

Committed Config:

```text
configs/decision-providers.cloudflare.json
```

必要なEnvironment Variable:

```bash
export CLOUDFLARE_ACCOUNT_ID='...'
export CLOUDFLARE_API_TOKEN='...'
```

Custom API Tokenを作る場合、Cloudflare REST DocsではWorkers AI Read / Workers AI Edit Permissionが必要。

Environment Variable未設定の場合、Request前にConfig LoaderをFailさせる。

## Pricing

2026-10-06時点のCloudflare公式価格:

```text
Clef-Flash:
  $0.09 / 1M input tokens
  8,182 Neurons / 1M input tokens

Workers AI Free Allocation:
  10,000 Neurons / day
```

換算するとClef-Flashだけを使う場合のFree Allocationは概算:

```text
約1.22M input tokens / day
```

ただし同一Accountの他Workers AI Usageも10,000 Neuronsを共有する。

350-case Benchmarkが無料枠内と事前断定せず、実際のUsageを測る。

Provider BenchmarkはResponse `usage` のNumeric FieldをHTTP Request単位でAggregateする。

## Cloudflare公開Latencyとの区別

Cloudflare Launch Benchmark:

```text
Clef-Flash median = 38.8ms
Clef-Flash p95    = 122.4ms
```

これは本Projectの実測値ではない。

今回測るLatencyはAI Agent PCからCloudflare REST APIまでのClient-observed End-to-endであり、

- Internet RTT
- API Layer
- Inference
- Queueing

を含む。

## Development Dataset

```text
datasets/engineering-routing-single-policy-risk-fresh.jsonl
```

この350-caseは既使用EvidenceなのでProvider Development / Comparisonに利用できる。

Fresh Validationには使わない。

Nimble / Laya / Strands比較と同じDatasetを使うことでQualityを直接比較する。

## Smoke Test

```bash
uv run systemone-provider-bench \
  --providers configs/decision-providers.cloudflare.json \
  --only cloudflare-clef-flash \
  --dataset datasets/smoke.jsonl \
  --warmup 1 \
  --iterations 1
```

確認項目:

- Auth成功
- Cloudflare `result` Envelopeをunwrapできる
- System One Answerを既存Parserで処理できる
- Latency取得
- Usageが返る場合はUsage取得

## 350-case Development

```bash
uv run systemone-provider-bench \
  --providers configs/decision-providers.cloudflare.json \
  --only cloudflare-clef-flash \
  --dataset datasets/engineering-routing-single-policy-risk-fresh.jsonl \
  --warmup 1 \
  --iterations 1 \
  --thresholds 0.50,0.60,0.70,0.80,0.90
```

Primary Metrics:

1. Raw Routing Accuracy
2. Class別Error
3. Confidence Ranking / Selective Risk
4. Zero / Near-zero Accepted Error時のCoverage
5. Client-observed p50 / p95 / p99
6. Input Token / Neuron Usage / Estimated Cost

## Selective Analysis

Raw Qualityが十分な場合:

```bash
uv run systemone-selective \
  --details results/<RUN_ID>-provider-details.jsonl \
  --model cloudflare-clef-flash \
  --bins 10 \
  --output results/<RUN_ID>-clef-flash-selective.json
```

Nimble / Strands Thresholdを流用しない。

Clef-Flash Confidenceは独立したScaleとして扱う。

## Threshold Development

Selective Qualityが十分な場合のみ:

```bash
uv run systemone-risk-control \
  --details results/<RUN_ID>-provider-details.jsonl \
  --model cloudflare-clef-flash \
  --thresholds 0.50:0.99:0.01 \
  --max-risk 0.01 \
  --confidence-level 0.95 \
  --output results/<RUN_ID>-clef-flash-risk-development.json
```

これはDevelopment Evidence。

Candidate Policyを決めたら、新Fresh Holdoutを見る前にFreezeする。

## Development Gate

Fresh Holdoutへ進める条件:

```text
Quality:
  <=1% Accepted-riskを狙えるOperating Pointがある

Coverage:
  Development Evidenceで >=85%

Latency:
  Strands Local p50 約3.5sより十分速い

Cost:
  想定するFree / Cheap-cloud Budgetと整合
```

Cloudflare Vendor Benchmarkの38.8ms再現自体はRequirementではない。

## Cost計算

Summaryに `input_tokens` がある場合:

```text
estimated USD
  = input_tokens / 1,000,000 * 0.09

estimated Neurons
  = input_tokens / 1,000,000 * 8,182

free allocation share
  = estimated Neurons / 10,000
```

Account全体のAuthoritative Neuron UsageはCloudflare Dashboardで確認する。

## References

- https://developers.cloudflare.com/changelog/post/2026-10-01-clef-workers-ai/
- https://developers.cloudflare.com/workers-ai/get-started/rest-api/
- https://developers.cloudflare.com/workers-ai/platform/pricing/
- https://blog.cloudflare.com/clef-decision-models/
