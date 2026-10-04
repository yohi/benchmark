from __future__ import annotations

import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASETS = ROOT / "datasets"
DATASET = DATASETS / "engineering-routing-policy-fresh-holdout.jsonl"

EXPECTED_COUNTS = {
    "implementation": 20,
    "debug": 20,
    "review": 20,
    "research": 20,
    "planning": 20,
    "documentation": 20,
    "deterministic": 20,
}
EXPECTED_LABELS = set(EXPECTED_COUNTS)
ROUTING_LABELS = set(EXPECTED_COUNTS)


def load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


class PolicyFreshHoldoutDatasetTests(unittest.TestCase):
    def test_dataset_is_balanced_unique_and_complete(self) -> None:
        rows = load_jsonl(DATASET)

        self.assertEqual(len(rows), 140)
        self.assertEqual(len({row["id"] for row in rows}), 140)
        self.assertEqual(len({row["state"]["task"] for row in rows}), 140)
        self.assertEqual(
            Counter(row["expected"]["route"] for row in rows),
            Counter(EXPECTED_COUNTS),
        )

    def test_schema_and_frozen_policy_metadata(self) -> None:
        rows = load_jsonl(DATASET)

        for row in rows:
            expected = row["expected"]["route"]
            metadata = row["metadata"]
            question = row["questions"]["route"]

            self.assertIn(expected, EXPECTED_LABELS)
            self.assertEqual(metadata["split"], "policy-fresh-holdout")
            self.assertEqual(metadata["label"], expected)
            self.assertEqual(
                metadata["derivation"],
                "abstracted_from_distinct_real_request_pattern",
            )
            self.assertEqual(metadata["language"], "ja-mixed")
            self.assertTrue(metadata["source_family"])
            self.assertTrue(metadata["task_shape"])

            frozen = metadata["policy_frozen_before_run"]
            self.assertEqual(frozen["default_threshold"], 0.60)
            self.assertEqual(
                frozen["predicted_label_thresholds"],
                {"planning": 0.80},
            )

            self.assertEqual(question["type"], "choice")
            self.assertEqual(set(question["criteria"]), ROUTING_LABELS)

    def test_tasks_do_not_overlap_prior_sets(self) -> None:
        fresh = load_jsonl(DATASET)
        prior_paths = [
            DATASETS / "engineering-routing-golden.jsonl",
            DATASETS / "engineering-routing-validation.jsonl",
            DATASETS / "engineering-routing-implementation-boundary.jsonl",
            DATASETS / "engineering-routing-production-derived-fresh.jsonl",
        ]

        prior_tasks = {
            row["state"]["task"]
            for path in prior_paths
            for row in load_jsonl(path)
        }
        fresh_tasks = {row["state"]["task"] for row in fresh}

        self.assertFalse(fresh_tasks & prior_tasks)


if __name__ == "__main__":
    unittest.main()
