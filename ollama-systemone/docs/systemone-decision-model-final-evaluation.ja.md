# System One Decision Model 最終評価 — 2026-10-06

## Executive Summary

Engineering Routing向けSystem One / Decision Model探索を終了する。

最終採用Candidateは:

```text
Cloudflare hosted Clef-Flash
threshold = 0.50
```

比較した候補の中で唯一、

1. Untouched Fresh HoldoutでRaw Accuracy 100%
2. Single Predeclared Policyの95% One-sided Exact Accepted-risk Upper Bound <= 1%
3. Interactive Routingに十分なSub-second Median Latency

を同時に満たした。

最終推奨Routing Architecture:

```text
Tier 0: deterministic rule / exact local logic
    ↓ unresolved
Tier 1: Cloudflare hosted Clef-Flash
        confidence >= 0.50 → accept
    ↓ confidence < 0.50 / unavailable / quota exhausted
Tier 2+: existing stronger fallback LLM
```

NimbleはValidated Local Quality Referenceとして残すが、約15秒のLatencyから通常の同期Interactive Pathには入れない。

Local Clef-Flash Q4_K_MもInteractive用途はSTOPする。

---

## 1. Objective

目的は、Engineering RoutingをFrontier / Paid LLMへ毎回送るのではなく、低コストなDecision Layerで可能な限り処理しつつQualityを落とさないこと。

優先順位:

```text
0. deterministic rules / exact logic
1. local decision model
2. free / cheap hosted decision model
3. stronger paid/frontier LLM fallback
```

Primary Quality Gate:

```text
maximum low-cost coverage
subject to:
  accepted-risk <= 1%
  at 95% confidence
```

---

## 2. Final Comparison

| Candidate | Evidence | Raw Quality | Frozen-policy result | p50 latency | Final status |
| --- | --- | ---: | --- | ---: | --- |
| Nimble .80 | Fresh 350 | 350/350 = 100% | 349 accepted, 0 errors, 95% upper risk **0.85%** | **15.22s** | Validated Local Quality Reference |
| Laya Multilingual | Development 350 | **41.14%** | confidence gatingでも救済不能 | **0.359s** | Reject |
| Strands Decider 2B v21 .50 | Fresh 350 | 346/350 = 98.857% | 325 accepted, 2 errors, 95% upper risk **1.92%** | **3.542s** | Fresh Gate FAIL / STOP |
| Cloudflare hosted Clef-Flash .50 | Fresh 350 | **350/350 = 100%** | 332 accepted, 0 errors, 95% upper risk **0.90%** | **0.183s** | **ADOPT** |
| Clef-Flash Q4_K_M / llama.cpp | Smoke only | 5/6 | Full quality validation intentionally skipped | **6.14s**; tuned **10.68s** | Interactive STOP |

QualityとLatencyを同時に満たしたのはHosted Clef-Flashのみ。

---

## 3. Nimble — Validated Local Quality Reference

Frozen Policy:

```text
model = nimble
threshold = 0.80
max accepted risk = 1%
confidence level = 95%
candidate count = 1
```

Fresh 350-case Validation:

```text
raw accuracy = 350/350 = 100%
accepted = 349/350
coverage = 99.714%
accepted errors = 0
95% one-sided exact upper risk = 0.85%
result = PASS
```

Latency:

```text
mean = 15.73s
p50 = 15.22s
p95 = 16.64s
p99 = 31.88s
```

### Decision

Qualityは十分だが、Interactive Routingで15秒待つのは非実用的。

Latency Tail / Warmup / Process Restart / Request Telemetry調査でも、Host TuningでInteractive Levelまで縮められるEvidenceは得られなかった。

```text
Validated Local Quality Reference
Offline Validation / Research用途では維持
Synchronous Interactive Pathからは除外
```

---

## 4. Laya Multilingual — Reject

Development 350-case:

```text
raw accuracy = 41.14%
p50 = 359ms
p95 = 499ms
```

Latencyは非常に優秀だがRouting Qualityが不足。

Thresholdを上げてもAccepted Accuracyが要求水準へ届かず、Selective Confidenceで救済できなかった。

### Decision

```text
Reject
```

---

## 5. Strands Decider 2B v21 — Fresh Validation FAIL

Developmentでは有望だった。

```text
raw accuracy = 349/350
threshold .50:
  accepted = 344
  errors = 0
p50 = 3.51s
```

Frozen Policyを新しいUntouched 350-case Holdoutで検証:

```text
raw accuracy = 346/350 = 98.857%
threshold = 0.50
accepted = 325/350
coverage = 92.857%
accepted errors = 2
empirical accepted risk = 0.615%
95% upper risk = 1.92%
required <= 1%
result = FAIL
```

FAIL後のThreshold Development:

```text
0.68:
  coverage = 85.43%
  errors = 1
  single-policy upper risk ≈ 1.577%

0.73:
  first zero-error
  coverage = 80.00%
  upper risk ≈ 1.064%
```

85% Coverageと1% Riskを同時に満たせない。

### Decision

```text
STOP
```

---

## 6. Cloudflare Hosted Clef-Flash — Adopt

### 6.1 Development

```text
raw accuracy = 350/350 = 100%
p50 = 187.732ms
p95 = 524.920ms

threshold .50:
  accepted = 348/350
  coverage = 99.43%
  accepted errors = 0
  95% upper risk = 0.86%
```

Fresh Holdoutを見る前にPolicyを固定:

```text
provider = cloudflare-clef-flash
model = clef-flash
threshold = 0.50
max accepted risk = 1%
confidence level = 95%
candidate count = 1
```

### 6.2 Untouched Fresh Validation

Run:

```text
20261006-155459
```

Dataset:

