"""Offline dataset validation and classification evaluation."""
import argparse
import hashlib
import json
from pathlib import Path


def load(path):
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows or any(not isinstance(r, dict) for r in rows):
        raise ValueError("expected nonempty JSONL objects")
    return rows


def validate(paths):
    seen = {key: set() for key in ("id", "group", "input")}
    for path in paths:
        current = {key: set() for key in seen}
        for row in load(path):
            for key in ("id", "group", "label"):
                if not isinstance(row.get(key), str) or not row[key].strip():
                    raise ValueError(f"invalid {key}")
            if not isinstance(row.get("input"), dict) or not row["input"]:
                raise ValueError("invalid input")
            values = {"id": row["id"], "group": row["group"],
                      "input": json.dumps(row["input"], sort_keys=True, ensure_ascii=False)}
            for key, value in values.items():
                if value in seen[key] or (key == "id" and value in current[key]):
                    raise ValueError(f"duplicate or cross-split {key}")
                current[key].add(value)
        for key in seen:
            seen[key].update(current[key])
    return {"status": "VALIDATED", "sha256": [hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths]}


def evaluate(dataset, predictions):
    validate([dataset])
    truth = {r["id"]: r["label"] for r in load(dataset)}
    pred = {}
    for row in load(predictions):
        key, label = row.get("id"), row.get("label")
        if not isinstance(key, str) or key in pred or not isinstance(label, str) or not label.strip():
            raise ValueError("invalid or duplicate prediction")
        pred[key] = label
    if truth.keys() != pred.keys():
        raise ValueError("prediction IDs must match dataset")
    correct = sum(truth[k] == pred[k] for k in truth)
    return {"count": len(truth), "correct": correct, "accuracy": correct / len(truth)}


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    v = sub.add_parser("validate")
    v.add_argument("splits", nargs=3)
    e = sub.add_parser("evaluate")
    e.add_argument("dataset")
    e.add_argument("predictions")
    args = parser.parse_args()
    try:
        result = validate(args.splits) if args.command == "validate" else evaluate(args.dataset, args.predictions)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"error: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
