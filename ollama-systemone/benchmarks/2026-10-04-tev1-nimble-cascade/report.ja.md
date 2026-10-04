# Tev1 → Nimble Cascade Analysis — 2026-10-04

## 目的

2 段のローカル Cascade が、Nimble 単独と比較して、追加されるレイテンシと複雑性に見合うだけの Safe Local Coverage 改善をもたらすかを確認する。

この分析では、2 つの 50 件 Golden Dataset Detail File を再利用し、Ollama の再実行は行っていない。

## 結果

| Configuration | Local Coverage | Accepted Accuracy | 平均 Local Latency | p95 Local Latency | Local Calls/Request |
| --- | ---: | ---: | ---: | ---: | ---: |
| Tev1 → Nimble | 96% | 100% | **19.339 秒** | 31.300 秒 | 1.48 |
| Nimble 単独 | 96% | 100% | 19.986 秒 | **21.457 秒** | **1.00** |
| Tev1 単独 | 52% | 100% | **9.883 秒** | **10.046 秒** | **1.00** |

観測された最良の Cascade Plateau:

- Tev1 threshold: 0.68
- Nimble threshold: 0.45..0.78
- Local Coverage: 96%
- Fallback: 4%

100% Accepted Accuracy 制約下で観測された最良の Nimble 単独 Plateau:

- threshold: 0.45..0.58
- Local Coverage: 96%
- Fallback: 4%

## 解釈

Cascade は Nimble 単独と比べて平均 Local Latency を約 0.65 秒だけ改善したが、以下の代償があった。

- p95 Latency が約 21.5 秒から 31.3 秒へ悪化
- Local Calls/Request が 1.00 から 1.48 に増加
- Coverage 改善なし
- Fallback Rate 改善なし

Tev1 単独は高速・低 Coverage の選択肢としては依然有用だが、Nimble の前段に置く価値は限定的だった。

## 意思決定への影響

次の Validation Stage では、Tev1 → Nimble Cascade ではなく **Nimble 単独**を優先する。

ただし、この結論も 50 件の Development Set に基づいているため、Deployment Threshold を決める前に Holdout Validation が必要だった。

その後続結果は `../2026-10-04-nimble-validation/` に記録されている。
