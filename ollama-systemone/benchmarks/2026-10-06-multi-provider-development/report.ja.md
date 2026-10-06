# Multi-provider Decision Model Development比較 — 2026-10-06

## 目的

Engineering Routingについて、Nimbleの品質を維持しながらCPU Latencyを大幅に下げられるSmall Local Decision Modelがあるか検証する。

今回の350-case DatasetはNimble Validationですでに使用済みなので、**Development Evidence**としてのみ扱う。

新しいProvider PolicyのFresh Validationではない。

## Validation

```text
Ran 77 tests in 0.050s
OK
```

## Laya Multilingual

Run ID:

```text
20261006-141753
```

Latency:

```text
mean 371ms
p50  359ms
p95  499ms
p99  644ms
```

Raw Routing Accuracy:

```text
41.14%
```

Class別:

```text
implementation   6%
review           0%
deterministic   26%
documentation   46%
planning        56%
debug           74%
research        80%
```

Confidence ThresholdでもQuality-preserving Operating Pointは作れない。

threshold 0.70:

```text
coverage = 8.57%
accepted accuracy = 73.33%
```

threshold 0.90:

```text
coverage = 3.43%
accepted accuracy = 58.33%
```

### Decision

Laya MultilingualはこのRouting Taskでは不採用。

CPU Latencyは非常に優秀だが、Routing Quality / Confidence Rankingが不足。

## Strands Decider 2B v21

Run ID:

```text
20261006-142040
```

Latency:

```text
mean 3.59s
p50  3.51s
p95  4.27s
p99  4.98s
```

Raw Routing Accuracy:

```text
349 / 350 = 99.714%
```

Raw Errorは1件のみ:

```text
debug -> implementation
```

他6 Classはすべて50/50正解。

Threshold:

| threshold | coverage | accepted accuracy | accepted |
| ---: | ---: | ---: | ---: |
| 0.50 | 98.29% | 100% | 344 |
| 0.60 | 94.57% | 100% | 331 |
| 0.70 | 84.00% | 100% | 294 |
| 0.80 | 57.71% | 100% | 202 |
| 0.90 | 36.57% | 100% | 128 |

threshold 0.50で唯一のRaw ErrorをRejectできる。

344 Accepted / Error 0件のOne-sided Exact 95% Zero-error Upper Risk Bound:

```text
約0.867%
```

Development Set上では1% Targetを下回る。

ただし結果を見て0.50を選んでいるため、これはValidation PASSではない。

## Validated Nimbleとの比較

Nimble:

```text
threshold = 0.80
accepted = 349 / 350
accepted errors = 0
coverage = 99.714%
steady-state median ≈ 15.2s
```

Strands Development Candidate:

```text
threshold = 0.50
accepted = 344 / 350
accepted errors = 0
coverage = 98.286%
p50 = 3.51s
```

Latency Speedup:

```text
15.2s / 3.51s ≈ 4.3×
```

Development Sample上ではLocal Coverageを約1.43pt下げる代わりに、Median Latencyを約77%削減。

## Interpretation

### Laya

- Latency: Excellent
- Quality: Unacceptable
- Confidence Gating: Rescue不能
- Status: Reject

### Strands

- Latency: Nimbleより大幅に速い
- Raw Accuracy: Near-perfect
- 唯一のErrorは0.50 ThresholdでReject可能
- 0.50でもCoverageは高い
- Status: Advance

## Fresh Validation用Candidate Policy

次段階では以下をFreezeする。

```text
provider = Strands Decider 2B v21
checkpoint = StrandsAgents/strands-decider-2B-hobson-v21
threshold = 0.50
maximum accepted risk = 1%
confidence level = 95%
candidate count = 1
```

新しいHoldoutを見る前に固定する。

## Next Step

新しいUntouched Fresh Routing Holdoutを作る。

Single Predeclared PolicyでAccepted Error 0件の場合、95% Confidenceで1%未満をcertifyするにはAccepted >= 299が必要。

Development Coverageが約98.3%なので、350-case Fresh Setで十分な見込み。

Fresh Setを見てThreshold 0.50を変更しない。

## Decision

- Current Quality ReferenceとしてValidated Nimbleは維持
- Laya MultilingualはReject
- Strands Decider 2B v21をReplacement CandidateとしてAdvance
- 次Fresh ValidationではThreshold 0.50をFreeze
- 新Fresh Holdoutを通るまではStrandsをValidated Replacementとは呼ばない
