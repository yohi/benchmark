# Nimble vs Clef Flash エンジニアリングルーティング Golden ベンチマーク — 2026-10-03

## 目的

Tev1 の基準値に対して、より強いローカル System One 候補である Nimble と Clef Flash を、同じ 50 件のエンジニアリングルーティング Golden Dataset 上で比較する。

## 結果

| Model | Raw Accuracy | 平均レイテンシ | p95 レイテンシ | Coverage @ 0.70 | Accepted Accuracy @ 0.70 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Nimble | **98%** | 19.985 秒 | 21.457 秒 | **94%** | **100%** |
| Clef Flash | 96% | 21.003 秒 | 21.216 秒 | 54% | 100% |

Nimble の Raw Error は 1 件:

- `semantic-28-debug`, confidence 0.442549

Clef Flash の Raw Error は 2 件:

- `semantic-06-implementation`, confidence 0.414685
- `semantic-45-deterministic`, confidence 0.538367

## 解釈

Nimble は Clef Flash とほぼ同程度のレイテンシで、Safe Local Coverage を大きく引き上げた。

threshold 0.70 では、Nimble は 47/50 件を Accepted Error なしで受理した。一方 Clef Flash は 27/50 件だった。

この Dataset と今回の用途では、Clef Flash は Nimble に対して実質的に劣後した。

## 意思決定への影響

Nimble を強いローカルルータの第一候補とした。

次の論点は「どのローカルモデルを使うか」から、「Tev1 → Nimble の Cascade が Nimble 単独より十分な価値を持つか」に移った。

ただし、この 50 件は Development Set であり、Threshold の最終選定には別の Holdout Validation が必要と判断した。
