# Fine-tuning Lab

Justice / Nexus / Chronos-Graph の独立したオフライン学習実験基盤。既存 ollama-systemone は変更しない。

## Quick start
Python 3.11+。このディレクトリで実行する。

```sh
python -m unittest discover -s tests -v
python lab.py validate fixtures/train.jsonl fixtures/dev.jsonl fixtures/test.jsonl
python lab.py evaluate fixtures/test.jsonl fixtures/predictions.jsonl
```

fixture は架空の動作確認用であり、モデル品質の証拠ではない。

## 実験手順
1. projects/ の契約を参考に対象を一つ選び、許可済みデータを Git 管理外の data/ に準備する。
2. train/dev/test をシナリオ・リポジトリ・時間等の group 単位で分離する。validate で ID、group、完全一致入力の重複を検査する。意味的重複は別途確認する。
3. dev でベースモデルと学習候補を比較する。test はモデル・閾値確定後の最終評価専用。
4. Colab 上で学習し、モデルと依存関係、入力ハッシュ、実行条件を回収する。CPU 上でも品質・速度を評価する。
5. Human Owner の採択後のみ各プロダクトに統合する。

## 範囲
現段階はデータ契約、検証、分類評価、実験記録の骨格。実学習バックエンド、ランキング評価、ONNX/GGUF export、自動 GPU 起動は未実装。最初の実験で必要なものだけ追加する。

公開リポジトリに秘密情報、業務コード、実セッションログ、未許可の教師出力、モデル重みを登録しない。既存 System One holdout を学習に流用しない。データの利用権・転送許可を確認する。自動配備・自動承認は禁止。
