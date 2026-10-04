# Tev1 4B エンジニアリングルーティング Golden ベンチマーク — 2026-10-03

## 目的

キャッシュリセット対応後の 50 件のエンジニアリングルーティング Golden Dataset を用いて、Tev1 4B の再現可能なローカルルーティング基準値を確立する。

## 結果

- Raw Accuracy: **96%（48/50）**
- 平均レイテンシ: **9.883 秒**
- p95 レイテンシ: **10.046 秒**
- Throughput: **0.101 requests/s**

| Threshold | Local Coverage | Accepted Accuracy | Escalation |
| ---: | ---: | ---: | ---: |
| 0.70 | 50% | 100% | 50% |
| 0.75 | 38% | 100% | 62% |
| 0.80 | 26% | 100% | 74% |
| 0.85 | 20% | 100% | 80% |
| 0.90 | 14% | 100% | 86% |

Raw Error は 2 件で、Confidence はそれぞれ 0.677913 と 0.550183 だった。したがって threshold 0.70 では両方とも reject される。

## 解釈

Tev1 4B は低レイテンシのローカル層として有用な特性を示した。threshold 0.70 では Golden Dataset の半数をローカルで受理し、このサンプル上では Accepted Error は観測されなかった。

一方で Escalation Rate は 50% と高く、より強いローカルモデルを評価する理由が残った。

## 意思決定への影響

この結果を、後続の Tev1 → Nimble Cascade Analysis における高速ローカル基準値として採用した。

ただし、これは 50 件の synthetic development set における結果であり、threshold 0.70 が外部データでも 100% Accuracy を保証することを意味しない。
