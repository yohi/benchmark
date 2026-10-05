from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from systemone_bench.warmup_study import (
    PROFILE_REPRESENTATIVE,
    PROFILE_SYNTHETIC,
    aggregate_profile_trials,
    build_profile_schedule,
    compare_profiles,
    execute_measured_workload,
    representative_warmup_payloads,
    reset_runtime,
    summarize_trial,
)


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "datasets" / "latency-warmup-fixed-workload.jsonl"


class WarmupStudyTests(unittest.TestCase):
    def test_schedule_alternates_profile_order(self) -> None:
        self.assertEqual(
            build_profile_schedule(2),
            [
                (1, PROFILE_SYNTHETIC),
                (1, PROFILE_REPRESENTATIVE),
                (2, PROFILE_REPRESENTATIVE),
                (2, PROFILE_SYNTHETIC),
            ],
        )

    def test_representative_warmups_cover_all_route_labels(self) -> None:
        rows = [
            json.loads(line)
            for line in DATASET.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        question = rows[0]["questions"]["route"]
        payloads = representative_warmup_payloads(
            "nimble",
            question,
            "10m",
        )
        self.assertEqual(len(payloads), 7)
        self.assertEqual(
            {payload["_warmup_label"] for payload in payloads},
            set(question["criteria"]),
        )

    def test_fixed_workload_is_balanced_and_reused_for_latency_only(self) -> None:
        rows = [
            json.loads(line)
            for line in DATASET.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(len(rows), 35)
        self.assertEqual(len({row["id"] for row in rows}), 35)
        self.assertEqual(
            {row["metadata"]["purpose"] for row in rows},
            {"latency-only-reused-workload"},
        )

        counts: dict[str, int] = {}
        scenarios = set()
        for row in rows:
            label = row["expected"]["route"]
            counts[label] = counts.get(label, 0) + 1
            scenarios.add(row["metadata"]["scenario_family"])

        self.assertEqual(set(counts.values()), {5})
        self.assertEqual(len(counts), 7)
        self.assertEqual(len(scenarios), 5)

    def test_summarize_trial_detects_prefix_tail(self) -> None:
        latencies = [
            30000,
            30000,
            30000,
            30000,
            30000,
            *([15000] * 30),
        ]
        rows = [
            {
                "position": index + 1,
                "latency_ms": latency,
            }
            for index, latency in enumerate(latencies)
        ]
        result = summarize_trial(rows)

        self.assertTrue(result["prefix_concentrated_tail"])
        self.assertGreater(result["first_5_mean_ratio"], 1.9)
        self.assertEqual(result["late_tail_count"], 0)

    @patch("systemone_bench.warmup_study.wait_for_ollama")
    @patch("systemone_bench.warmup_study.subprocess.run")
    def test_restart_reset_runs_command_and_waits_for_readiness(
        self,
        run_mock: MagicMock,
        wait_mock: MagicMock,
    ) -> None:
        client = MagicMock()

        result = reset_runtime(
            client=client,
            base_url="http://localhost:11434",
            model="nimble",
            reset_mode="restart",
            restart_command="sudo -n systemctl restart ollama",
            restart_wait=0.0,
            timeout=30.0,
        )

        run_mock.assert_called_once_with(
            ["sudo", "-n", "systemctl", "restart", "ollama"],
            check=True,
        )
        wait_mock.assert_called_once_with(
            client,
            "http://localhost:11434",
            30.0,
        )
        self.assertEqual(result["mode"], "restart")
        self.assertEqual(
            result["restart_command"],
            "sudo -n systemctl restart ollama",
        )

    @patch("systemone_bench.warmup_study.subprocess.run")
    def test_restart_reset_wraps_command_failure(
        self,
        run_mock: MagicMock,
    ) -> None:
        import subprocess

        run_mock.side_effect = subprocess.CalledProcessError(
            1,
            ["sudo", "systemctl", "restart", "ollama"],
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "restart command failed with exit status 1",
        ):
            reset_runtime(
                client=MagicMock(),
                base_url="http://localhost:11434",
                model="nimble",
                reset_mode="restart",
                restart_command="sudo systemctl restart ollama",
                restart_wait=0.0,
                timeout=30.0,
            )

    def test_restart_reset_requires_command(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "restart mode requires --restart-command",
        ):
            reset_runtime(
                client=MagicMock(),
                base_url="http://localhost:11434",
                model="nimble",
                reset_mode="restart",
                restart_command="",
                restart_wait=0.0,
                timeout=30.0,
            )

    @patch("systemone_bench.warmup_study.derive_request_telemetry")
    @patch("systemone_bench.warmup_study.capture_request_telemetry")
    @patch("systemone_bench.warmup_study.psutil.virtual_memory")
    @patch("systemone_bench.warmup_study.psutil.cpu_percent")
    def test_measured_workload_records_opt_in_request_telemetry(
        self,
        cpu_percent_mock: MagicMock,
        virtual_memory_mock: MagicMock,
        capture_mock: MagicMock,
        derive_mock: MagicMock,
    ) -> None:
        cpu_percent_mock.side_effect = [10.0, 20.0]
        virtual_memory_mock.side_effect = [
            MagicMock(used=1000),
            MagicMock(used=2000),
        ]
        capture_mock.side_effect = [{"sample": "before"}, {"sample": "after"}]
        derive_mock.return_value = {"derived": {"sample": True}}

        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "answers": {
                "route": {
                    "choice": "implementation",
                    "confidence": 0.9,
                }
            }
        }
        client = MagicMock()
        client.post.return_value = response

        rows = [
            {
                "id": "case-1",
                "state": {"task": "Implement it."},
                "questions": {
                    "route": {
                        "type": "choice",
                        "instructions": "Classify.",
                        "criteria": {
                            "implementation": "Implement.",
                            "review": "Review.",
                        },
                    }
                },
                "expected": {"route": "implementation"},
                "metadata": {},
            }
        ]

        result = execute_measured_workload(
            client=client,
            base_url="http://localhost:11434",
            model="nimble",
            keep_alive="10m",
            rows=rows,
            repeat=1,
            profile=PROFILE_SYNTHETIC,
            trial_order=1,
            request_telemetry=True,
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(
            result[0]["request_telemetry"],
            {"derived": {"sample": True}},
        )
        self.assertEqual(capture_mock.call_count, 2)
        derive_mock.assert_called_once()

    def test_profile_comparison_reports_reduction(self) -> None:
        synthetic_trials = [
            {
                "summary": {
                    "mean_ms": 20.0,
                    "median_ms": 20.0,
                    "p95_ms": 30.0,
                    "p99_ms": 35.0,
                    "first_1_mean_ms": 30.0,
                    "first_5_mean_ms": 25.0,
                    "first_10_mean_ms": 23.0,
                    "first_20_mean_ms": 22.0,
                    "after_20_mean_ms": 15.0,
                    "first_20_mean_ratio": 22.0 / 15.0,
                    "prefix_concentrated_tail": True,
                    "late_tail_count": 0,
                }
            }
        ]
        representative_trials = [
            {
                "summary": {
                    "mean_ms": 15.0,
                    "median_ms": 15.0,
                    "p95_ms": 16.0,
                    "p99_ms": 17.0,
                    "first_1_mean_ms": 16.0,
                    "first_5_mean_ms": 16.0,
                    "first_10_mean_ms": 15.5,
                    "first_20_mean_ms": 15.5,
                    "after_20_mean_ms": 15.0,
                    "first_20_mean_ratio": 15.5 / 15.0,
                    "prefix_concentrated_tail": False,
                    "late_tail_count": 0,
                }
            }
        ]

        synthetic = aggregate_profile_trials(synthetic_trials)
        representative = aggregate_profile_trials(representative_trials)
        comparison = compare_profiles(synthetic, representative)

        first5 = comparison["first_5_mean_ms_mean_across_trials"]
        self.assertAlmostEqual(first5["representative_over_synthetic"], 0.64)
        self.assertAlmostEqual(first5["reduction_fraction"], 0.36)


if __name__ == "__main__":
    unittest.main()
