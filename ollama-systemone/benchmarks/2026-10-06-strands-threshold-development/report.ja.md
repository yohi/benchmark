# Strands Threshold Development — Fresh Validation Failure後

## Result

**STRANDS打ち切り**

事前に決めたDevelopment Gate:

```text
Accepted Risk <= 1%
Coverage >= 85%
```

を同時に満たす実用的なStrands Thresholdは見つからなかった。

## Sweep

```bash
uv run systemone-risk-control \
  --details results/20261006-145352-provider-details.jsonl \
  --model strands-decider-2b-v21 \
  --thresholds 0.50:0.99:0.01 \
  --max-risk 0.01 \
  --confidence-level 0.95 \
  --output results/20261006-145352-strands-threshold-development.json
```

50 Candidateを探索したためToolはBonferroni補正を適用:

```text
family alpha = 0.05
pointwise alpha = 0.001
zero-error sample requirement = 688
```

同時Boundを満たすCandidateはなし。

## Bonferroniだけが理由ではない

Development SweepなのでBonferroniは保守的。

そのため、もし各Thresholdを事前固定したSingle Policyとして扱った場合でも成立するかを確認した。

### threshold 0.68

85% Coverage Cutoffを満たす最後のThreshold:

```text
coverage = 85.43%
accepted = 299
errors = 1
```

0.68をSingle Policyとして固定したとしても、One-sided Exact 95% Upper Riskは約:

```text
1.577%
```

よって:

```text
1.577% > 1%
FAIL
```

### threshold 0.73

最初のZero-error Threshold:

```text
coverage = 80.00%
accepted = 280
errors = 0
```

この時点でCoverage >=85%を満たさない。

さらにSingle-policy Zero-error 95% Upper Boundも:

```text
約1.064%
```

なので1% Requirementにも届かない。

## Threshold遷移

```text
0.68:
  coverage 85.43%
  accepted 299
  error 1

0.69-0.72:
  coverage < 85%
  error 1

0.73:
  first zero-error
  coverage 80%
  accepted 280
```

したがって観測Evidence上、

```text
coverage >= 85%
かつ
single-policy 95% upper risk <= 1%
```

を同時に満たすThresholdはない。

## Decision

Strands用の新Fresh Holdoutは作らない。

Strandsは約3.5sでNimble約15.2sより大幅に速いが、Current Objectiveに対するCoverage / Risk Trade-offは、もう1 Validation Cycleを使うほど強くない。

Current Status:

```text
Nimble .80:
  Validated Local Quality Reference

Strands 2B:
  Fast
  Fresh Validation FAIL
  85% Coverage + 1% Riskを両立できず
  STOP

Laya:
  Routing Quality不足でReject
```

## Next Step

StrandsのRetuneを続けず別Layerへ進む。

次候補はHosted Fast Decision ModelのCloudflare Clef-Flash。

次に確認するのは、Clef-FlashがRouting Qualityを維持しながらLatencyを下げ、Free/Cheap-cloud Budget内へ収まるか。
