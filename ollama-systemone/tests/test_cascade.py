from __future__ import annotations

import unittest

from systemone_bench.cascade import parse_threshold_grid, pareto_frontier, simulate


class CascadeTests(unittest.TestCase):
    def test_parse_threshold_grid_supports_ranges_and_values(self) -> None:
        self.assertEqual(
            parse_threshold_grid("0.60:0.70:0.05,0.90"),
            [0.6, 0.65, 0.7, 0.9],
        )

    def test_two_stage_cascade_metrics(self) -> None:
        keys = [
            ("case-1", 1, "route"),
            ("case-2", 1, "route"),
            ("case-3", 1, "route"),
        ]
        by_model = {
            "fast": {
                keys[0]: {"confidence": 0.80, "correct": True, "latency_ms": 10.0},
                keys[1]: {"confidence": 0.60, "correct": False, "latency_ms": 10.0},
                keys[2]: {"confidence": 0.40, "correct": True, "latency_ms": 10.0},
            },
            "strong": {
                keys[0]: {"confidence": 0.95, "correct": True, "latency_ms": 20.0},
                keys[1]: {"confidence": 0.80, "correct": True, "latency_ms": 20.0},
                keys[2]: {"confidence": 0.30, "correct": False, "latency_ms": 20.0},
            },
        }

        result = simulate(
            by_model,
            keys,
            ["fast", "strong"],
            (0.70, 0.70),
            fallback_latency_ms=100.0,
        )

        self.assertAlmostEqual(result["local_coverage"], 2 / 3)
        self.assertEqual(result["accepted_accuracy"], 1.0)
        self.assertAlmostEqual(result["fallback_rate"], 1 / 3)
        self.assertAlmostEqual(result["avg_local_latency_ms"], 70 / 3)
        self.assertAlmostEqual(result["local_calls_per_request"], 5 / 3)
        self.assertAlmostEqual(result["total_calls_per_request"], 2.0)
        self.assertAlmostEqual(result["avg_end_to_end_latency_ms"], 170 / 3)
        self.assertEqual(result["stages"]["fast"]["accepted"], 1)
        self.assertEqual(result["stages"]["strong"]["accepted"], 1)

    def test_pareto_frontier_removes_dominated_configuration(self) -> None:
        rows = [
            {"local_coverage": 0.90, "avg_local_latency_ms": 20.0, "local_calls_per_request": 1.5},
            {"local_coverage": 0.90, "avg_local_latency_ms": 25.0, "local_calls_per_request": 1.6},
            {"local_coverage": 0.80, "avg_local_latency_ms": 10.0, "local_calls_per_request": 1.0},
        ]
        frontier = pareto_frontier(rows)
        self.assertIn(rows[0], frontier)
        self.assertNotIn(rows[1], frontier)
        self.assertIn(rows[2], frontier)


if __name__ == "__main__":
    unittest.main()
