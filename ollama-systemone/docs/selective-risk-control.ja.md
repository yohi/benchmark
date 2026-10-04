# Selective Risk Control

## 目的

`systemone-risk-control` は、直前のError Confidenceを少し上回るThresholdを選ぶのではなく、Development Evidence上のAccepted Error Riskに対する上側信頼限界からConfidence Thresholdを選定する。

処理は以下。

1. 事前固定したConfidence Threshold Gridを評価
2. 各ThresholdでAccepted件数とAccepted Error件数を数える
3. Accepted Error Riskに対するone-sided exact Clopper-Pearson upper boundを計算
4. Threshold Grid全体の探索にBonferroni補正を適用
5. 補正後Upper Boundが指定Risk以下となるThresholdのうちCoverage最大を選ぶ

選定されたThresholdはDevelopment Candidateであり、新しいUntouched Fresh Holdoutを見る前にFreezeする。

## なぜ次にこれを試すか

Nimbleの4 Run横断分析ではConfidence Rankingは強かった。

- Error-detection AUROC: 0.9659〜0.9952
- Excess AURC: 0.0000〜0.0007
- Confidence上位90%では全RunでError 0件

一方、Observed Max Error Confidenceは約0.54から0.79まで上昇した。

つまり、

```text
Relative Ranking: 強い
Absolute Cutoff: 不安定
```

という状態。

そこで「直前の最大Errorより少し高い値」ではなく、Accepted Riskの統計的Upper Boundを満たすCutoffがFresh Setへ一般化するかを次に検証する。

## 統計手法

各固定Thresholdについて、

- `confidence >= threshold` をAccept
- Accepted件数を `n`
- Accepted Error件数を `k`
- Empirical Accepted Riskを `k / n`
- One-sided exact binomial upper confidence boundを計算

同じDevelopment Evidence上で複数Thresholdを探索するため、Family AlphaをThreshold候補数で割るBonferroni補正を行う。

例:

```text
confidence level = 0.95
threshold candidates = 50
family alpha = 0.05
pointwise alpha = 0.001
```

Candidateは以下を満たす必要がある。

```text
simultaneous upper accepted-risk bound <= requested max risk
```

その中でDevelopment Coverage最大のThresholdを選ぶ。

## Sample Size要件

厳しいRisk Targetは、Accepted Errorが0件でもSample不足で証明不能な場合がある。

Error 0件のOne-sided Upper Boundは:

```text
1 - alpha^(1/n)
```

CLIはMultiple-testing補正後のRisk Targetを証明するために必要なMinimum Zero-error Accepted Sample Sizeも出力する。

例えば:

```text
max risk = 1%
family confidence = 95%
threshold candidates = 50
pointwise alpha = 0.001
```

では、最低 **688件のZero-error Accepted Decision** が必要。

これにより「Feasible Policyなし」がModelの失敗なのか、単にEvidence不足なのかを区別できる。

## 実行例

既存4 RunをDevelopment Evidenceとして利用する。

```bash
uv run systemone-risk-control \
  --details \
    results/20261004-012101-details.jsonl \
    results/20261005-033733-details.jsonl \
    results/20261005-042132-details.jsonl \
    results/20261005-052440-details.jsonl \
  --model nimble \
  --thresholds 0.50:0.99:0.01 \
  --max-risk 0.01 \
  --confidence-level 0.95 \
  --output results/nimble-risk-control-1pct.json
```

現在のEvidence量でどの程度までRisk Boundを証明できるかを見る補助診断として、1.5%も実行可能。

```bash
uv run systemone-risk-control \
  --details \
    results/20261004-012101-details.jsonl \
    results/20261005-033733-details.jsonl \
    results/20261005-042132-details.jsonl \
    results/20261005-052440-details.jsonl \
  --model nimble \
  --thresholds 0.50:0.99:0.01 \
  --max-risk 0.015 \
  --confidence-level 0.95 \
  --output results/nimble-risk-control-1p5pct.json
```

ただし、Coverageが魅力的になるRisk Targetを結果を見て採用してはいけない。

Target RiskはTuning Parameterではなく、Product / Safety Requirementとして事前に決める。

## Output

以下を出力する。

- Threshold候補数
- Family Alpha / Pointwise Alpha
- Requested Riskを証明するためのMinimum Zero-error Sample Size
- 各ThresholdのEmpirical Accepted Risk
- 各ThresholdのSimultaneous One-sided Upper Risk Bound
- FeasibleならCoverage最大Threshold
- Selected Thresholdにおける各Detail File別Empirical Metrics

## Scope / Limitation

これは **Distribution Shiftに対するGuaranteeではない**。

Fixed Threshold Ruleに対してDevelopment Examplesがi.i.d. / exchangeableであるという前提のSample内Statistical Bound。

Bonferroni補正は設定されたFixed Grid上のThreshold SearchをDevelopment Evidence内で保護するが、将来Workloadで同じRiskになることまでは保証しない。

したがって:

- Selected ThresholdをDeployment Validatedと呼ばない
- 新しいFresh Holdoutを見る前にThresholdをFreezeする
- Fresh Holdoutで失敗したら同じHoldout上で再調整してFresh扱いしない
- Fresh Validation後もProduction Monitoringは必要

また、これはFull Conformal Risk Control実装ではない。

より複雑な仕組みを入れる前に、Exact Binomial Risk Controlという最小構成が成立するかを確認するためのExperiment。
