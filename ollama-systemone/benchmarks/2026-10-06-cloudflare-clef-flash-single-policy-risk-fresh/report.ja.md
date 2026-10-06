# Cloudflare Clef-Flash Single-policy 1% Risk Fresh Validation

## Result

**PASS**

事前固定したClef-Flash PolicyがFresh 1% Accepted-risk Validation GateをPASSした。

## Frozen Policy

Holdoutを見る前に固定:

```text
provider = cloudflare-clef-flash
model = clef-flash
endpoint model = @cf/cloudflare/clef-flash
threshold = 0.50
maximum accepted risk = 1%
confidence level = 95%
candidate count = 1
```

このHoldout上でThreshold Searchは行っていない。

## Repository Validation

```text
Ran 88 tests in 0.194s
OK
```

新Holdout Testで以下を確認:

- 350 balanced unique cases
- Frozen Policy Metadata
- Prior Routing DatasetとのExact Task Overlap 0
- Nimble / Strands 350-case HoldoutとのScenario-family Overlap 0

## Fresh Benchmark

Run ID:

```text
20261006-155459
```

Dataset:

```text
datasets/engineering-routing-clef-flash-risk-fresh.jsonl
```

Raw Result:

```text
350 / 350 correct
raw accuracy = 100%
raw errors = 0
```

7 Routing Classすべて50/50正解。

## Latency

Client-observed End-to-end:

```text
mean = 289.348ms
p50  = 183.269ms
p90  = 512.616ms
p95  = 611.721ms
p99  = 1514.512ms
```

## Usage

```text
requests = 350
input_tokens = 153,187
output_tokens = 0
```

## Canonical Single-policy Risk Control

Exactly One Candidate:

```text
threshold = 0.50
candidate count = 1
family alpha = 0.05
pointwise alpha = 0.05
zero-error sample requirement = 299 accepted decisions
```

Canonical Result:

```text
coverage = 94.86%
accepted = 332 / 350
accepted errors = 0
empirical accepted risk = 0
one-sided exact 95% upper risk bound = 0.90%
```

Primary Gate:

```text
0.90% <= 1.00%
PASS
```

## Interpretation

Provider Benchmark Summaryの `comparison_status = development-only` はCLIの固定Methodology Labelであり、このExperiment Design自体を表していない。

今回をFresh Validation Evidenceとして扱える理由:

- Datasetを見る前にPolicyをFreeze
- Datasetを新規作成
- Prior Routing SetとのExact Task Overlap 0
- Nimble / Strands 350-case HoldoutとのScenario-family Overlap 0
- Exactly One Thresholdのみ評価

## Decision

Clef-Flash threshold 0.50を **Current Benchmark Distributionに対するValidated Hosted Decision-layer Candidate** とする。

比較:

```text
Nimble .80:
  Validated Local Quality Reference
  fresh coverage 99.71%
  accepted errors 0
  95% upper risk 約0.85%
  p50 約15.2s

Clef-Flash .50:
  Validated Hosted Decision-layer Candidate
  fresh coverage 94.86%
  accepted errors 0
  95% upper risk 0.90%
  p50 183ms

Strands 2B:
  Fresh Validation FAIL
  STOP

Laya:
  Routing Quality不足
  Reject
```

## Claimの範囲

このValidationはBenchmark Distributionに対するFrozen Policyの検証。

任意のProduction Distribution Shiftまで保証するものではない。

Production Rolloutでは少なくとも以下を維持する:

- confidence <0.50でabstain / escalate
- Routing Decision / Confidence Telemetry
- Stronger Fallback Path
- Workload Shapeが大きく変化した場合の再評価
