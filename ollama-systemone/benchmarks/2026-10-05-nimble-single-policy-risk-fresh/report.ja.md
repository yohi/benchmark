# Nimble Single-policy 1% Risk Fresh Validation — 2026-10-05

## 目的

測定前に固定した以下のPolicyをFresh Holdoutで検証する。

```text
model = nimble
threshold = 0.80
maximum accepted risk = 1%
confidence level = 95%
candidate count = 1
```

このFresh Holdoutは新規350件で構成し、Threshold探索は行わない。

## Validation

Repository Test:

- 42 passed
- 0 failed

Fresh Benchmark:

```text
run_id = 20261005-063902
decisions = 350
raw accuracy = 350/350 = 100%
```

Threshold 0.80:

- Accepted: **349/350**
- Coverage: **99.714%**
- Accepted Error: **0**
- Accepted Accuracy: **100%**
- Fallback: **1/350**

唯一のFallbackは `risk-fresh-112-deterministic`。
Prediction自体はCorrectだがConfidence 0.734555のためEscalateされた。

## Canonical Single-policy Risk Evaluation

実行結果:

```text
candidates = 1
family alpha = 0.05
pointwise alpha = 0.05
zero-error sample requirement = 299 accepted decisions
```

Observed:

```text
threshold = 0.80
coverage = 0.9971
accepted = 349
errors = 0
empirical risk = 0.0000
upper risk bound = 0.0085
```

One-sided Exact 95% Upper Accepted-risk Boundは約 **0.85%** で、事前固定した **1%** Targetを下回った。

## Verdict

**PASS**

事前固定したSingle-policy CandidateはFresh Holdout Gateを満たした。

```text
upper accepted-risk bound <= 1%
```

このHoldout上でThreshold Tuningは行っていない。

## Per-class Result

7 Routing ClassすべてRaw Accuracy 50/50。

Threshold 0.80では:

- debug: 50 accepted / 0 errors
- deterministic: 49 accepted / 0 errors
- documentation: 50 accepted / 0 errors
- implementation: 50 accepted / 0 errors
- planning: 50 accepted / 0 errors
- research: 50 accepted / 0 errors
- review: 50 accepted / 0 errors

## 解釈

これは以前のDevelopment-time Threshold Searchより強いEvidence。

理由:

1. threshold 0.80をDataset測定前に固定
2. Accepted Risk Target 1%も事前固定
3. 1% GateをStatistically Test可能なAccepted Sample Sizeを確保
4. Canonical Single-policy Exact-binomial EvaluationでPASS

したがって、このFresh Evaluation Distributionに対してPolicyはValidationを通過した。

ただし、将来Production Distribution Shiftに対するGuaranteeではない。

## Latency Note

Quality GateはPASSしたがLatencyは別問題。

Observed Latency:

- Mean: 15.73s
- p50: 15.22s
- p95: 16.64s
- p99: 31.88s

p99 TailはRouting Qualityとは分離して調査すべき。

## Decision

以下のRouting Policyを **Fresh-holdout Validated** と扱える。

```text
nimble
confidence >= 0.80 ならLocal Accept
それ未満はEscalate
```

次のWorkは:

- Production / Online Monitoring Design
- Latency Tail Investigation
- 時間を跨いだ追加Independent Evidence

このHoldoutをThreshold調整に再利用し、そのままFresh Validation Evidenceと呼び続けてはいけない。
