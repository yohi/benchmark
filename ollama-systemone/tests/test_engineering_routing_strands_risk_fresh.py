from __future__ import annotations

import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASETS = ROOT / "datasets"
DATASET = DATASETS / "engineering-routing-strands-risk-fresh.jsonl"

EXPECTED_COUNTS = {
    "implementation": 50,
    "debug": 50,
    "review": 50,
    "research": 50,
    "planning": 50,
    "documentation": 50,
    "deterministic": 50,
}
EXPECTED_LABELS = set(EXPECTED_COUNTS)
EXPECTED_PROVIDER = "strands-decider-2b-v21"
EXPECTED_CHECKPOINT = "StrandsAgents/strands-decider-2B-hobson-v21"


def load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


class StrandsRiskFreshDatasetTests(unittest.TestCase):
    def test_dataset_is_balanced_unique_and_complete(self) -> None:
        rows = load_jsonl(DATASET)

        self.assertEqual(len(rows), 350)
        self.assertEqual(len({row["id"] for row in rows}), 350)
        self.assertEqual(len({row["state"]["task"] for row in rows}), 350)
        self.assertEqual(
            Counter(row["expected"]["route"] for row in rows),
            Counter(EXPECTED_COUNTS),
        )

    def test_schema_and_frozen_policy_metadata(self) -> None:
        rows = load_jsonl(DATASET)

        scenario_variants: Counter[tuple[str, str]] = Counter()
        for row in rows:
            expected = row["expected"]["route"]
            metadata = row["metadata"]
            question = row["questions"]["route"]

            self.assertIn(expected, EXPECTED_LABELS)
            self.assertEqual(
                metadata["split"],
                "strands-single-policy-risk-fresh-holdout",
            )
            self.assertEqual(metadata["label"], expected)
            self.assertEqual(metadata["language"], "ja-mixed")
            self.assertEqual(
                metadata["derivation"],
                "paired_action_boundary_from_new_engineering_scenario",
            )

            frozen = metadata["policy_frozen_before_run"]
            self.assertEqual(frozen["provider"], EXPECTED_PROVIDER)
            self.assertEqual(frozen["model"], EXPECTED_PROVIDER)
            self.assertEqual(frozen["checkpoint"], EXPECTED_CHECKPOINT)
            self.assertEqual(frozen["threshold"], 0.50)
            self.assertEqual(frozen["max_accepted_risk"], 0.01)
            self.assertEqual(frozen["confidence_level"], 0.95)
            self.assertEqual(frozen["candidate_count"], 1)
            self.assertEqual(
                frozen["multiple_testing_correction"],
                "none-single-predeclared-policy",
            )

            self.assertEqual(question["type"], "choice")
            self.assertEqual(set(question["criteria"]), EXPECTED_LABELS)

            scenario_variants[
                (metadata["scenario_family"], expected)
            ] += 1

        self.assertEqual(len({key[0] for key in scenario_variants}), 25)
        self.assertTrue(all(count == 2 for count in scenario_variants.values()))

    def test_tasks_do_not_overlap_any_prior_routing_set(self) -> None:
        fresh = load_jsonl(DATASET)
        prior_paths = [
            DATASETS / "engineering-routing-golden.jsonl",
            DATASETS / "engineering-routing-validation.jsonl",
            DATASETS / "engineering-routing-implementation-boundary.jsonl",
            DATASETS / "engineering-routing-production-derived-fresh.jsonl",
            DATASETS / "engineering-routing-policy-fresh-holdout.jsonl",
            DATASETS / "engineering-routing-single-policy-risk-fresh.jsonl",
        ]

        prior_tasks = {
            row["state"]["task"]
            for path in prior_paths
            for row in load_jsonl(path)
        }
        fresh_tasks = {row["state"]["task"] for row in fresh}

        self.assertFalse(fresh_tasks & prior_tasks)

    def test_scenario_families_are_new_relative_to_nimble_risk_holdout(self) -> None:
        fresh = load_jsonl(DATASET)
        prior = load_jsonl(
            DATASETS / "engineering-routing-single-policy-risk-fresh.jsonl"
        )

        fresh_families = {
            row["metadata"]["scenario_family"] for row in fresh
        }
        prior_families = {
            row["metadata"]["scenario_family"] for row in prior
        }

        self.assertFalse(fresh_families & prior_families)


if __name__ == "__main__":
    unittest.main()
