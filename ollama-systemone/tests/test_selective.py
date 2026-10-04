from __future__ import annotations

import unittest

from systemone_bench.selective import (
    area_under_risk_coverage,
    brier_score,
    calibration_bins,
    error_detection_auroc,
    expected_calibration_error,
    oracle_aurc,
    risk_at_coverages,
    risk_coverage_curve,
    summarize_subset,
)


class SelectiveConfidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rows = [
            {"confidence": 0.95, "correct": True, "prediction": "a"},
            {"confidence": 0.80, "correct": True, "prediction": "a"},
            {"confidence": 0.70, "correct": False, "prediction": "b"},
            {"confidence": 0.40, "correct": False, "prediction": "b"},
        ]

    def test_brier_score_uses_confidence_as_correctness_probability(self) -> None:
        expected = (
            (0.95 - 1.0) ** 2
            + (0.80 - 1.0) ** 2
            + (0.70 - 0.0) ** 2
            + (0.40 - 0.0) ** 2
        ) / 4
        self.assertAlmostEqual(brier_score(self.rows), expected)

    def test_ece_uses_weighted_bin_calibration_gap(self) -> None:
        bins = calibration_bins(self.rows, 2)
        self.assertEqual(bins[0]["n"], 1)
        self.assertEqual(bins[1]["n"], 3)

        expected = (1 / 4) * 0.40 + (3 / 4) * abs(
            ((0.95 + 0.80 + 0.70) / 3) - (2 / 3)
        )
        self.assertAlmostEqual(
            expected_calibration_error(bins, len(self.rows)),
            expected,
        )

    def test_risk_coverage_curve_accepts_high_confidence_first(self) -> None:
        curve = risk_coverage_curve(self.rows)

        self.assertEqual(curve[0]["accepted"], 1)
        self.assertEqual(curve[0]["risk"], 0.0)
        self.assertEqual(curve[1]["risk"], 0.0)
        self.assertAlmostEqual(curve[2]["risk"], 1 / 3)
        self.assertAlmostEqual(curve[3]["risk"], 1 / 2)

    def test_aurc_is_better_than_or_equal_to_oracle(self) -> None:
        curve = risk_coverage_curve(self.rows)
        aurc = area_under_risk_coverage(curve)
        oracle = oracle_aurc(self.rows)

        self.assertGreaterEqual(aurc, oracle)
        self.assertAlmostEqual(aurc, oracle)

    def test_excess_aurc_detects_bad_confidence_ordering(self) -> None:
        inverted = [
            {"confidence": 0.95, "correct": False, "prediction": "b"},
            {"confidence": 0.80, "correct": True, "prediction": "a"},
            {"confidence": 0.70, "correct": True, "prediction": "a"},
            {"confidence": 0.40, "correct": False, "prediction": "b"},
        ]

        aurc = area_under_risk_coverage(risk_coverage_curve(inverted))
        oracle = oracle_aurc(inverted)

        self.assertGreater(aurc, oracle)

    def test_error_detection_auroc_measures_confidence_ranking(self) -> None:
        self.assertEqual(error_detection_auroc(self.rows), 1.0)

        inverted = [
            {"confidence": 0.40, "correct": True, "prediction": "a"},
            {"confidence": 0.30, "correct": True, "prediction": "a"},
            {"confidence": 0.95, "correct": False, "prediction": "b"},
        ]
        self.assertEqual(error_detection_auroc(inverted), 0.0)

    def test_risk_at_coverages_reports_top_confidence_subset(self) -> None:
        result = risk_at_coverages(self.rows, [0.5, 1.0])

        self.assertEqual(result["0.50"]["accepted"], 2)
        self.assertEqual(result["0.50"]["accepted_accuracy"], 1.0)
        self.assertEqual(result["0.50"]["threshold_floor"], 0.80)
        self.assertEqual(result["1.00"]["errors"], 2)

    def test_summary_exposes_selective_and_calibration_metrics(self) -> None:
        summary = summarize_subset(self.rows, bins=4)

        self.assertEqual(summary["decisions"], 4)
        self.assertEqual(summary["accuracy"], 0.5)
        self.assertEqual(summary["error_count"], 2)
        self.assertEqual(summary["max_error_confidence"], 0.70)
        self.assertEqual(summary["min_correct_confidence"], 0.80)
        self.assertEqual(summary["error_detection_auroc"], 1.0)
        self.assertAlmostEqual(summary["excess_aurc"], 0.0)


if __name__ == "__main__":
    unittest.main()
