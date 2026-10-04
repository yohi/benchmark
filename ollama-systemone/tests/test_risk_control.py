from __future__ import annotations

import math
import unittest

from systemone_bench.risk_control import (
    binomial_cdf,
    clopper_pearson_upper,
    evaluate_threshold,
    select_risk_controlled_threshold,
)


class SelectiveRiskControlTests(unittest.TestCase):
    def test_binomial_cdf_matches_simple_cases(self) -> None:
        self.assertAlmostEqual(binomial_cdf(0, 2, 0.5), 0.25)
        self.assertAlmostEqual(binomial_cdf(1, 2, 0.5), 0.75)
        self.assertEqual(binomial_cdf(2, 2, 0.5), 1.0)

    def test_zero_error_upper_bound_matches_closed_form(self) -> None:
        bound = clopper_pearson_upper(0, 100, 0.05)
        expected = 1.0 - 0.05 ** (1.0 / 100)
        self.assertAlmostEqual(bound, expected)

    def test_upper_bound_increases_with_more_errors(self) -> None:
        zero = clopper_pearson_upper(0, 100, 0.05)
        one = clopper_pearson_upper(1, 100, 0.05)
        two = clopper_pearson_upper(2, 100, 0.05)

        self.assertLess(zero, one)
        self.assertLess(one, two)

    def test_bonferroni_is_more_conservative_than_single_test(self) -> None:
        single = clopper_pearson_upper(0, 100, 0.05)
        corrected = clopper_pearson_upper(0, 100, 0.05 / 10)

        self.assertGreater(corrected, single)

    def test_evaluate_threshold_reports_selective_risk(self) -> None:
        rows = [
            {"confidence": 0.95, "correct": True},
            {"confidence": 0.90, "correct": True},
            {"confidence": 0.80, "correct": False},
            {"confidence": 0.40, "correct": False},
        ]

        result = evaluate_threshold(rows, 0.80, alpha_pointwise=0.05)

        self.assertEqual(result["accepted"], 3)
        self.assertEqual(result["errors"], 1)
        self.assertAlmostEqual(result["coverage"], 0.75)
        self.assertAlmostEqual(result["empirical_risk"], 1 / 3)

    def test_selects_maximum_coverage_feasible_threshold(self) -> None:
        rows = [
            *[
                {
                    "confidence": 0.95 - index * 0.001,
                    "correct": True,
                    "_detail_file": "a.jsonl",
                }
                for index in range(100)
            ],
            {
                "confidence": 0.70,
                "correct": False,
                "_detail_file": "a.jsonl",
            },
        ]

        result = select_risk_controlled_threshold(
            rows,
            thresholds=[0.70, 0.80, 0.90],
            max_risk=0.10,
            confidence_level=0.95,
            min_coverage=0.5,
        )

        self.assertIsNotNone(result["selected"])
        assert result["selected"] is not None
        self.assertEqual(result["selected"]["threshold"], 0.80)
        self.assertEqual(result["selected"]["errors"], 0)

    def test_returns_no_policy_when_bound_is_too_strict(self) -> None:
        rows = [
            {
                "confidence": 0.95,
                "correct": True,
                "_detail_file": "a.jsonl",
            }
            for _ in range(20)
        ]

        result = select_risk_controlled_threshold(
            rows,
            thresholds=[0.90],
            max_risk=0.01,
            confidence_level=0.95,
            min_coverage=0.0,
        )

        self.assertIsNone(result["selected"])

    def test_selected_result_includes_per_file_diagnostics(self) -> None:
        rows = [
            *[
                {
                    "confidence": 0.95,
                    "correct": True,
                    "_detail_file": "a.jsonl",
                }
                for _ in range(50)
            ],
            *[
                {
                    "confidence": 0.94,
                    "correct": True,
                    "_detail_file": "b.jsonl",
                }
                for _ in range(50)
            ],
        ]

        result = select_risk_controlled_threshold(
            rows,
            thresholds=[0.90],
            max_risk=0.10,
            confidence_level=0.95,
            min_coverage=0.5,
        )

        self.assertIsNotNone(result["selected"])
        self.assertEqual(
            set(result["per_file_at_selected"]),
            {"a.jsonl", "b.jsonl"},
        )
        self.assertEqual(
            result["per_file_at_selected"]["a.jsonl"]["errors"],
            0,
        )


if __name__ == "__main__":
    unittest.main()
