# Selective Confidence Analysis

## 目的

`systemone-selective` は、ある1つのDatasetで特定Thresholdが成功したかではなく、Decision ModelのConfidenceが **Abstention（棄却判断）に使える信号か** を評価する。

Fresh Engineering-routing Setを跨いでThreshold Policyが一般化しなかったため、次の段階としてConfidence自体の性質を調べる。

既存の `*-details.jsonl` だけを利用し、Ollamaは再実行しない。

## 評価する2つの問題

### 1. Calibration

Confidenceの数値を「そのPredictionが正しい確率」と解釈できるかを見る。

Metrics:

- **Mean ConfidenceとAccuracyの差**
- **ECE** — Equal-width BinによるExpected Calibration Error
- **MCE** — Calibration Binの最大Gap
- **Brier Score** — ConfidenceとCorrectnessの二乗誤差

ECE / MCE / Brierは低いほど良い。

ただしSystem OneのConfidenceを最初から確率と仮定しない。これらは、その仮定が実データで成立するかを診断するための指標。

### 2. Selective Classification

Confidenceが確率として校正されていなくても、少なくとも「安全なDecisionほど高Confidence、危険なDecisionほど低Confidence」という順位付けができるかを見る。

Metrics:

- **AURC** — Risk-Coverage Curveの面積。低いほど良い
- **Oracle AURC** — 同じError数で理想的に並べた場合のAURC
- **Excess AURC** — Observed AURC - Oracle AURC。0が理想
- **Error-detection AUROC** — `1 - confidence` をError Scoreとして評価。高いほど良い
- **Risk@Coverage** — 高Confidence順に50% / 80% / 90% / 95% / 100%をAcceptした時のRisk

Raw ErrorのConfidenceに加え、Predicted Label別・Expected Label別のBreakdownも出力する。

## 実行例

既存のNimble RunをOllama再実行なしで比較する。

```bash
uv run systemone-selective \
  --details \
    results/20261004-012101-details.jsonl \
    results/20261005-033733-details.jsonl \
    results/20261005-042132-details.jsonl \
    results/20261005-052440-details.jsonl \
  --model nimble \
  --bins 10 \
  --output results/nimble-selective-confidence.json
```

各Detail Fileは独立して分析する。

Development SetとFresh HoldoutをPoolするとDataset固有のFailureを隠す可能性があるため、意図的にまとめない。

## 現在のRouting問題で見るポイント

Confidenceが有効な信号なら、独立した複数Runで以下が再現することを期待する。

1. ErrorのConfidenceがCorrect Decisionより低い
2. Error-detection AUROCが一貫してRandom Rankingを上回る
3. Excess AURCが小さい
4. Coverageを下げるほどSelective Riskも下がる
5. High-confidence Errorが少なく、Predicted Label間を不規則に移動しない

Raw Accuracyが高くても、ごく少数のErrorへ非常に高いConfidenceを付けるならSelective Classifierとしては弱い。

今回評価したいのはまさにこのFailure Mode。

## 統計上の注意

現在のEngineering-routing Datasetでは、各RunのError数が非常に少ない。

そのため:

- ECEはBin数とSample Sizeに影響される
- Errorが2〜3件しかないとAUROCは大きく動く
- Label別Metricはさらに不安定
- 1回のRisk@Coverage成功だけではDeployment Evidenceにならない

単一Datasetから別Thresholdを作るためではなく、複数の独立RunでConfidenceの性質が再現するかを見るために使用する。

## 次フェーズへの判断

Confidence Analysisを確認するまでは、新しいRouting Thresholdを追加しない。

ConfidenceがErrorとCorrectを一貫して分離できるなら、より原理的なAbstention Policyを検討できる。

一方、無関係なPredicted LabelでHigh-confidence Errorが繰り返されるなら、Label-specific Thresholdを継ぎ足すのではなく、別Decision Modelとの比較や追加Uncertainty Signalを検討する。
