# Nexus
候補: Query/Code の Cross-Encoder reranking。候補集合を固定し、既存順位・未学習モデル・学習済みモデルを比較する。
評価: MRR、nDCG@K、Recall@K、CPU p50/p95。query 単位で分割し、hard negatives を用意する。既存検索・索引は変更しない。最初の実験候補。
