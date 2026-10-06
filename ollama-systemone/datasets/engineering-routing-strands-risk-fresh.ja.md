# Strands Decider 2B v21 — Single-policy 1% Risk Fresh Holdout

## 目的

測定前に以下へ固定した1つのPolicyだけを新しいUntouched Holdoutで検証する。

```text
provider = strands-decider-2b-v21
checkpoint = StrandsAgents/strands-decider-2B-hobson-v21
confidence threshold = 0.50
maximum accepted risk = 1%
confidence level = 95%
candidate policies = 1
```

threshold 0.50は前段の350-case Development比較で選定済み。

このFresh HoldoutではThreshold Search / Retuneをしない。

確認する問いは1点だけ。

> 事前固定したStrands threshold 0.50が、新しいEvidenceでもAccepted Risk 1% Requirementを満たすか。

## 350件にする理由

Single Predeclared PolicyなのでThreshold Search由来のMultiple-testing Penaltyはない。

Accepted Error 0件の場合、One-sided Exact 95% Binomial Upper Boundを1%以下にするには最低299 Accepted Decisionが必要。

Development Coverageはthreshold 0.50で約98.3%。

Fresh Coverageが約85.4%以上なら299 Acceptedを超えられるため、350-case Holdoutとする。

これはSample Size Designであり、PASSを保証するものではない。

## Dataset Design

`engineering-routing-strands-risk-fresh.jsonl` は350件。

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

25個の新しいEngineering Scenario Familyを使い、各Familyから7 Routing Label × 2 Variantを作る。

Scenario Family:

- Kubernetes HPA
- Terraform remote state
- RDS failover
- S3 multipart upload
- SQS DLQ redrive
- Kafka consumer rebalance
- gRPC deadline propagation
- Nginx reverse proxy
- OIDC refresh-token rotation
- WebAuthn/passkey
- systemd socket activation
- Tailscale ACL/grants
- Docker BuildKit cache
- Celery retry/acknowledgement
- PostgreSQL logical replication
- Cloudflare D1 migration
- Cloudflare R2 lifecycle
- API Gateway authorizer cache
- AWS IAM permission boundary
- Amazon Bedrock model routing
- Vercel/Next.js cache revalidation
- Next.js Server Actions
- Supabase RLS
- GitHub repository ruleset
- Linux cgroup v2

同一Family内ではTechnical Contextを近づけたままRequested Primary Actionだけを変える。

Keyword RecognitionではなくRouting Boundaryを検証する。

## Freshness Check

```text
350 rows
350 unique task texts
25 scenario families
prior routing datasetsとのexact task overlap = 0
previous Nimble 350-case holdoutとのscenario-family overlap = 0
```

Repository Testでもこれを固定する。

## Frozen Policy Metadata

全Rowに以下を保存する。

```json
{
  "provider": "strands-decider-2b-v21",
  "model": "strands-decider-2b-v21",
  "checkpoint": "StrandsAgents/strands-decider-2B-hobson-v21",
  "threshold": 0.50,
  "max_accepted_risk": 0.01,
  "confidence_level": 0.95,
  "candidate_count": 1,
  "multiple_testing_correction": "none-single-predeclared-policy"
}
```

Outputを見た後でこの値を変更し、同じDatasetをFresh Validation Evidenceと呼び続けてはいけない。

## Evaluation Protocol

Developmentと同じCheckpoint / RuntimeでStrands Serverを起動する。

Benchmark:

```bash
uv run systemone-provider-bench \
  --providers configs/decision-providers.local.json \
  --only strands-decider-2b-v21 \
  --dataset datasets/engineering-routing-strands-risk-fresh.jsonl \
  --warmup 1 \
  --iterations 1 \
  --thresholds 0.50
```

Frozen Policyを1つだけ評価:

```bash
uv run systemone-risk-control \
  --details results/<RUN_ID>-provider-details.jsonl \
  --model strands-decider-2b-v21 \
  --thresholds 0.50 \
  --max-risk 0.01 \
  --confidence-level 0.95 \
  --output results/<RUN_ID>-strands-single-policy-risk.json
```

DiagnosticとしてSelective Analysisを実施してもよい。

```bash
uv run systemone-selective \
  --details results/<RUN_ID>-provider-details.jsonl \
  --model strands-decider-2b-v21 \
  --bins 10 \
  --output results/<RUN_ID>-strands-selective.json
```

ただしSelective Resultを見てthreshold 0.50を変更しない。

## Pass / Fail

Primary Gate:

```text
one-sided exact upper accepted-risk bound <= 1%
```

- **PASS** — Upper Risk Bound <= 1%
- **FAIL — Accepted Risk** — Accepted Error発生などでBound > 1%
- **INCONCLUSIVE — Sample Size** — Accepted Error 0件だがAccepted Decision不足

Coverage / LatencyはSecondary。

## Result後

PASSなら、Current Engineering-routing Benchmark ObjectiveにおけるValidated Local Replacement CandidateとしてStrandsを扱える。

FAILならFailureをValidation Evidenceとして保存する。

このHoldout上でRetuneしてFresh扱いしない。
