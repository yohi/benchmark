# Nimble Implementation Boundary Adversarial ベンチマーク — 2026-10-05

## 目的

210件 Holdout Validation で `implementation` 方向への Raw Error が観測されたため、Implementation に隣接するタスクだけを集めた Adversarial Dataset で、現在の Nimble Routing Policy を Stress Test する。

この Dataset では、debug / planning / review / research の要求にも意図的に implementation 関連語彙を含めている。

今回の Run を見る前に Candidate Policy は固定済み。

- Model: `nimble`
- Confidence Threshold: **0.60**

## 実行条件

- Run ID: `20261005-033733`
- Dataset: `datasets/engineering-routing-implementation-boundary.jsonl`
- Cases: 125
- Classes: implementation / debug / planning / review / research
- 各 Class: 25件
- Warmup: 1
- Iterations: 1
- Cache Reset: `unload`

```bash
uv run systemone-bench \
  --models nimble \
  --dataset datasets/engineering-routing-implementation-boundary.jsonl \
  --warmup 1 \
  --iterations 1 \
  --cache-reset unload \
  --thresholds 0.55,0.60,0.65,0.70
```

## 結果

Raw Accuracy は **98.4%（123/125）**。

| Threshold | Local Coverage | Accepted Accuracy | Escalation | Accepted |
| ---: | ---: | ---: | ---: | ---: |
| 0.55 | 94.4% | 100% | 5.6% | 118 |
| **0.60** | **92.0%** | **100%** | **8.0%** | **115** |
| 0.65 | 89.6% | 100% | 10.4% | 112 |
| 0.70 | 86.4% | 100% | 13.6% | 108 |

事前に選定した threshold 0.60 では、Local Accept した 115件すべてが正解だった。

## Raw Error

観測された Raw Error は2件。

| Case | Expected | Predicted | Confidence |
| --- | --- | --- | ---: |
| `boundary-018-debug` | debug | review | 0.541419 |
| `boundary-097-research` | research | review | 0.513124 |

いずれも threshold 0.60 では Reject される。

特に重要なのは、今回狙って検証した **implementation への誤分類が 0件**だったこと。

## threshold 0.60 における Class 別結果

| Expected Class | Raw Accuracy | Local Coverage | Accepted Accuracy |
| --- | ---: | ---: | ---: |
| implementation | 100% | 88% | 100% |
| debug | 96% | 92% | 100% |
| planning | 100% | 100% | 100% |
| review | 100% | 100% | 100% |
| research | 96% | 80% | 100% |

210件 Holdout で懸念された Implementation Attractor は、この Adversarial Set では再現しなかった。

2件の誤分類はいずれも `review` 方向であり、Confidence も 0.55 未満だった。

## 意思決定

**Nimble threshold 0.60 を Current Candidate Policy として維持する。**

今回 threshold 0.55 でも Accepted Accuracy 100% かつ Coverage 94.4% だったが、この結果を見た後で 0.55 に下げると、この Fresh Adversarial Set を Threshold Tuning に使用することになる。

したがって、0.55 へ再調整する根拠にはせず、事前固定していた **0.60 の追加検証成功**として扱う。

## Latency に関する注意

今回の Latency:

- Mean: 11.806秒
- p50: 10.556秒
- p95: 22.983秒
- p99: 23.219秒

分布は均一ではなく、Run 前半の一部が約23秒、その後の多くが約10.5秒となっている。

今回の `--cache-reset unload` は Model Benchmark の開始前に Reset するものであり、各 Measured Request の前に Unload しているわけではない。

したがって、この Run は Request ごとの Cold Latency を示すものではなく、以前の210件 Validation Run と Latency を単純比較すべきではない。

今回の主要な Evidence は Routing Quality である。

## 次のステップ

現在の Evidence Chain は以下。

1. 50件 Development Set で Nimble を Strong Local Candidate と判断
2. 210件 Holdout で threshold 0.60 を支持
3. 125件 Implementation Boundary Adversarial Set でも threshold 0.60 で Accepted Accuracy 100% を維持し、Implementation への誤分類 0件

Production 利用前の次の有力な Validation は、Synthetic Dataset をさらに Threshold Tuning することではなく、自然な曖昧さ・ノイズ・Multi-intent を含む **Production-derived Fresh Dataset** での評価。
