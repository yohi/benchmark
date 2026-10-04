# Single-policy 1% Risk Fresh Holdout

## 目的

測定前に以下へ固定した1つのPolicyだけを、新しいUntouched Validation Setで検証する。

```text
model = nimble
confidence threshold = 0.80
maximum accepted risk = 1%
confidence level = 95%
candidate policies = 1
```

前回のDevelopment-time Threshold Searchとは異なり、今回はThreshold Gridを探索しない。

確認するのは1点だけ。

> 事前固定したthreshold 0.80が、新しいEvidenceでAccepted Risk 1% Requirementを満たすか。

## 350件にする理由

Single Predeclared Policyなので、Threshold候補間のMultiple-testing Penaltyはない。

95% ConfidenceでOne-sided Exact Binomial Upper Boundを1%以下にするには、Accepted Errorが0件の場合でも最低 **299 Accepted Decision** が必要。

Development Poolではthreshold 0.80のCoverageが88.29%だった。

Fresh Coverageが約85.4%以上を維持すれば299 Acceptedを超えられるよう、Holdout Sizeを350件にした。

これはSample Size Designであり、PolicyがPassすることを保証するものではない。

## Dataset Design

`engineering-routing-single-policy-risk-fresh.jsonl` は **350件**。

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

25個のEngineering Scenario Familyを使い、各Scenarioから7 Routing Label × 2 Variantを作成している。

Scenario Familyには以下を含む。

- coding-agent context isolation
- retry / convergence control
- checkpoint / replay safety
- MCP schema compatibility
- OpenTelemetry agent tracing
- Git worktree isolation
- Django idempotency
- DRF query performance
- Python TaskGroup error handling
- Pydantic migration
- PostgreSQL locks
- Redis leases
- AWS Lambda latency
- Step Functions retry behavior
- ECS / ALB latency
- Cloudflare Worker CPU budget
- GitHub Actions matrix handling
- Bitbucket cache behavior
- Nexus index snapshots
- Justice artifact provenance
- OCTG provider routing
- benchmark confidence analysis
- uv entrypoint behavior
- Pyright monorepo resolution
- API schema compatibility

同じTechnical Contextの中でRequested Primary Actionだけを変えるPaired-action構成にしている。

これにより、既存Task Textの言い換えではなくRouting Boundaryそのものを検証する。

## Frozen Policy Metadata

全Rowに以下を記録する。

```json
{
  "model": "nimble",
  "threshold": 0.80,
  "max_accepted_risk": 0.01,
  "confidence_level": 0.95,
  "candidate_count": 1,
  "multiple_testing_correction": "none-single-predeclared-policy"
}
```

Model Outputを見た後でこの値を変更し、同じDatasetをFresh Validation Evidenceと呼び続けてはいけない。

## Evaluation Protocol

### 1. Fresh Nimble Decisionを生成

```bash
uv run systemone-bench \
  --models nimble \
  --dataset datasets/engineering-routing-single-policy-risk-fresh.jsonl \
  --warmup 1 \
  --iterations 1 \
  --cache-reset unload \
  --thresholds 0.80
```

### 2. 事前固定Policyを1つだけ評価

```bash
uv run systemone-risk-control \
  --details results/<RUN_ID>-details.jsonl \
  --model nimble \
  --thresholds 0.80 \
  --max-risk 0.01 \
  --confidence-level 0.95 \
  --output results/<RUN_ID>-single-policy-risk.json
```

Threshold Gridには0.80しか含めないためCandidate Countは1。

Pointwise Alpha = Family Alphaとなり、Threshold Search由来のMultiple-testing Penaltyは発生しない。

## Pass / Fail

Primary Statistical Gate:

```text
one-sided exact upper accepted-risk bound <= 1%
```

Accepted Error 0件でも299 Accepted Decisionが必要。

したがって判定は以下。

- **PASS**: Upper Risk Bound <= 1%
- **FAIL — Accepted Risk**: Accepted Error発生などによりBound > 1%
- **INCONCLUSIVE — Sample Size**: Accepted Error 0件だがAccepted Decisionが不足しBoundを1%以下にできない

CoverageはSecondary Metric。

このHoldoutを見た後でCoverageを改善するため1% Targetを緩めてはいけない。

## Methodology

これはSingle-policy Validation Experimentであり、新しいPolicy Development Searchではない。

Threshold 0.80がFailした場合:

- FailureをValidation Evidenceとして保存
- 同じDataset上でRetuneしてFresh扱いしない
- 後続PolicyがこのDatasetを利用した時点でDevelopment Evidenceへ位置付けを変更する

Threshold 0.80がPassした場合:

- 前回Development Analysisより強いEvidenceになる
- それでも将来Production Distribution ShiftへのGuaranteeではない
- Production Monitoringおよび追加Independent Evidenceは引き続き必要
