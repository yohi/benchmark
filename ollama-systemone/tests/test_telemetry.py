from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from systemone_bench.telemetry import (
    cpu_frequency_summary,
    derive_request_telemetry,
    temperature_summary,
)


class TelemetryTests(unittest.TestCase):
    def test_derive_request_telemetry_calculates_process_cpu_percent(self) -> None:
        before = {
            "ollama": {
                "cpu_time_seconds_total": 10.0,
                "rss_bytes_total": 1000,
                "create_times": [{"pid": 10, "create_time": 1.0}],
            }
        }
        after = {
            "ollama": {
                "cpu_time_seconds_total": 14.0,
                "rss_bytes_total": 1500,
                "create_times": [{"pid": 10, "create_time": 1.0}],
            }
        }

        result = derive_request_telemetry(before, after, 2000.0)

        self.assertAlmostEqual(
            result["derived"]["ollama_cpu_percent_over_request"],
            200.0,
        )
        self.assertEqual(
            result["derived"]["ollama_rss_delta_bytes"],
            500,
        )
        self.assertFalse(
            result["derived"]["ollama_process_identity_changed"]
        )

    def test_derive_request_telemetry_detects_process_identity_change(self) -> None:
        before = {
            "ollama": {
                "cpu_time_seconds_total": 1.0,
                "rss_bytes_total": 1000,
                "create_times": [{"pid": 10, "create_time": 1.0}],
            }
        }
        after = {
            "ollama": {
                "cpu_time_seconds_total": 1.0,
                "rss_bytes_total": 1000,
                "create_times": [{"pid": 11, "create_time": 2.0}],
            }
        }

        result = derive_request_telemetry(before, after, 1000.0)

        self.assertTrue(
            result["derived"]["ollama_process_identity_changed"]
        )

    @patch("systemone_bench.telemetry.psutil.cpu_freq")
    def test_cpu_frequency_summary_aggregates_per_cpu(
        self,
        cpu_freq_mock: MagicMock,
    ) -> None:
        cpu_freq_mock.return_value = [
            MagicMock(current=1000.0),
            MagicMock(current=2000.0),
            MagicMock(current=3000.0),
        ]

        result = cpu_frequency_summary()

        self.assertEqual(result["current_mhz_mean"], 2000.0)
        self.assertEqual(result["current_mhz_min"], 1000.0)
        self.assertEqual(result["current_mhz_max"], 3000.0)

    @patch("systemone_bench.telemetry.psutil.sensors_temperatures")
    def test_temperature_summary_is_optional(
        self,
        sensors_mock: MagicMock,
    ) -> None:
        sensors_mock.return_value = {}

        result = temperature_summary()

        self.assertIsNone(result["max_c"])
        self.assertEqual(result["readings"], [])


if __name__ == "__main__":
    unittest.main()
