# Nimble Selective Confidence Analysis — 2026-10-05

## 目的

Fresh Routing Datasetを跨いでAbsolute ThresholdおよびPredicted-label-specific Thresholdが一般化しなかったため、NimbleのConfidence自体がAbstention Signalとして有効かを評価する。

既存4 Runを独立して分析し、Ollamaは再実行していない。

## Validation

Repository Test Suite:

- 30 tests passed
- 0 failures

## 結果

| Run | N | Accuracy | Mean conf | ECE | Brier | Excess AURC | Error AUROC | Max error conf |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 20261004-012101 | 210 | 0.9905 | 0.9054 | 0.0890 | 0.0167 | 0.0000 | 0.9952 | 0.542108 |
| 20261005-033733 | 125 | 0.9840 | 0.8728 | 0.1112 | 0.0372 | 0.0005 | 0.9675 | 0.541419 |
| 20261005-042132 | 140 | 0.9786 | 0.9064 | 0.0722 | 0.0254 | 0.0007 | 0.9659 | 0.740743 |
| 20261005-052440 | 140 | 0.9786 | 0.9317 | 0.0626 | 0.0158 | 0.0003 | 0.9878 | 0.790712 |

Confidenceが高い順にAcceptした場合、4 Runすべてで **Coverage 90%まではAccepted Accuracy 100%** を維持した。

Coverage 95%では:
- 210件ValidationはError 0
- 残り3 Runは各1件のErrorが入った

## Calibration

Nimbleは、この4 Datasetでは一貫してUnder-confident。

Mean ConfidenceはすべてRaw Accuracyを下回り、Signed Gapは約 -0.047 〜 -0.111。

ECEも0.063〜0.111であり、Raw Confidenceをそのまま「正答確率」と解釈する根拠は弱い。

## Selective Ranking

一方、Ranking Signalは非常に強い。

- Error-detection AUROC: **0.9659〜0.9952**
- Excess AURC: **0.0000〜0.0007**
- 4 RunすべてでHighest-confidence 90%にError 0件

つまり現在のEvidenceでは、Confidenceは「確率」としては弱いが、Safe DecisionをErrorより上位へ並べるSignalとしては安定している。

## なぜThreshold Policyが失敗したか

Observed Max Error ConfidenceはDatasetが難しくなるにつれて上昇した。

```text
0.542108
0.541419
0.740743
0.790712
```

直前のError Boundaryの少し上に固定Thresholdを置く方式は、Dataset Shiftに耐えなかった。

したがって現在のEvidenceは以下を支持する。

- **Absolute Threshold Stability:** 弱い
- **Relative Confidence Ranking:** 強い

## Decision

Predicted LabelごとのThresholdをさらに追加しない。

同時に、Confidence自体も捨てない。

次は、UniversalなConfidence Cutoffを仮定せず、強いRanking Signalを利用できるより原理的なAbstention方式を評価する。

候補:
- Development EvidenceでCalibrationし、PolicyをFreezeしてFresh Validation
- Coverage-targeted Abstention
- Selective / Conformal Risk Control
- 同一Metricで別Decision Modelと比較

この4 RunからPolicyを導いた場合、それらはDevelopment Evidenceとして扱い、新しいUntouched Fresh Setで再検証する。

## 統計上の注意

各RunのErrorは2〜3件しかない。

そのため:
- High AUROC Point Estimateでも不確実性は大きい
- ECEはBin数・Sample Sizeに依存する
- Label別Metricはさらに不安定

Cross-runで同じ傾向が繰り返されたことは重要だが、Deployment Proofではない。
