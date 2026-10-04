from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Any


def load_labeled_details(path: Path, model: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if str(row.get("model")) != model:
                continue
            if row.get("correct") is None:
                raise ValueError(
                    f"{path}:{line_no}: selective analysis requires labeled decisions"
                )
            confidence = row.get("confidence")
            if not isinstance(confidence, (int, float)):
                raise ValueError(
                    f"{path}:{line_no}: selective analysis requires numeric confidence"
                )
            confidence = float(confidence)
            if not 0.0 <= confidence <= 1.0:
                raise ValueError(
                    f"{path}:{line_no}: confidence must be between 0 and 1"
                )
            if row.get("prediction") is None:
                raise ValueError(
                    f"{path}:{line_no}: selective analysis requires a prediction"
                )
            normalized = dict(row)
            normalized["confidence"] = confidence
            normalized["correct"] = bool(row["correct"])
            rows.append(normalized)

    if not rows:
        raise ValueError(f"{path}: no labeled rows found for model {model!r}")
    return rows


def brier_score(rows: list[dict[str, Any]]) -> float:
    return statistics.mean(
        (float(row["confidence"]) - (1.0 if row["correct"] else 0.0)) ** 2
        for row in rows
    )


def calibration_bins(
    rows: list[dict[str, Any]],
    bins: int,
) -> list[dict[str, Any]]:
    if bins < 1:
        raise ValueError("bins must be >= 1")

    grouped: list[list[dict[str, Any]]] = [[] for _ in range(bins)]
    for row in rows:
        confidence = float(row["confidence"])
        index = min(int(confidence * bins), bins - 1)
        grouped[index].append(row)

    result: list[dict[str, Any]] = []
    for index, bucket in enumerate(grouped):
        lower = index / bins
        upper = (index + 1) / bins
        if bucket:
            mean_confidence = statistics.mean(
                float(row["confidence"]) for row in bucket
            )
            accuracy = statistics.mean(
                1.0 if row["correct"] else 0.0 for row in bucket
            )
            gap = abs(mean_confidence - accuracy)
        else:
            mean_confidence = None
            accuracy = None
            gap = None
        result.append(
            {
                "bin": index,
                "lower": lower,
                "upper": upper,
                "n": len(bucket),
                "mean_confidence": mean_confidence,
                "accuracy": accuracy,
                "absolute_gap": gap,
            }
        )
    return result


def expected_calibration_error(
    bins_result: list[dict[str, Any]],
    total: int,
) -> float:
    if total == 0:
        return math.nan
    return sum(
        (bucket["n"] / total) * float(bucket["absolute_gap"])
        for bucket in bins_result
        if bucket["n"] and bucket["absolute_gap"] is not None
    )


def maximum_calibration_error(
    bins_result: list[dict[str, Any]],
) -> float:
    gaps = [
        float(bucket["absolute_gap"])
        for bucket in bins_result
        if bucket["absolute_gap"] is not None
    ]
    return max(gaps) if gaps else math.nan


def risk_coverage_curve(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(
        rows,
        key=lambda row: float(row["confidence"]),
        reverse=True,
    )
    errors = 0
    total = len(ranked)
    curve: list[dict[str, Any]] = []
    for index, row in enumerate(ranked, 1):
        if not row["correct"]:
            errors += 1
        curve.append(
            {
                "accepted": index,
                "coverage": index / total,
                "risk": errors / index,
                "accepted_accuracy": 1.0 - (errors / index),
                "threshold_floor": float(row["confidence"]),
            }
        )
    return curve


def area_under_risk_coverage(curve: list[dict[str, Any]]) -> float:
    if not curve:
        return math.nan
    return statistics.mean(float(point["risk"]) for point in curve)


def oracle_aurc(rows: list[dict[str, Any]]) -> float:
    oracle = sorted(
        rows,
        key=lambda row: 1 if row["correct"] else 0,
        reverse=True,
    )
    return area_under_risk_coverage(risk_coverage_curve(oracle))


def risk_at_coverages(
    rows: list[dict[str, Any]],
    coverages: list[float],
) -> dict[str, dict[str, Any]]:
    ranked = sorted(
        rows,
        key=lambda row: float(row["confidence"]),
        reverse=True,
    )
    total = len(ranked)
    result: dict[str, dict[str, Any]] = {}
    for coverage in coverages:
        if not 0.0 < coverage <= 1.0:
            raise ValueError("coverage targets must be in (0, 1]")
        accepted = max(1, math.ceil(total * coverage))
        selected = ranked[:accepted]
        errors = sum(1 for row in selected if not row["correct"])
        result[f"{coverage:.2f}"] = {
            "target_coverage": coverage,
            "accepted": accepted,
            "actual_coverage": accepted / total,
            "risk": errors / accepted,
            "accepted_accuracy": 1.0 - (errors / accepted),
            "errors": errors,
            "threshold_floor": float(selected[-1]["confidence"]),
        }
    return result


def error_detection_auroc(rows: list[dict[str, Any]]) -> float | None:
    positives = [row for row in rows if not row["correct"]]
    negatives = [row for row in rows if row["correct"]]
    if not positives or not negatives:
        return None

    wins = 0.0
    comparisons = 0
    for error in positives:
        error_score = 1.0 - float(error["confidence"])
        for correct in negatives:
            correct_score = 1.0 - float(correct["confidence"])
            comparisons += 1
            if error_score > correct_score:
                wins += 1.0
            elif error_score == correct_score:
                wins += 0.5
    return wins / comparisons


def summarize_subset(
    rows: list[dict[str, Any]],
    bins: int,
) -> dict[str, Any]:
    if not rows:
        raise ValueError("cannot summarize empty row set")

    accuracy = statistics.mean(
        1.0 if row["correct"] else 0.0 for row in rows
    )
    mean_confidence = statistics.mean(
        float(row["confidence"]) for row in rows
    )
    errors = [row for row in rows if not row["correct"]]
    bins_result = calibration_bins(rows, bins)
    curve = risk_coverage_curve(rows)
    aurc = area_under_risk_coverage(curve)
    oracle = oracle_aurc(rows)

    return {
        "decisions": len(rows),
        "accuracy": accuracy,
        "mean_confidence": mean_confidence,
        "signed_calibration_gap": mean_confidence - accuracy,
        "absolute_calibration_gap": abs(mean_confidence - accuracy),
        "brier_score": brier_score(rows),
        "ece": expected_calibration_error(bins_result, len(rows)),
        "mce": maximum_calibration_error(bins_result),
        "aurc": aurc,
        "oracle_aurc": oracle,
        "excess_aurc": aurc - oracle,
        "error_detection_auroc": error_detection_auroc(rows),
        "error_count": len(errors),
        "max_error_confidence": (
            max(float(row["confidence"]) for row in errors)
            if errors else None
        ),
        "min_correct_confidence": min(
            float(row["confidence"])
            for row in rows
            if row["correct"]
        ) if any(row["correct"] for row in rows) else None,
        "error_confidences": sorted(
            (float(row["confidence"]) for row in errors),
            reverse=True,
        ),
        "calibration_bins": bins_result,
        "risk_at_coverage": risk_at_coverages(
            rows,
            [0.50, 0.80, 0.90, 0.95, 1.0],
        ),
    }


def analyze_file(
    path: Path,
    model: str,
    bins: int,
) -> dict[str, Any]:
    rows = load_labeled_details(path, model)
    overall = summarize_subset(rows, bins)

    by_predicted: dict[str, Any] = {}
    labels = sorted({str(row["prediction"]) for row in rows})
    for label in labels:
        subset = [
            row for row in rows if str(row["prediction"]) == label
        ]
        by_predicted[label] = summarize_subset(subset, bins)

    errors = [
        {
            "case_id": row.get("case_id"),
            "pass": row.get("pass"),
            "question": row.get("question"),
            "expected": row.get("expected"),
            "prediction": row.get("prediction"),
            "confidence": float(row["confidence"]),
        }
        for row in rows
        if not row["correct"]
    ]
    errors.sort(key=lambda row: row["confidence"], reverse=True)

    return {
        "detail_file": str(path),
        "model": model,
        "overall": overall,
        "by_predicted": by_predicted,
        "errors": errors,
    }


def format_optional(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}"


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Analyze System One confidence calibration and selective "
            "classification behavior from existing detail JSONL files"
        )
    )
    ap.add_argument(
        "--details",
        type=Path,
        nargs="+",
        required=True,
        help="one or more *-details.jsonl files, analyzed independently",
    )
    ap.add_argument("--model", required=True, help="model to analyze")
    ap.add_argument(
        "--bins",
        type=int,
        default=10,
        help="equal-width confidence bins for ECE/MCE",
    )
    ap.add_argument(
        "--output",
        type=Path,
        default=None,
        help="optional JSON output path",
    )
    args = ap.parse_args()

    if args.bins < 1:
        ap.error("--bins must be >= 1")

    try:
        analyses = [
            analyze_file(path, args.model, args.bins)
            for path in args.details
        ]
    except ValueError as exc:
        ap.error(str(exc))

    print(
        f"Selective confidence analysis: model={args.model} "
        f"files={len(analyses)} bins={args.bins}"
    )
    print(
        "\nfile  n  accuracy  mean_conf  gap  ece  brier  "
        "aurc  excess_aurc  err_auroc  errors  max_err_conf"
    )
    for analysis in analyses:
        overall = analysis["overall"]
        print(
            f"{Path(analysis['detail_file']).name} "
            f"{overall['decisions']:>4} "
            f"{overall['accuracy']:.4f} "
            f"{overall['mean_confidence']:.4f} "
            f"{overall['signed_calibration_gap']:+.4f} "
            f"{overall['ece']:.4f} "
            f"{overall['brier_score']:.4f} "
            f"{overall['aurc']:.4f} "
            f"{overall['excess_aurc']:.4f} "
            f"{format_optional(overall['error_detection_auroc'])} "
            f"{overall['error_count']:>3} "
            f"{format_optional(overall['max_error_confidence'])}"
        )

        if analysis["errors"]:
            print("  errors:")
            for error in analysis["errors"]:
                print(
                    f"    {error['case_id']}: "
                    f"{error['expected']} -> {error['prediction']} "
                    f"confidence={error['confidence']:.6f}"
                )

        print("  risk@coverage:")
        for target, point in overall["risk_at_coverage"].items():
            print(
                f"    {target}: accepted={point['accepted']} "
                f"accuracy={point['accepted_accuracy']:.4f} "
                f"risk={point['risk']:.4f} "
                f"floor={point['threshold_floor']:.4f}"
            )

    output = {
        "model": args.model,
        "bins": args.bins,
        "analyses": analyses,
        "metric_notes": {
            "ece": (
                "Equal-width expected calibration error. Lower is better. "
                "Interprets confidence as an estimated probability of correctness."
            ),
            "brier_score": (
                "Mean squared error between confidence and correctness. "
                "Lower is better."
            ),
            "aurc": (
                "Mean selective risk while accepting examples from highest to "
                "lowest confidence. Lower is better."
            ),
            "excess_aurc": (
                "AURC minus the oracle ordering for the same error count. "
                "Lower is better; zero is ideal ranking."
            ),
            "error_detection_auroc": (
                "AUROC using 1-confidence to rank errors above correct decisions. "
                "Higher is better; 1.0 is perfect separation."
            ),
        },
    }

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(output, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"\nWrote {args.output}")


if __name__ == "__main__":
    main()
