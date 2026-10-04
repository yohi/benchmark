from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from systemone_bench.latency_tail import (
    analyze,
    late_tail_count,
    load_request_rows,
    position_buckets,
    prefix_analysis,
    top_outliers,
)


class LatencyTailTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rows = [
            {
                "position": index + 1,
                "case_id": f"case-{index + 1}",
                "pass": 1,
                "latency_ms": latency,
                "expected": "implementation",
                "prediction": "implementation",
                "correct": True,
                "confidence": 0.9,
                "metadata": {
                    "source_family": "test",
                    "scenario_family": "scenario",
                },
            }
            for index, latency in enumerate(
                [30000, 25000, 15000, 15100, 14900, 15200, 15050, 14850, 15150, 15000]
            )
        ]

    def test_prefix_analysis_detects_slow_start(self) -> None:
        result = prefix_analysis(self.rows, [2])
        self.assertEqual(len(result), 1)
        self.assertGreater(result[0]["mean_ratio"], 1.5)

    def test_position_buckets_preserve_request_order(self) -> None:
        result = position_buckets(self.rows, 2)
        self.assertEqual(result[0]["start_position"], 1)
        self.assertEqual(result[0]["end_position"], 5)
        self.assertEqual(result[1]["start_position"], 6)
        self.assertEqual(result[1]["end_position"], 10)

    def test_top_outliers_are_ranked_by_latency(self) -> None:
        result = top_outliers(self.rows, 2)
        self.assertEqual([row["position"] for row in result], [1, 2])

    def test_late_tail_excludes_early_startup_requests(self) -> None:
        result = late_tail_count(
            self.rows,
            start_position=3,
            multiplier=1.5,
        )
        self.assertEqual(result["tail_count"], 0)

    def test_load_request_rows_deduplicates_questions(self) -> None:
        data = [
            {
                "model": "nimble",
                "case_id": "case-1",
                "pass": 1,
                "question": "q1",
                "latency_ms": 100,
            },
            {
                "model": "nimble",
                "case_id": "case-1",
                "pass": 1,
                "question": "q2",
                "latency_ms": 100,
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "details.jsonl"
            path.write_text(
                "".join(json.dumps(row) + "\n" for row in data),
                encoding="utf-8",
            )
            rows = load_request_rows(path, "nimble")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["latency_ms"], 100.0)

    def test_analyze_detects_prefix_tail_when_bucket_median_does_not(self) -> None:
        latencies = [
            30000,
            30000,
            15000,
            15000,
            15000,
            15000,
            15000,
            15000,
            15000,
            15000,
        ]
        data = [
            {
                "model": "nimble",
                "case_id": f"case-{index + 1}",
                "pass": 1,
                "question": "route",
                "latency_ms": latency,
                "expected": "implementation",
                "prediction": "implementation",
                "correct": True,
                "confidence": 0.9,
                "metadata": {
                    "source_family": "test",
                    "scenario_family": "scenario",
                },
            }
            for index, latency in enumerate(latencies)
        ]

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "details.jsonl"
            path.write_text(
                "".join(json.dumps(row) + "\n" for row in data),
                encoding="utf-8",
            )
            result = analyze(
                path,
                "nimble",
                prefixes=[5],
                buckets=2,
                top=5,
                late_start=6,
                tail_multiplier=1.5,
            )

        self.assertFalse(
            result["diagnostics"]["first_bucket_median_warmup_like"]
        )
        self.assertTrue(
            result["diagnostics"]["prefix_concentrated_tail"]
        )
        self.assertEqual(
            result["diagnostics"]["strongest_early_prefix"]["prefix_requests"],
            5,
        )
        self.assertEqual(result["late_tail"]["tail_count"], 0)

    def test_analyze_flags_warmup_like_first_bucket(self) -> None:
        data = []
        for row in self.rows:
            data.append(
                {
                    "model": "nimble",
                    "case_id": row["case_id"],
                    "pass": 1,
                    "question": "route",
                    "latency_ms": row["latency_ms"],
                    "expected": row["expected"],
                    "prediction": row["prediction"],
                    "correct": row["correct"],
                    "confidence": row["confidence"],
                    "metadata": row["metadata"],
                }
            )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "details.jsonl"
            path.write_text(
                "".join(json.dumps(row) + "\n" for row in data),
                encoding="utf-8",
            )
            result = analyze(
                path,
                "nimble",
                prefixes=[2],
                buckets=5,
                top=2,
                late_start=3,
                tail_multiplier=1.5,
            )

        self.assertTrue(
            result["diagnostics"]["first_bucket_median_warmup_like"]
        )
        self.assertEqual(result["top_outliers"][0]["position"], 1)


if __name__ == "__main__":
    unittest.main()
