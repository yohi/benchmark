# Strands Decider 2B v21 — Single-policy 1% Risk Fresh Validation

## Result

**FAIL**

事前固定したStrands Policyは、Untouched Fresh Holdoutで要求したAccepted-risk Guaranteeを満たさなかった。

```text
provider = strands-decider-2b-v21
checkpoint = StrandsAgents/strands-decider-2B-hobson-v21
threshold = 0.50
maximum accepted risk = 1%
confidence level = 95%
candidate count = 1
```

## Repository Validation

```text
Ran 81 tests in 0.192s
OK
```

## Fresh Benchmark

Run ID:

```text
20261006-145352
```

Raw:

```text
346 / 350 correct
accuracy = 98.8571%
errors = 4
```

Latency:

```text
mean = 3642.047ms
p50  = 3541.741ms
p90  = 3827.330ms
p95  = 4227.894ms
p99  = 5212.714ms
```

Class Accuracy:

```text
debug           50/50 = 100%
deterministic   50/50 = 100%
documentation   50/50 = 100%
implementation  47/50 = 94%
planning        50/50 = 100%
research        49/50 = 98%
review          50/50 = 100%
```

Raw Confusion:

```text
implementation -> planning: 3
research       -> planning: 1
```

## Frozen Threshold 0.50

```text
accepted = 325 / 350
coverage = 92.8571%
accepted errors = 2
accepted accuracy = 99.3846%
empirical accepted risk = 0.6154%
```

Point Estimateは1%未満だが、GateはPoint Estimateでは判定しない。

## Canonical Risk-control

```text
Risk control: model=strands-decider-2b-v21
decisions=350
candidates=1
max_risk=0.0100
confidence=0.9500
correction=bonferroni
family alpha=0.05
pointwise alpha=0.05
zero-error sample requirement=299
```

Candidate:

```text
threshold  coverage  accepted  errors  empirical_risk  upper_risk_bound
0.50       0.9286    325       2       0.0062          0.0192
```

Canonical Decision:

```text
No threshold satisfies the requested simultaneous risk bound and minimum coverage.
```

Candidate Countは1なのでBonferroniでもPointwise Alpha = Family Alpha。

この場合、Single-policy 95% Boundと数値的に同じ。

## FAIL理由

Required Gate:

```text
one-sided exact 95% upper accepted-risk bound <= 1%
```

Observed:

```text
upper bound = 1.92%
```

したがって:

```text
1.92% > 1.00%
FAIL
```

## Development vs Fresh

Development:

```text
threshold .50
accepted = 344 / 350
coverage = 98.286%
accepted errors = 0
```

Fresh:

```text
threshold .50
accepted = 325 / 350
coverage = 92.857%
accepted errors = 2
```

Fresh Holdoutにより、「threshold 0.50でStrands Errorを十分分離して1% Accepted-risk Guaranteeを維持できる」というDevelopment HypothesisはFalsifyされた。

## Interpretation

Latency面ではStrandsは依然魅力的。

```text
Strands p50 ≈ 3.54s
Nimble steady-state median ≈ 15.2s
speedup ≈ 4.3x
```

ただしPredeclared Quality / Risk Requirementを満たさない以上、速度だけで置換はできない。

これは**Latency FailureではなくRisk-control Failure**。

## Decision

- **Nimble threshold 0.80をValidated Local Quality Referenceとして維持**
- **Strands threshold 0.50はValidated Replacementではない**
- このHoldoutを見てThresholdを引き上げ、その結果をFresh Validationと呼ばない
- Strands Revised Policyを作る場合、このDatasetはDevelopment Evidenceへ降格し、別のUntouched Holdoutが必要
- LayaはRouting Quality不足でRejectのまま

## Next Step

Strands継続はOptional。

Higher ThresholdでCoverageを下げてAccepted Riskを下げられる可能性はあるが、既使用Evidence上でDevelopmentしてから新Holdoutが必要。

別案として、Cloudflare Clef-FlashのようなHosted Fast Decision Modelを次のLayer候補として検証できる。
