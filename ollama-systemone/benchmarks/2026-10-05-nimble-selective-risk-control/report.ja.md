# Nimble Selective Risk Control — 2026-10-05

## 目的

直前に観測したError ConfidenceへThresholdを追従させるのではなく、Accepted Riskの統計的Upper BoundからThresholdを選ぶ方式が成立するかを評価する。

既存4 RunをDevelopment Evidenceとして扱い、合計615 Decisionを使用した。

## Method

0.50〜0.99の50個のFixed Threshold Candidateを評価。

各Thresholdで:

- confidenceがThreshold以上のDecisionをAccept
- Accepted Errorを数える
- Empirical Accepted Riskを計算
- One-sided exact Clopper-Pearson Upper Boundを計算
- 50 Candidate全体へBonferroni補正

Family-wise Confidence Levelは95%。

```text
family alpha = 0.05
pointwise alpha = 0.001
```

## Test Validation

Repository Test Suite:

- 39 tests passed
- 0 failures

## Accepted Risk 1% Target

補正後に1% RiskをZero Errorで証明するために必要なAccepted Decisionは **688件**。

現在のDevelopment Pool全体は **615件**。

結果:

```text
feasible policy = none
```

これは主として **Evidence量不足** であり、「Nimbleでは1% Riskを達成不能」という意味ではない。

Threshold 0.80では:

- Coverage: 88.29%
- Accepted: 543
- Error: 0
- Empirical Risk: 0%
- Simultaneous Upper Risk Bound: 1.26%

Observed Resultは良いが、補正済みUpper Boundが1%を超えるためcertifyできない。

## Accepted Risk 1.5% Diagnostic

Zero-error Sample Requirementは **458件** へ下がる。

このDiagnostic条件ではMaximum-coverage Feasible Policyは:

```text
threshold = 0.80
```

Development Metrics:

- Coverage: **88.29%**
- Accepted: **543 / 615**
- Accepted Error: **0**
- Empirical Risk: **0%**
- Simultaneous Upper Risk Bound: **1.26%**

Threshold 0.80における各Run:

| Run | Coverage | Accepted | Errors |
| --- | ---: | ---: | ---: |
| 20261004-012101 | 90.95% | 191 | 0 |
| 20261005-033733 | 78.40% | 98 | 0 |
| 20261005-042132 | 87.86% | 123 | 0 |
| 20261005-052440 | 93.57% | 131 | 0 |

4 RunすべてでAccepted Errorは0件。

## 解釈

1% Runから分かるのは、50 Threshold Searchを含めて厳密なSimultaneous Boundを立てるには現在のDataset Sizeが不足しているということ。

一方1.5% DiagnosticではPolicyが成立しており、このMethod自体が無意味ではないことも確認できた。

ただし **1.5%は事前にProduct / Safety Requirementとして定義した値ではない**。

したがって、この結果だけでThreshold 0.80をDeployment CandidateとしてFreezeしない。

## Decision

Coverageを見てからAcceptable Risk Targetを選ばない。

次の判断はOptimizationの外側で決める必要がある。

- Requirementが1%なら、独立Development Evidenceを追加するか、事前固定するCandidate Familyを縮小する
- 独立した理由で1.26%以上のRisk Requirementが許容されるなら、Threshold 0.80をCandidateとしてFreezeし、新しいUntouched Fresh Holdoutへ進める

## Limitation

これはi.i.d. / Exchangeabilityを前提とするDevelopment-sample Statistical Bound。

以下ではない。

- Distribution Shift Guarantee
- Deployment Validation
- New Fresh Holdoutの代替
- Full Conformal Risk Control

Fresh Validation後もProduction Monitoringは必要。
