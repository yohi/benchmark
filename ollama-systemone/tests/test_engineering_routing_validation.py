from __future__ import annotations

import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASETS = ROOT / "datasets"
LABELS = {
    "implementation",
    "review",
    "research",
    "debug",
    "planning",
    "documentation",
    "deterministic",
}


def load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


class EngineeringRoutingValidationDatasetTests(unittest.TestCase):
    def test_validation_set_is_balanced_and_unique(self) -> None:
        rows = load_jsonl(DATASETS / "engineering-routing-validation.jsonl")

        self.assertEqual(len(rows), 210)
        self.assertEqual(len({row["id"] for row in rows}), 210)
        self.assertEqual(len({row["state"]["task"] for row in rows}), 210)

        counts = Counter(row["expected"]["route"] for row in rows)
        self.assertEqual(counts, Counter({label: 30 for label in LABELS}))

    def test_validation_schema_and_metadata_are_consistent(self) -> None:
        rows = load_jsonl(DATASETS / "engineering-routing-validation.jsonl")

        for row in rows:
            expected = row["expected"]["route"]
            self.assertIn(expected, LABELS)
            self.assertEqual(row["metadata"]["split"], "validation")
            self.assertEqual(row["metadata"]["label"], expected)
            self.assertEqual(row["questions"]["route"]["type"], "choice")
            self.assertEqual(
                set(row["questions"]["route"]["criteria"]),
                LABELS,
            )

    def test_validation_tasks_do_not_duplicate_development_set(self) -> None:
        validation = load_jsonl(DATASETS / "engineering-routing-validation.jsonl")
        development = load_jsonl(DATASETS / "engineering-routing-golden.jsonl")

        validation_tasks = {row["state"]["task"] for row in validation}
        development_tasks = {row["state"]["task"] for row in development}
        self.assertFalse(validation_tasks & development_tasks)


if __name__ == "__main__":
    unittest.main()
