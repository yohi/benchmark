from __future__ import annotations

import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASETS = ROOT / "datasets"
DATASET = DATASETS / "engineering-routing-production-derived-fresh.jsonl"

EXPECTED_COUNTS = {
    "implementation": 30,
    "debug": 25,
    "review": 20,
    "research": 20,
    "planning": 20,
    "documentation": 15,
    "deterministic": 10,
}
EXPECTED_LABELS = set(EXPECTED_COUNTS)
ROUTING_LABELS = {
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


class ProductionDerivedFreshDatasetTests(unittest.TestCase):
    def test_dataset_shape_and_distribution(self) -> None:
        rows = load_jsonl(DATASET)

        self.assertEqual(len(rows), 140)
        self.assertEqual(len({row["id"] for row in rows}), 140)
        self.assertEqual(len({row["state"]["task"] for row in rows}), 140)

        counts = Counter(row["expected"]["route"] for row in rows)
        self.assertEqual(counts, Counter(EXPECTED_COUNTS))

    def test_schema_and_provenance_metadata(self) -> None:
        rows = load_jsonl(DATASET)

        for row in rows:
            expected = row["expected"]["route"]
            metadata = row["metadata"]
            question = row["questions"]["route"]

            self.assertIn(expected, EXPECTED_LABELS)
            self.assertEqual(metadata["split"], "production-derived-fresh")
            self.assertEqual(metadata["label"], expected)
            self.assertEqual(
                metadata["derivation"],
                "abstracted_from_real_request",
            )
            self.assertEqual(metadata["language"], "ja-mixed")
            self.assertTrue(metadata["source_family"])
            self.assertTrue(metadata["task_shape"])

            self.assertEqual(question["type"], "choice")
            self.assertEqual(set(question["criteria"]), ROUTING_LABELS)

    def test_tasks_do_not_overlap_existing_benchmark_sets(self) -> None:
        fresh = load_jsonl(DATASET)
        existing_paths = [
            DATASETS / "engineering-routing-golden.jsonl",
            DATASETS / "engineering-routing-validation.jsonl",
            DATASETS / "engineering-routing-implementation-boundary.jsonl",
        ]

        existing_tasks = {
            row["state"]["task"]
            for path in existing_paths
            for row in load_jsonl(path)
        }
        fresh_tasks = {row["state"]["task"] for row in fresh}

        self.assertFalse(fresh_tasks & existing_tasks)


if __name__ == "__main__":
    unittest.main()
