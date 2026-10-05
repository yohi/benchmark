from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from systemone_bench.spike_analysis import (
    analyze,
    load_rows,
    pearson,
)


def row(
    latency: float,
    cpu_freq: float,
    load1: float,
    cpu_percent: float,
    position: int,
) -> dict:
    return {
        "latency_ms": latency,
        "case_id": f"case-{position}",
        "repeat": 1,
        "profile": "synthetic-1",
        "trial_order": 1,
        "position": position,
        "request_telemetry": {
            "before": {
                "cpu_frequency": {
                    "current_mhz_mean": cpu_freq,
                },
                "load_average": {"load1": load1},
                "temperature": {"max_c": None},
                "ollama": {"rss_bytes_total": 1000},
                "system_memory": {"available_bytes": 1000000},
            },
            "after": {
                "cpu_frequency": {
                    "current_mhz_mean": cpu_freq,
                },
                "load_average": {"load1": load1},
                "temperature": {"max_c": None},
                "ollama": {"rss_bytes_total": 1000},
            },
            "derived": {
                "ollama_cpu_percent_over_request": cpu_percent,
                "ollama_process_identity_changed": False,
            },
        },
    }


class SpikeAnalysisTests(unittest.TestCase):
    def test_pearson_detects_positive_relationship(self) -> None:
        result = pearson([1.0, 2.0, 3.0], [2.0, 4.0, 6.0])
        self.assertAlmostEqual(result, 1.0)

    def test_analyze_separates_spikes_from_normal_requests(self) -> None:
        rows = [
            row(100.0, 3000.0, 1.0, 100.0, 1),
            row(100.0, 3000.0, 1.0, 100.0, 2),
            row(100.0, 3000.0, 1.0, 100.0, 3),
            row(200.0, 2000.0, 2.0, 200.0, 4),
        ]

        result = analyze(rows, spike_multiplier=1.25, top=2)

        self.assertEqual(result["median_latency_ms"], 100.0)
        self.assertEqual(result["spike_threshold_ms"], 125.0)
        self.assertEqual(result["spike_count"], 1)
        self.assertEqual(
            result["top_latency_requests"][0]["case_id"],
            "case-4",
        )
        self.assertEqual(
            result["metrics"]["cpu_freq_before_mhz"]["spikes"]["mean"],
            2000.0,
        )

    def test_analyze_reports_trial_stratification(self) -> None:
        rows = [
            row(100.0, 3000.0, 1.0, 100.0, 1),
            row(100.0, 3000.0, 1.0, 100.0, 2),
            row(200.0, 2000.0, 2.0, 200.0, 3),
            row(100.0, 3000.0, 1.0, 100.0, 4),
        ]
        rows[2]["trial_order"] = 2
        rows[3]["trial_order"] = 2

        result = analyze(rows, spike_multiplier=1.25, top=2)

        self.assertEqual(result["by_trial"]["1"]["spike_count"], 0)
        self.assertEqual(result["by_trial"]["2"]["spike_count"], 1)
        self.assertEqual(result["by_trial"]["2"]["requests"], 2)

    def test_load_rows_ignores_rows_without_telemetry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "details.jsonl"
            path.write_text(
                "\n".join(
                    [
                        json.dumps({"latency_ms": 100.0}),
                        json.dumps(row(200.0, 2000.0, 2.0, 200.0, 2)),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            result = load_rows(path)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["latency_ms"], 200.0)


if __name__ == "__main__":
    unittest.main()