```text
350 cases
7 classes × 50
25 new scenario families
prior exact task overlap = 0
Nimble / Strands holdout family overlap = 0
```

Raw Result:

```text
350/350 correct
raw accuracy = 100%
```

Frozen threshold .50:

```text
accepted = 332/350
coverage = 94.857%
accepted errors = 0
empirical accepted risk = 0
95% one-sided exact upper risk = 0.90%
```

Primary Gate:

```text
0.90% <= 1.00%
PASS
```

Latency:

```text
mean = 289.348ms
p50 = 183.269ms
p95 = 611.721ms
p99 = 1514.512ms
```

### Decision

```text
VALIDATED HOSTED DECISION-LAYER CANDIDATE
ADOPT for interactive routing
```

---

## 7. Hosted Clef-Flash Cost / Usage

Fresh 350-request run:

```text
input tokens = 153,187
output tokens = 0
average input ≈ 438 tokens/request
```

Cloudflare Workers AI pricing checked 2026-10-06:

```text
@cf/cloudflare/clef-flash
$0.090 / 1M input tokens
8,182 Neurons / 1M input tokens

Workers AI free allocation:
10,000 Neurons / day
```

Fresh run相当:

```text
estimated token-price equivalent ≈ $0.0138 / 350 requests
estimated Neurons ≈ 1,253
average ≈ 3.58 Neurons/request
```

同程度のRequest Shapeだけを仮定した粗い目安:

```text
10,000 / 3.58 ≈ 2,790 requests/day
```

までDaily Free Allocation内。

これは実測Usageからの概算であり、Request SizeやWorkers AI側Pricing変更で変動する。

Official sources:

- https://developers.cloudflare.com/workers-ai/platform/pricing/
- https://developers.cloudflare.com/changelog/post/2026-10-01-clef-workers-ai/

---

## 8. Local Clef-Flash Q4_K_M — Interactive STOP

公開済み:

```text
ggml-org/Clef-Flash-GGUF
Q4_K_M
6.49 GB
llama.cpp /v1/systemone
```

Untuned Smoke:

```text
raw = 5/6
p50 = 6.14s
p95 = 6.21s
```

Prompt / Batch CPU Pathを狙って:

```text
-t 24
-tb 24
```

を1回だけ検証。

Result:

```text
p50 = 10.68s
p95 = 10.91s
1.74x slower than untuned
```

事前Decision Rule:

```text
p50 > 3s → STOP
```

を大幅に超過。

### Decision

```text
Interactive Path: STOP
350-case Full Development: intentionally skipped
Offline / Research用途だけ残す
```

Hosted版の183ms Medianに対し、Local Q4はUntunedでも約33倍遅い。

---

## 9. Why the Search Can End

探索終了の根拠は「Clefが一番速かった」だけではない。

- Hosted Clef-FlashはFresh 350/350
- Frozen threshold .50で95% upper accepted-risk = 0.90% <= 1%
- p50 = 183ms
- NimbleはQuality PASSだが15.2s
- StrandsはFresh Risk FAIL
- LayaはQuality FAIL
- Local Clef Q4はMulti-secondでInteractive STOP

Current Objectiveに対する明確なWinnerが得られた。

追加モデル探索は、Requirements・Provider Economics・Model Availabilityが大きく変わらない限りExpected Valueが低い。

---

## 10. Final Routing Architecture

### Recommended

```text
Request
  │
  ├─ deterministic / exact ruleで決定可能
  │      └─ accept immediately
  │
  └─ semantic routing required
         │
         ▼
    Cloudflare Clef-Flash
    threshold = 0.50
         │
         ├─ confidence >= .50
         │      └─ accept route
         │
         └─ confidence < .50
                └─ stronger fallback LLM
```

Hosted Provider Failure / Timeout / Quota ExhaustionもFallback条件とする。

### Nimble

通常のSynchronous Fallbackへ入れると15秒級Latencyを追加するため、Default ArchitectureではInteractive Pathに置かない。

用途:

- Offline audit
- Regression comparison
- Incident investigation
- Cloud-independent local reference
- Non-interactive batch decision

### Local Clef Q4

```text
Research / Offline fallback only
```

---

## 11. Production Guardrails

Benchmark PASSは任意のProduction Distribution Shiftを保証しない。

最低限:

1. Clef confidence <0.50は必ずEscalate
2. Provider timeout / HTTP error / malformed responseはFallback
3. Routing label / confidence / latency / fallback reasonをTelemetry化
4. Task Result品質とRouting Decision品質を分離してMonitor
5. Routing Class分布が大きく変化したら再評価
6. Model / Provider / confidence semanticsが更新されたらFresh Validationを再実施
7. 同じHoldoutをRetune後のFresh Evidenceとして再利用しない

---

## 12. Final Status

```text
MODEL SEARCH: CLOSED

ADOPT:
  Cloudflare hosted Clef-Flash
  threshold = 0.50

KEEP AS REFERENCE:
  Nimble .80

STOP:
  Strands Decider 2B v21
  Laya Multilingual
  Local Clef-Flash Q4_K_M for interactive routing

NEXT PHASE:
  production routing cascade implementation
  telemetry / fallback / rollout design
```

---

## Evidence

- `benchmarks/2026-10-05-nimble-single-policy-risk-fresh/`
- `benchmarks/2026-10-06-multi-provider-development/`
- `benchmarks/2026-10-06-strands-single-policy-risk-fresh/`
- `benchmarks/2026-10-06-strands-threshold-development/`
- `benchmarks/2026-10-06-cloudflare-clef-flash-development/`
- `benchmarks/2026-10-06-cloudflare-clef-flash-single-policy-risk-fresh/`
- `benchmarks/2026-10-06-clef-flash-llamacpp-q4-smoke/`
