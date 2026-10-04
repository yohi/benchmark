# ベンチマーク記録

`results/` は意図的に Git 管理対象外とし、Raw Benchmark Output の作業領域として使用する。

意思決定に使った重要な測定結果だけを、この `benchmarks/` 配下へ明示的に昇格して保存する。

各正式記録は原則として以下を含む。

- `manifest.json` — 実行コマンド、モデル、Dataset、実行環境、Run ID
- `metrics.json` — 後から比較可能な機械可読の主要測定値
- `report.md` — 英語版の人間向け解釈・意思決定記録
- `report.ja.md` — 日本語版の人間向け解釈・意思決定記録

この構成により、大量の一時的・探索的 Run を Git に入れずに、設計判断の根拠だけを永続化する。

## 記録ポリシー

モデル選定、Threshold、Architecture、Rollout 判断に実質的な影響を与えた Run を正式記録へ昇格する。

すべての探索的 Run を保存するのではなく、意味のある実験・Validation Milestone ごとに 1 つの Durable Record を残す。

Markdown Report は Machine-readable Metrics の代替ではない。

- JSON は「何が測定されたか」
- Markdown は「その数値をどう解釈し、何を決めたか」

を記録する。

Validation Record を見た後で Threshold や Routing Policy を変更した場合、その Dataset は以後「未使用の Holdout」とは扱わない。変更後の Policy は新しい Fresh Split で再検証する。

## 記録済み Milestone

- `2026-10-03-tev1-golden/` — Tev1 4B の 50 件 Golden Dataset 基準値
- `2026-10-03-nimble-clef-golden/` — Nimble と Clef Flash の比較。Nimble を強い Local Candidate とした根拠
- `2026-10-04-tev1-nimble-cascade/` — Tev1 → Nimble Cascade と単一モデル構成の比較
- `2026-10-04-nimble-validation/` — 210 件 Holdout Validation。Nimble threshold 0.60 を次の Candidate Policy とした根拠

最初の 3 件は Recording Policy 導入後に Backfill した記録である。元の `results/` Raw Artifact はローカルのまま Git 管理対象外だが、実際に観測された意思決定関連の Metrics、実行条件、解釈をこのディレクトリに保存している。
