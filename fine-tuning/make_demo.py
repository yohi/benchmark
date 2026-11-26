"""Synthetic plumbing fixture, not evidence of generalization."""
import argparse
import json
from pathlib import Path

def main():
    p = argparse.ArgumentParser()
    p.add_argument("output")
    out = Path(p.parse_args().output)
    out.mkdir(parents=True, exist_ok=False)
    topics = [("session", "close"), ("token", "refresh"), ("file", "read"),
              ("cache", "evict"), ("database", "connect"), ("queue", "drain"),
              ("socket", "bind"), ("index", "rebuild"), ("lock", "release")]
    for split, subset in zip(("train","dev","test"), (topics[:5],topics[5:7],topics[7:])):
        rows = []
        for noun, verb in subset:
            for n, (code, label) in enumerate([
                (f"def {verb}_{noun}(): pass", "relevant"),
                (f"def inspect_{noun}(): pass", "irrelevant"),
                (f"def {verb}_unrelated(): pass", "irrelevant")]):
                rows.append({"id":f"{noun}-{n}", "group":noun,
                             "input":{"query":f"{verb} the {noun}", "candidate":code}, "label":label})
        (out/f"{split}.jsonl").write_text("".join(json.dumps(r)+"\n" for r in rows), encoding="utf-8")
if __name__ == "__main__":
    main()
