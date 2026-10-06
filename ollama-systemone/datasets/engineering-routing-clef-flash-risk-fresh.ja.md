# Cloudflare Clef-Flash — Single-policy 1% Risk Fresh Holdout

## 目的

測定前に固定した以下のClef-Flash Policyだけを、新しいUntouched Holdoutで検証する。

```text
provider = cloudflare-clef-flash
model = clef-flash
endpoint model = @cf/cloudflare/clef-flash
threshold = 0.50
maximum accepted risk = 1%
confidence level = 95%
candidate policies = 1
```

threshold 0.50はこのDataset作成前のDevelopment Evidenceで選定済み。

このHoldoutを見てThreshold Search / Retuneを行い、同じDatasetをFresh Validation Evidenceと呼び続けてはいけない。

## 350件にする理由

Single Predeclared Policyなので、Accepted Error 0件の場合にOne-sided Exact 95% Binomial Upper Boundを1%以下へ置くには最低299 Accepted Decisionが必要。

Developmentではthreshold 0.50で:

```text
348 / 350 = 99.43% coverage
```

Fresh Coverageが約85.4%以上なら299 Acceptedを超えられるため350-caseとする。

これはSample Size DesignでありPASSを保証しない。

## Dataset Design

`engineering-routing-clef-flash-risk-fresh.jsonl` は350件。

| Label | Cases |
| --- | ---: |
| implementation | 50 |
| debug | 50 |
| review | 50 |
| research | 50 |
| planning | 50 |
| documentation | 50 |
| deterministic | 50 |
| **total** | **350** |

25 Engineering Scenario Family × 7 Routing Label × 2 Variant。

Scenario Family:

- DNSSEC rollover
- mTLS certificate rotation
- OpenAPI schema evolution
- Protocol Buffers evolution
- Prometheus cardinality
- OpenSearch shard allocation
- RabbitMQ quorum queues
- NATS JetStream
- Envoy circuit breaker / outlier detection
- Vault dynamic credentials
- AWS KMS key rotation
- SAML SSO
- SCIM provisioning
- WebSocket backpressure
- HTTP/3 QUIC fallback
- GraphQL DataLoader
- SQLite WAL
- MySQL replica lag
- DynamoDB hot partition
- CloudFront cache key
- Route 53 failover
- EKS IRSA
- Argo CD sync wave
- OpenTelemetry Collector
- Linux nftables

同一Scenario内ではTechnical Contextを近づけ、Requested Primary Actionだけを変える。

Keyword RecognitionではなくSemantic Routing Boundaryを検証する。

## Freshness Guarantee

Construction Check:

```text
rows = 350
unique task texts = 350
prior routing datasetsとのexact task overlap = 0
scenario families = 25
Nimble 350-case holdoutとのscenario-family overlap = 0
Strands 350-case holdoutとのscenario-family overlap = 0
```

Repository Testでも固定する。

## Frozen Policy Metadata

全Row:

```json
{
  "provider": "cloudflare-clef-flash",
  "model": "clef-flash",
  "endpoint_model": "@cf/cloudflare/clef-flash",
  "threshold": 0.50,
  "max_accepted_risk": 0.01,
  "confidence_level": 0.95,
  "candidate_count": 1,
  "multiple_testing_correction": "none-single-predeclared-policy"
}
```

## Validation Protocol

Development時と同じCloudflare Credentialを設定:

```bash
export CLOUDFLARE_ACCOUNT_ID='...'
export CLOUDFLARE_API_TOKEN='...'
```

Frozen PolicyをExactly Once実行:

```bash
uv run systemone-provider-bench \
  --providers configs/decision-providers.cloudflare.json \
  --only cloudflare-clef-flash \
  --dataset datasets/engineering-routing-clef-flash-risk-fresh.jsonl \
  --warmup 1 \
  --iterations 1 \
  --thresholds 0.50
```

Exactly One ThresholdでRisk Control:

```bash
uv run systemone-risk-control \
  --details results/<RUN_ID>-provider-details.jsonl \
  --model cloudflare-clef-flash \
  --thresholds 0.50 \
  --max-risk 0.01 \
  --confidence-level 0.95 \
  --output results/<RUN_ID>-clef-flash-single-policy-risk.json
```

DiagnosticとしてSelective Analysisを行ってもよい:

```bash
uv run systemone-selective \
  --details results/<RUN_ID>-provider-details.jsonl \
  --model cloudflare-clef-flash \
  --bins 10 \
  --output results/<RUN_ID>-clef-flash-selective.json
```

ただしその結果でthreshold 0.50を変更しない。

## Primary Gate

```text
one-sided exact 95% upper accepted-risk bound <= 1%
```

- **PASS** — Upper Risk Bound <= 1%
- **FAIL — Accepted Risk** — Upper Bound > 1%
- **INCONCLUSIVE — Sample Size** — Accepted Error 0だがAccepted数不足

Coverage / LatencyはSecondary。

## Secondary Observation

以下も記録する。

- Raw Routing Accuracy
- Class-level Confusion
- Client-observed p50/p95/p99
- Input-token Usage
- Estimated Neurons / Cost
- threshold 0.50 Coverage

Hosted Latency / Costが魅力的でもPrimary Quality Gateを緩めない。

## Result後

PASS:

- Current Benchmark Distributionに対するValidated Hosted Decision-layer Candidateとする
- Frozen PolicyとEvidenceをDurable Record化
- Production Distribution Shiftへの保証とは区別する

FAIL:

- Failureをそのまま保存
- 同HoldoutでRetuneしてFresh扱いしない
- Revised Clef Policyには別Untouched Holdoutが必要
