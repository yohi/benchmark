# Class-aware Policy Fresh Holdout

## 目的

このDatasetは、前回140件のProduction-derived SetをDevelopment Evidenceとして選定した **Class-aware Nimble Policy** を、新しいデータで検証するFresh Holdout。

測定前にPolicyを以下へ固定する。

```text
default threshold = 0.60
predicted planning threshold = 0.80
```

このDataset上でより良いThresholdを探索することが目的ではない。

すでに選定済みのPolicyが別データへ一般化するかを確認する。

## Dataset

`engineering-routing-policy-fresh-holdout.jsonl` は140件。

7つのRouting Labelを各20件に均等化している。

| Label | Cases |
| --- | ---: |
| implementation | 20 |
| debug | 20 |
| review | 20 |
| research | 20 |
| planning | 20 |
| documentation | 20 |
| deterministic | 20 |
| **total** | **140** |

前回のProduction-derived Setは実Workloadの比率へ寄せたが、今回はValidation目的のため意図的にBalancedにしている。

これにより、弱いClassが全体件数比率で隠れることを防ぐ。

## Freshness

Taskは、前回とは異なる実Engineering Request Patternを抽象化して作成している。

以下とのTask Text完全一致は0件とする。

- 50件 Golden / Development Set
- 210件 Validation Set
- 125件 Implementation-boundary Adversarial Set
- 140件 Production-derived Development Set

新しいRequest Familyには以下を含む。

- subagent context isolation / fix-loop convergence
- checkpoint / replay safety
- agent observability / OpenTelemetry
- MCP schema / versioning
- idempotency / ORM query performance
- Python concurrency / compatibility migration
- CI runner / cache behavior
- benchmark methodology / selective classification

## Evaluation Protocol

まずPolicyを変更せず、通常のBenchmarkを実行する。

```bash
uv run systemone-bench \
  --models nimble \
  --dataset datasets/engineering-routing-policy-fresh-holdout.jsonl \
  --warmup 1 \
  --iterations 1 \
  --cache-reset unload \
  --thresholds 0.60,0.80
```

その後、探索Gridではなく **固定済みPolicyを1通りだけ** 評価する。

```bash
uv run systemone-policy \
  --details results/<RUN_ID>-details.jsonl \
  --model nimble \
  --default-threshold 0.60 \
  --label-grid planning=0.80 \
  --min-accepted-accuracy 1.0 \
  --output results/<RUN_ID>-fixed-policy.json
```

`planning=0.80` は値が1つだけなので、Analyzerが評価するCandidate Policyも1通りだけ。

## Pass / Fail

Primary Gate:

- 固定Class-aware Policyにおける Accepted Accuracy

Secondary Metrics:

- Local Coverage
- Fallback Rate
- Predicted Label別Acceptance
- 全Raw ErrorのConfidence
- Confusion Matrix

固定Policyが誤答を1件でもLocal Acceptした場合、このHoldoutはCandidate Policyを反証したと扱う。

結果を見た後で0.60や0.80を変更し、同じDatasetをFresh Validationと呼び続けてはいけない。

Policyを変更した場合は、さらに別のFresh Setで再検証する。
