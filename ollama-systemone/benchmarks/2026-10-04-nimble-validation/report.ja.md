# Nimble エンジニアリングルーティング Validation — 2026-10-04

## 目的

50 件の Development / Golden Set で観測された Nimble の Confidence Threshold が、別の 210 件 Holdout Set でも再現するかを検証する。

この Run は **Validation Record** であり、Threshold の調整用 Dataset ではない。Threshold 候補は、この Run を見る前に小さい Development Set から選定している。

## 実行条件

- Run ID: `20261004-012101`
- Model: `nimble`
- Dataset: `datasets/engineering-routing-validation.jsonl`
- Cases: 210
- Split: implementation / review / research / debug / planning / documentation / deterministic を各 30 件
- Warmup: synthetic request 1 回
- Iterations: 1
- Cache Reset: `unload`

```bash
uv run systemone-bench \
  --models nimble \
  --dataset datasets/engineering-routing-validation.jsonl \
  --warmup 1 \
  --iterations 1 \
  --cache-reset unload \
  --thresholds 0.40,0.45,0.50,0.55,0.58,0.60,0.65,0.70
```

## 実行環境

- Platform: Linux 7.0.0-34-generic x86_64, glibc 2.43
- Python: 3.14.7
- Logical CPUs: 24
- Physical CPUs: 24
- Memory: 60.81 GiB

## 結果

Raw Classification Accuracy は **99.05%（208/210）**。

| Threshold | Local Coverage | Accepted Accuracy | Escalation | Accepted |
| ---: | ---: | ---: | ---: | ---: |
| 0.40 | 99.52% | 99.52% | 0.48% | 209 |
| 0.45 | 99.52% | 99.52% | 0.48% | 209 |
| 0.50 | 98.57% | 99.52% | 1.43% | 207 |
| **0.55** | **98.10%** | **100%** | **1.90%** | **206** |
| 0.58 | 98.10% | 100% | 1.90% | 206 |
| **0.60** | **97.62%** | **100%** | **2.38%** | **205** |
| 0.65 | 97.14% | 100% | 2.86% | 204 |
| 0.70 | 96.19% | 100% | 3.81% | 202 |

Latency:

- Mean: 20.750 秒
- p50: 21.199 秒
- p95: 21.465 秒
- p99: 21.623 秒
- Throughput: 0.048 requests/s

## Raw Error

2 件の Raw Error を観測した。

| Case | Expected | Predicted | Confidence |
| --- | --- | --- | ---: |
| `validation-098-debug` | debug | implementation | 0.542108 |
| `validation-140-planning` | planning | implementation | 0.277578 |

threshold 0.55 以上では、どちらも Local Accept されない。

観測された Confusion Pattern は、**debug → implementation** と **planning → implementation** に集中している。

## Class 別品質

Raw Accuracy:

- implementation: 30/30
- review: 30/30
- research: 30/30
- debug: 29/30
- planning: 29/30
- documentation: 30/30
- deterministic: 30/30

threshold 0.60 では、この Holdout で Local Accept された Decision はすべて正解だった。各 Class の Coverage も高く、Reject は主に Confidence の低い review / research / debug / planning 周辺に集中した。

## 意思決定

**現在の Deployment Candidate は Nimble + confidence threshold 0.60 とする。**

根拠:

1. 50 件 Development Set では、安全そうな Threshold Plateau が 0.45–0.58 付近に現れた。
2. 別の 210 件 Holdout でも Confidence Gating の挙動が再現した。
3. threshold 0.55 は、今回試した中で Accepted Error が 0 件となる最小 Threshold だった。
4. threshold 0.60 は、観測された最大 Error Confidence 0.542108 より余裕を取りつつ、0.55 と比べて追加 Reject は 1 件だけだった。
5. Nimble 単独でも 97.62% の Local Coverage が得られたため、以前検討した Tev1 → Nimble Cascade を Coverage 目的で採用する理由は弱くなった。

ただし、これは **普遍的な 100% Accuracy を証明するものではない**。この 210 件 synthetic holdout において、threshold 0.60 で Accepted Error が観測されなかった、という記録である。

## 次の Validation Target

Implementation と混同されやすい境界を狙った、別の Adversarial Boundary Set を作る。

重点対象:

- debug vs implementation
- planning vs implementation
- review vs implementation
- research vs implementation

この Holdout を見た後で Threshold を繰り返し調整すると、この Dataset は Development Evidence になる。修正した Policy は新しい Fresh Split で再検証する。

## Artifact

- `manifest.json` — Run Configuration / Environment / Local Raw Artifact 参照
- `metrics.json` — 本レポートで使用した主要な Machine-readable Metrics
- Local Raw Summary: `results/20261004-012101-summary.json`（gitignore）
- Local Raw Details: `results/20261004-012101-details.jsonl`（gitignore）
