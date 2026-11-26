# First runnable training experiment

This is a full-weight small encoder classifier, not LoRA. Ranking uses a binary relevance head (cross-encoder). No product integration. Synthetic demo only; real Nexus data is not included.

## Local or Colab shell
From fine-tuning/ with Python 3.11+:
```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-ml.txt
python -m unittest discover -s tests -v
python make_demo.py data/demo
```
Select a small pretrained encoder (e.g. distilbert/distilbert-base-uncased for English plumbing only), resolve its exact Hugging Face commit revision, and set MODEL and REV to those values. Check license before use. For Japanese production experiments select a multilingual encoder. The initial classification head is randomly initialized; baseline is not an existing trained reranker.

```sh
python mvp.py train --model "$MODEL" --revision "$REV" --train data/demo/train.jsonl --dev data/demo/dev.jsonl --test data/demo/test.jsonl --output artifacts/demo --device cuda
```
Use --device cpu for local smoke. Copy the complete artifacts/demo directory back to the home PC before stopping Colab. No automatic upload or GPU allocation.
```sh
python mvp.py evaluate --model artifacts/demo --test data/demo/test.jsonl --device cpu
python mvp.py predict --model artifacts/demo --query 'release the lock' --candidate 'def release_lock(): pass'
```
For Justice or Chronos classification use --task classification consistently and provide labeled query/candidate pairs. Keep test sealed until model selection. The demo is tiny and cannot establish practical quality. Compare real Nexus existing ranking and a pretrained reranker separately before adoption. Dependency ranges are not a reproducible lock; record pip freeze and source commit for real runs. Native safetensors CPU inference is supported by design; ONNX/GGUF not implemented. No live training or dependency installation has been verified by this commit.
