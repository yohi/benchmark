# Nimble Class-aware Policy Fresh Holdout — 2026-10-05

## 目的

事前に選定したClass-aware Nimble Policyを、新しいBalanced Fresh Holdoutで検証する。

測定前にPolicyは以下へ固定済み。

```text
default threshold = 0.60
predicted planning threshold = 0.80
```

## Test Validation

ローカルでRepository Test Suiteを実行。

- 21 tests passed
- 0 failures

新しいHoldoutのschema / balance / frozen-policy / non-overlap testに加え、既存benchmark / policy testもすべて通過した。

## Benchmark Result

Run ID: `20261005-052440`

Raw Accuracy: **97.86%（137/140）**。

Global Thresholdの参考値:

| Threshold | Coverage | Accepted Accuracy | Escalation |
| ---: | ---: | ---: | ---: |
| 0.60 | 98.57% | 99.28% | 1.43% |
| 0.80 | 93.57% | 100% | 6.43% |

ただし今回の評価対象はGlobal Thresholdではなく、事前固定したClass-aware Policy。

## Raw Error

Raw Errorは3件。

| Case | Expected | Predicted | Confidence | Frozen Policy |
| --- | --- | --- | ---: | --- |
| `fresh-037-debug` | debug | review | 0.432299 | fallback |
| `fresh-116-documentation` | documentation | implementation | **0.790712** | **誤ってaccept** |
| `fresh-120-documentation` | documentation | implementation | 0.585526 | fallback |

決定的なのは `fresh-116-documentation`。

現在のCandidate PolicyがThresholdを引き上げるのは、ModelのPredictionが `planning` の場合だけ。

このErrorはPredictionが `implementation` のためdefault 0.60が適用され、confidence 0.790712によりLocal Acceptされる。

## Policy判定

**FAIL — 固定済みClass-aware Candidateは、このFresh Holdoutで反証された。**

前回のDevelopment Evidenceで観測した `planning` PredictionのFailureは対策できたが、今回は別軸のHigh-confidence Failureとして

```text
documentation → implementation
```

が出現した。

したがって現時点では、

```text
default = 0.60
planning = 0.80
```

をDeployment Candidateとして扱う根拠はない。

## 固定PolicyのDerived Metrics

このHoldoutに対する `systemone-policy` CLIはまだ実行していないが、Benchmark SummaryだけでPass / Failは確定できる。

Global 0.60では138件をAcceptし、Accepted Errorが1件。

planning-specific 0.80 overrideにより、confidence 0.631908の正しいplanning predictionが追加で1件fallbackする。

したがってFrozen Policyは以下になる。

- Local Accepted: 137/140
- Local Coverage: **97.86%**
- Accepted Correct: 136
- Accepted Accuracy: **99.27%**
- Fallback: 3/140 = **2.14%**
- Accepted Error: **1件**

CanonicalなFixed-policy Outputを残すため `systemone-policy` は実行すべきだが、判定自体は変わらない。

## 解釈

重要なのは、Riskが1つのPredicted Labelに限定されていないこと。

前回Production-derived Development Setでは、High-confidence Error 2件がどちらも `planning` Predictionだったため、planningだけThresholdを上げるPolicyを作った。

しかしFresh Holdoutでは新たに、

```text
documentation → implementation @ 0.790712
```

が出た。

つまり、直前に観測したFailure LabelだけにPolicyを合わせる方式は過度に局所的。

## Methodology上の位置付け

このHoldoutは、固定済み0.60/0.80 Policyに対するFresh Validation Evidenceとして有効であり、そのPolicyを反証した。

この結果を見てimplementation thresholdを同じHoldout上で調整し、そのままValidation Evidenceとして再利用してはいけない。

新しいPolicyを作る場合、このRunをDevelopment Evidenceとして利用してよいが、そのPolicyはさらに別のFresh Setで再検証する。
