# Cloudflare Clef-Flash Development Benchmark

## Result

**FRESH VALIDATIONへ進める**

既使用350-case Development SetでCloudflare-hosted Clef-FlashはRaw 350/350 = 100%を達成し、threshold 0.50のSingle-policy 1% Accepted-risk Development GateもPASSした。

## Repository Validation

```text
Ran 84 tests in 0.085s
OK
```

Hosted-provider Adapter、Environment Expansion、Response Envelope、Usage Aggregation、および既存Benchmark Testを含めて全PASS。

## Benchmark

Run ID:

```text
20261006-154141
```

Dataset:

```text
datasets/engineering-routing-single-policy-risk-fresh.jsonl
```

このDatasetはBenchmark Chainですでに使用済みなので、Clef-Flashに対してはDevelopment Evidence。

## Raw Quality

```text
350 / 350 correct
raw accuracy = 100%
raw errors = 0
```

7 Routing Classすべて50/50正解。

## Latency

Client-observed End-to-end:

```text
mean = 236.971ms
p50  = 187.732ms
p90  = 359.081ms
p95  = 524.920ms
p99  = 881.126ms
```

Network / API Overheadを含む実経路Latency。

## Usage

```text
requests = 350
input_tokens = 151,404
output_tokens = 0
```

## Selective Confidence

```text
accuracy = 1.0000
mean confidence = 0.8160
ECE = 0.1840
Brier = 0.0426
AURC = 0
errors = 0
error AUROC = n/a
```

Errorが0件なのでConfidenceのError-ranking性能は評価不能。

Observed Accuracy 100%に対してConfidenceはAbsoluteにはUnderconfidentだが、Raw Classifier自体が誤っていないためCalibrationはSecondary。

## Frozen Threshold Candidate

Exactly One ThresholdでRisk Control:

```text
threshold = 0.50
candidate count = 1
max accepted risk = 1%
confidence = 95%
```

Canonical Result:

```text
coverage = 99.43%
accepted = 348 / 350
accepted errors = 0
empirical risk = 0
95% one-sided exact upper risk bound = 0.86%
```

したがって:

```text
0.86% <= 1.00%
Development PASS
```

## Decision

次のFresh Holdoutを見る前にCandidateを固定する。

```text
provider = cloudflare-clef-flash
model = clef-flash
threshold = 0.50
max accepted risk = 1%
confidence = 95%
candidate count = 1
```

次のFresh Holdoutを見てThresholdを変更しない。

## Next Step

新しいUntouched 350-case Holdoutを作る。

条件:

- Routing Classごと50 cases
- 25 Engineering Scenario Families
- Prior Routing DatasetとのExact Task Overlapなし
- Nimble / Strandsの350-case HoldoutとのScenario-family Overlapなし
- Measurement前にClef-Flash Policy MetadataをFreeze

その後、Clef-Flash threshold 0.50をExactly Once実行して同じSingle-policy 1% Risk Gateを評価する。
