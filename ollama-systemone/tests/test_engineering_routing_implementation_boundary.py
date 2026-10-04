from __future__ import annotations

import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASETS = ROOT / "datasets"
EXPECTED_LABELS = {
    "implementation",
    "review",
    "research",
    "debug",
    "planning",
}


def load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


class ImplementationBoundaryDatasetTests(unittest.TestCase):
    def test_boundary_set_is_balanced_and_unique(self) -> None:
        rows = load_jsonl(
            DATASETS / "engineering-routing-implementation-boundary.jsonl"
        )

        self.assertEqual(len(rows), 125)
        self.assertEqual(len({row["id"] for row in rows}), 125)
        self.assertEqual(len({row["state"]["task"] for row in rows}), 125)

        counts = Counter(row["expected"]["route"] for row in rows)
        self.assertEqual(
            counts,
            Counter({label: 25 for label in EXPECTED_LABELS}),
        )

    def test_boundary_metadata_and_schema_are_consistent(self) -> None:
        rows = load_jsonl(
            DATASETS / "engineering-routing-implementation-boundary.jsonl"
        )

        for row in rows:
            expected = row["expected"]["route"]
            self.assertIn(expected, EXPECTED_LABELS)
            self.assertEqual(row["metadata"]["split"], "adversarial")
            self.assertEqual(row["metadata"]["label"], expected)
            self.assertEqual(
                row["metadata"]["boundary_with"],
                "implementation",
            )
            self.assertEqual(row["questions"]["route"]["type"], "choice")
            self.assertEqual(
                set(row["questions"]["route"]["criteria"]),
                {
                    "implementation",
                    "review",
                    "research",
                    "debug",
                    "planning",
                    "documentation",
                    "deterministic",
                },
            )

    def test_boundary_tasks_do_not_overlap_existing_sets(self) -> None:
        boundary = load_jsonl(
            DATASETS / "engineering-routing-implementation-boundary.jsonl"
        )
        golden = load_jsonl(DATASETS / "engineering-routing-golden.jsonl")
        validation = load_jsonl(
            DATASETS / "engineering-routing-validation.jsonl"
        )

        boundary_tasks = {row["state"]["task"] for row in boundary}
        existing_tasks = {
            row["state"]["task"]
            for row in golden + validation
        }
        self.assertFalse(boundary_tasks & existing_tasks)


if __name__ == "__main__":
    unittest.main()
