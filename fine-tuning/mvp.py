"""Small supervised classifier / pairwise relevance scorer. Explicit local output."""
import argparse
import hashlib
import json
import math
import random
import time
from pathlib import Path
from lab import load, validate


def metrics(rows, scores, labels, task):
    pred = [labels[max(range(len(s)), key=s.__getitem__)] for s in scores]
    result = {"accuracy": sum(p == r["label"] for p, r in zip(pred, rows)) / len(rows)}
    if task == "ranking":
        groups = {}
        for row, score in zip(rows, scores):
            groups.setdefault(row["group"], []).append((score[labels.index("relevant")], row["label"]))
        rr, ndcg, recall = [], [], []
        for items in groups.values():
            ranked = sorted(items, key=lambda x: -x[0])
            hits = [int(label == "relevant") for _, label in ranked]
            total = sum(hits)
            if not total:
                raise ValueError("ranking group lacks relevant candidate")
            rr.append(1 / (hits.index(1) + 1))
            ndcg.append(sum(h / math.log2(i + 2) for i, h in enumerate(hits[:5])) /
                        sum(1 / math.log2(i + 2) for i in range(min(total, 5))))
            recall.append(sum(hits[:5]) / total)
        result.update(mrr=sum(rr)/len(rr), ndcg_at_5=sum(ndcg)/len(ndcg), recall_at_5=sum(recall)/len(recall))
    return result


def pair(row):
    x = row["input"]
    if not isinstance(x.get("query"), str) or not isinstance(x.get("candidate"), str):
        raise ValueError("input requires query and candidate strings")
    return x["query"], x["candidate"]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["train", "evaluate", "predict"])
    p.add_argument("--model", required=True)
    p.add_argument("--revision")
    p.add_argument("--train")
    p.add_argument("--dev")
    p.add_argument("--test")
    p.add_argument("--output")
    p.add_argument("--query")
    p.add_argument("--candidate")
    p.add_argument("--task", choices=["classification", "ranking"], default="ranking")
    p.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    p.add_argument("--epochs", type=int, default=2)
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--max-length", type=int, default=256)
    p.add_argument("--seed", type=int, default=42)
    a = p.parse_args()
    if min(a.epochs, a.batch_size, a.max_length) < 1:
        p.error("positive training parameters required")
    if a.command == "train" and (not all([a.train, a.dev, a.test, a.output, a.revision]) or Path(a.output).exists()):
        p.error("train requires all splits, model revision and new output directory")
    import torch
    import transformers
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    random.seed(a.seed)
    torch.manual_seed(a.seed)
    if a.device == "cuda" and not torch.cuda.is_available():
        p.error("CUDA unavailable")
    kwargs = {"trust_remote_code": False}
    if a.revision:
        kwargs["revision"] = a.revision
    tokenizer = AutoTokenizer.from_pretrained(a.model, **kwargs)
    if a.command == "train":
        evidence = validate([a.train, a.dev, a.test])
        train, dev = load(a.train), load(a.dev)
        labels = sorted({r["label"] for r in train})
        if len(labels) < 2 or any(r["label"] not in labels for r in dev):
            p.error("invalid label vocabulary")
        if a.task == "ranking" and labels != ["irrelevant", "relevant"]:
            p.error("ranking requires irrelevant/relevant labels")
        model = AutoModelForSequenceClassification.from_pretrained(
            a.model, num_labels=len(labels), id2label=dict(enumerate(labels)),
            label2id={v:k for k,v in enumerate(labels)}, **kwargs).to(a.device)
    else:
        model = AutoModelForSequenceClassification.from_pretrained(a.model, **kwargs).to(a.device)
        labels = [model.config.id2label[i] for i in range(model.config.num_labels)]

    def encode(rows):
        pairs = [pair(r) for r in rows]
        return tokenizer([x[0] for x in pairs], [x[1] for x in pairs],
                         padding=True, truncation=True, max_length=a.max_length,
                         return_tensors="pt").to(a.device)

    def score(rows):
        model.eval()
        scores, latency = [], []
        with torch.inference_mode():
            for row in rows:
                start = time.perf_counter()
                scores.append(model(**encode([row])).logits.softmax(-1).cpu().tolist()[0])
                latency.append((time.perf_counter()-start)*1000)
        return scores, sorted(latency)

    def report(rows):
        if any(r["label"] not in labels for r in rows):
            raise ValueError("unknown evaluation label")
        scores, times = score(rows)
        return dict(metrics(rows, scores, labels, a.task),
                    p50_ms=times[math.ceil(len(times)*.5)-1],
                    p95_ms=times[math.ceil(len(times)*.95)-1])

    if a.command == "train":
        before = report(dev)
        optimizer = torch.optim.AdamW(model.parameters(), lr=2e-5)
        start = time.perf_counter()
        for _ in range(a.epochs):
            model.train()
            random.shuffle(train)
            for i in range(0, len(train), a.batch_size):
                batch = train[i:i+a.batch_size]
                target = torch.tensor([labels.index(r["label"]) for r in batch], device=a.device)
                optimizer.zero_grad()
                loss = model(**encode(batch), labels=target).loss
                loss.backward()
                optimizer.step()
        after = report(dev)
        out = Path(a.output)
        out.mkdir(parents=True, exist_ok=False)
        model.save_pretrained(out, safe_serialization=True)
        tokenizer.save_pretrained(out)
        manifest = {"status":"TRAINED_NOT_ADOPTED", "arguments":vars(a),
                    "resolved_model_revision":getattr(model.config, "_commit_hash", None),
                    "dataset_sha256":evidence["sha256"], "dev_before":before, "dev_after":after,
                    "elapsed_seconds":time.perf_counter()-start,
                    "torch":torch.__version__, "transformers":transformers.__version__,
                    "artifact_sha256":{f.name:hashlib.sha256(f.read_bytes()).hexdigest()
                                       for f in out.iterdir() if f.is_file()}}
        (out/"manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(json.dumps(manifest, indent=2))
    elif a.command == "evaluate":
        if not a.test:
            p.error("--test required")
        validate([a.test])
        print(json.dumps(report(load(a.test)), indent=2))
    else:
        if a.query is None or a.candidate is None:
            p.error("--query and --candidate required")
        scores, _ = score([{"input":{"query":a.query,"candidate":a.candidate}}])
        print(json.dumps(dict(zip(labels, scores[0])), indent=2))


if __name__ == "__main__":
    main()
