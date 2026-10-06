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
- `2026-10-05-nimble-implementation-boundary/` — 125 件 Adversarial Validation。threshold 0.60 で Accepted Accuracy 100% を維持し、Implementation Attractor が再現しなかった記録
- `2026-10-05-nimble-policy-fresh-holdout/` — Balanced Fresh Validation。`default=0.60 / planning=0.80` Candidate を High-confidence な documentation → implementation Error が反証した記録
- `2026-10-05-nimble-selective-confidence/` — Nimble 4 Run横断のCalibration / Selective Classification分析。Absolute Confidence Calibrationは弱い一方、Error Ranking Signalは強いことを確認した記録
- `2026-10-05-nimble-selective-risk-control/` — Exact Binomial Selective Risk Control分析。1%は現在のEvidence量ではcertify不能、1.5% Diagnosticではthreshold 0.80がDevelopment Coverage 88.29%・Accepted Error 0件でfeasibleとなった記録
- `2026-10-05-nimble-single-policy-risk-fresh/` — 事前固定したNimble threshold 0.80を350件Fresh Holdoutで検証。349/350 Accepted・Accepted Error 0件・95% One-sided Exact Upper Risk Bound 0.85%で1% GateをPASSした記録
- `2026-10-05-nimble-latency-tail-analysis/` — 31.88s p99のRequest順序分析。First-5 MeanがRemainderの1.907倍、Position 21以降の>=1.5×Median Tail Eventは0件で、TailがPrefixへ強く集中していることを確認した記録
- `2026-10-05-nimble-warmup-stabilization/` — 同一Fixed WorkloadでSynthetic-1とRepresentative-7を比較。Representative-7の改善Evidenceはなく、両ProfileともRepeat 1はSpike、Repeat 2は安定し、Warmup ProfileよりChronological / Runtime State Effectが支配的と判断した記録
- `2026-10-05-nimble-warmup-process-restart/` — 各Trial前にOllama Service Restartを行って同一Studyを再実行。Repeat 1/2のp95 GapがSynthetic約89.7%、Representative約84.9%縮小し、Process-local Runtime Stateの関与が強く示唆された記録。Sparse Outlierは残存
- `2026-10-06-nimble-request-telemetry/` — Ollama Daemon + 全Descendantを集計するCorrected Process-tree Telemetry Study。140 Requestすべてで>=1.25×Median Spikeは0件、強いLatency Correlationもなく、Host Tuningへ進む根拠なしとしてCurrent Benchmark ObjectiveのLatency InvestigationをCloseした記録
- `2026-10-06-multi-provider-development/` — 既使用350-case Routing SetでのLaya Multilingual / Strands Decider 2B v21 Development比較。LayaはRaw Accuracy 41.14%でReject、StrandsはRaw 99.714%、threshold 0.50でAccepted Error 0・Coverage 98.286%、p50 3.51sとなり、新Fresh Holdoutへ進めるCandidateとした記録

最初の 3 件は Recording Policy 導入後に Backfill した記録である。元の `results/` Raw Artifact はローカルのまま Git 管理対象外だが、実際に観測された意思決定関連の Metrics、実行条件、解釈をこのディレクトリに保存している。
