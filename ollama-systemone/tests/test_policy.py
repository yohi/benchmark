from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from systemone_bench.policy import (
    collapse_equivalent_policies,
    explore_policies,
    load_policy_details,
    parse_label_grid,
    simulate_policy,
)


class PredictedLabelPolicyTests(unittest.TestCase):
    def test_parse_label_grid_supports_threshold_ranges(self) -> None:
        label, grid = parse_label_grid("planning=0.60:0.75:0.05,0.90")
        self.assertEqual(label, "planning")
        self.assertEqual(grid, [0.6, 0.65, 0.7, 0.75, 0.9])


    def test_policy_loader_allows_multiple_questions_per_request(self) -> None:
        rows = [
            {
                "model": "nimble",
                "case_id": "case-1",
                "pass": 1,
                "question": "route-a",
                "prediction": "review",
                "expected": "review",
                "correct": True,
                "confidence": 0.9,
            },
            {
                "model": "nimble",
                "case_id": "case-1",
                "pass": 1,
                "question": "route-b",
                "prediction": "planning",
                "expected": "planning",
                "correct": True,
                "confidence": 0.8,
            },
        ]

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "details.jsonl"
            path.write_text(
                "".join(json.dumps(row) + "\n" for row in rows),
                encoding="utf-8",
            )
            loaded = load_policy_details([path])

        self.assertEqual(len(loaded["nimble"]), 2)

    def test_policy_uses_predicted_label_threshold(self) -> None:
        keys = [
            ("case-1", 1, "route"),
            ("case-2", 1, "route"),
            ("case-3", 1, "route"),
        ]
        rows = {
            keys[0]: {
                "prediction": "planning",
                "expected": "debug",
                "confidence": 0.64,
                "correct": False,
                "latency_ms": 10.0,
            },
            keys[1]: {
                "prediction": "planning",
                "expected": "planning",
                "confidence": 0.90,
                "correct": True,
                "latency_ms": 10.0,
            },
            keys[2]: {
                "prediction": "review",
                "expected": "review",
                "confidence": 0.61,
                "correct": True,
                "latency_ms": 10.0,
            },
        }

        result = simulate_policy(
            rows,
            keys,
            default_threshold=0.60,
            label_thresholds={"planning": 0.75},
        )

        self.assertEqual(result["local_accepted"], 2)
        self.assertAlmostEqual(result["local_coverage"], 2 / 3)
        self.assertEqual(result["accepted_accuracy"], 1.0)
        self.assertEqual(result["fallback_count"], 1)
        self.assertEqual(result["accepted_errors"], [])
        self.assertEqual(result["by_predicted"]["planning"]["accepted"], 1)

    def test_exploration_finds_safe_planning_override(self) -> None:
        keys = [
            ("case-1", 1, "route"),
            ("case-2", 1, "route"),
            ("case-3", 1, "route"),
            ("case-4", 1, "route"),
        ]
        rows = {
            keys[0]: {
                "prediction": "planning",
                "expected": "debug",
                "confidence": 0.64,
                "correct": False,
                "latency_ms": 10.0,
            },
            keys[1]: {
                "prediction": "planning",
                "expected": "documentation",
                "confidence": 0.74,
                "correct": False,
                "latency_ms": 10.0,
            },
            keys[2]: {
                "prediction": "planning",
                "expected": "planning",
                "confidence": 0.86,
                "correct": True,
                "latency_ms": 10.0,
            },
            keys[3]: {
                "prediction": "review",
                "expected": "review",
                "confidence": 0.80,
                "correct": True,
                "latency_ms": 10.0,
            },
        }

        ranked, evaluated = explore_policies(
            rows,
            keys,
            default_threshold=0.60,
            label_grids={"planning": [0.60, 0.65, 0.70, 0.75, 0.80]},
            min_accepted_accuracy=1.0,
        )

        self.assertEqual(evaluated, 5)
        self.assertTrue(ranked)
        self.assertEqual(ranked[0]["accepted_accuracy"], 1.0)
        self.assertEqual(ranked[0]["local_accepted"], 2)
        self.assertEqual(
            ranked[0]["threshold_ranges"]["planning"],
            {"min": 0.75, "max": 0.80},
        )

    def test_collapse_equivalent_policies_preserves_threshold_plateau(self) -> None:
        rows = [
            {
                "thresholds": {
                    "default": 0.60,
                    "by_predicted": {"planning": 0.75},
                },
                "local_coverage": 0.9,
                "accepted_accuracy": 1.0,
                "fallback_rate": 0.1,
                "accepted_errors": [],
                "_route_signature": ["accept", "fallback"],
            },
            {
                "thresholds": {
                    "default": 0.60,
                    "by_predicted": {"planning": 0.80},
                },
                "local_coverage": 0.9,
                "accepted_accuracy": 1.0,
                "fallback_rate": 0.1,
                "accepted_errors": [],
                "_route_signature": ["accept", "fallback"],
            },
        ]

        collapsed = collapse_equivalent_policies(rows, ["planning"])

        self.assertEqual(len(collapsed), 1)
        self.assertEqual(
            collapsed[0]["threshold_ranges"]["planning"],
            {"min": 0.75, "max": 0.80},
        )
        self.assertEqual(
            collapsed[0]["thresholds"]["by_predicted"]["planning"],
            0.80,
        )
        self.assertEqual(collapsed[0]["equivalent_configurations"], 2)
        self.assertNotIn("_route_signature", collapsed[0])


if __name__ == "__main__":
    unittest.main()
