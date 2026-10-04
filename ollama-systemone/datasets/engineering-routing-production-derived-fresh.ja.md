# Engineering Routing Production-derived Fresh Dataset

## 目的

この Dataset は、既存 Benchmark Template から生成した Synthetic Case ではなく、実際の Engineering Request のパターンを抽象化して、現在の Routing Policy を評価するためのもの。

これまでの Dataset とは役割が異なる。

- golden: 小規模で再現可能な Development Set を解けるか
- validation: Development Set で選んだ Threshold が大きな Synthetic Holdout に一般化するか
- implementation-boundary: Implementation 関連語彙が近接 Class を誤って引き寄せるか
- production-derived fresh: 実際に近い依頼文・言語・Task Mix でも同じ Policy が維持できるか

## 作成方法

140件の Task は、実際に発生した Engineering Request のパターンを抽象化して作成している。

対象領域の例:

- Application / Framework Development
- CI/CD
- Cloud Infrastructure
- Network
- AI / Model Routing
- Observability
- Repository Review
- Documentation

Private URL、Account Identifier、Secret、認証情報は Dataset に含めない。

保持するのは元会話そのものではなく、

- Engineering Intent
- Request Shape
- Technical Context

のみ。

Metadata には以下の粗い情報だけを保存する。

- `source_family`: 技術・Project 系統
- `task_shape`: 依頼形状
- `derivation=abstracted_from_real_request`
- `language=ja-mixed`

## 言語と Request Shape

実際の利用に合わせ、Task は **日本語中心**。

ただし、実運用と同様に以下は英語のまま混在する。

- Technical Term
- Error Message
- CLI Command
- Config Key
- Library / Service Name
- Log Fragment

含める Request Shape:

- 短い直接依頼
- 制約が多い依頼
- Log / Error 添付後の質問
- Multi-intent Request
- 最新情報の Research
- Code / Config Change
- Review-only
- Planning-only
- Documentation
- Deterministic Operation

## Class Distribution

| Label | Cases |
| --- | ---: |
| implementation | 30 |
| debug | 25 |
| review | 20 |
| research | 20 |
| planning | 20 |
| documentation | 15 |
| deterministic | 10 |
| **total** | **140** |

意図的に均等にはしていない。

Class Balance を最大化するのではなく、観測された Engineering Workload の比重に近づけることを優先している。

## Labeling Rule

**その依頼を今すぐ満たすために必要な Primary Action** を Label とする。

例:

- Failure の原因だけを調べる → `debug`
- 原因を調べたうえで修正まで要求される → `implementation`
- 最新の公式仕様や外部情報を確認する → `research`
- 既存 Diff / Plan を変更せず評価する → `review`
- 将来の実装手順を作るだけ → `planning`
- Product Behavior を変えず説明文だけ更新する → `documentation`
- 抽出・並べ替え・計算・機械的 Command 作成 → `deterministic`

## Evaluation Protocol

この Dataset を実行する前に Current Candidate Policy は固定済み。

- Model: `nimble`
- Threshold: `0.60`

実行:

```bash
uv run systemone-bench \
  --models nimble \
  --dataset datasets/engineering-routing-production-derived-fresh.jsonl \
  --warmup 1 \
  --iterations 1 \
  --cache-reset unload \
  --thresholds 0.55,0.60,0.65,0.70
```

Primary Checkpoint は threshold 0.60。

確認順:

1. 0.60 の Accepted Accuracy
2. 0.60 の Local Coverage
3. Class 別 Accepted Accuracy / Coverage
4. Confusion Matrix
5. 全 Raw Error の Confidence

この結果を見て Threshold や Routing Policy を変更した場合、この Dataset はその時点から Development Evidence として扱う。

変更後の Policy は、別の Fresh Set で再検証する。
