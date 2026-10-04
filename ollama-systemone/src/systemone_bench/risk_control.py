from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from systemone_bench.cascade import parse_threshold_grid
from systemone_bench.selective import load_labeled_details


def binomial_cdf(k: int, n: int, p: float) -> float:
    if n < 0:
        raise ValueError("n must be >= 0")
    if not 0 <= k <= n:
        raise ValueError("k must be between 0 and n")
    if not 0.0 <= p <= 1.0:
        raise ValueError("p must be between 0 and 1")
    if k == n:
        return 1.0
    if p == 0.0:
        return 1.0
    if p == 1.0:
        return 0.0

    q = 1.0 - p
    term = q**n
    total = term
    for i in range(k):
        term *= ((n - i) / (i + 1)) * (p / q)
        total += term
    return min(1.0, max(0.0, total))


def clopper_pearson_upper(
    errors: int,
    accepted: int,
    alpha: float,
) -> float:
    if accepted < 1:
        raise ValueError("accepted must be >= 1")
    if not 0 <= errors <= accepted:
        raise ValueError("errors must be between 0 and accepted")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be between 0 and 1")
    if errors == accepted:
        return 1.0
    if errors == 0:
        return 1.0 - alpha ** (1.0 / accepted)

    low = errors / accepted
    high = 1.0
    for _ in range(100):
        mid = (low + high) / 2.0
        cdf = binomial_cdf(errors, accepted, mid)
        if cdf > alpha:
            low = mid
        else:
            high = mid
    return high


def load_development_rows(
    paths: list[Path],
    model: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        for row in load_labeled_details(path, model):
            item = dict(row)
            item["_detail_file"] = str(path)
            rows.append(item)
    if not rows:
        raise ValueError("no development rows found")
    return rows


def evaluate_threshold(
    rows: list[dict[str, Any]],
    threshold: float,
    alpha_pointwise: float,
) -> dict[str, Any]:
    accepted_rows = [
        row for row in rows
        if float(row["confidence"]) >= threshold
    ]
    accepted = len(accepted_rows)
    total = len(rows)
    if accepted == 0:
        return {
            "threshold": threshold,
            "accepted": 0,
            "coverage": 0.0,
            "errors": 0,
            "empirical_risk": None,
            "accepted_accuracy": None,
            "upper_risk_bound": None,
        }

    errors = sum(1 for row in accepted_rows if not row["correct"])
    empirical_risk = errors / accepted
    return {
        "threshold": threshold,
        "accepted": accepted,
        "coverage": accepted / total,
        "errors": errors,
        "empirical_risk": empirical_risk,
        "accepted_accuracy": 1.0 - empirical_risk,
        "upper_risk_bound": clopper_pearson_upper(
            errors,
            accepted,
            alpha_pointwise,
        ),
    }


def per_file_at_threshold(
    rows: list[dict[str, Any]],
    threshold: float,
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row["_detail_file"]), []).append(row)

    result: dict[str, dict[str, Any]] = {}
    for path, file_rows in sorted(grouped.items()):
        accepted_rows = [
            row for row in file_rows
            if float(row["confidence"]) >= threshold
        ]
        errors = sum(1 for row in accepted_rows if not row["correct"])
        accepted = len(accepted_rows)
        result[path] = {
            "decisions": len(file_rows),
            "accepted": accepted,
            "coverage": accepted / len(file_rows),
            "errors": errors,
            "empirical_risk": errors / accepted if accepted else None,
            "accepted_accuracy": (
                1.0 - errors / accepted if accepted else None
            ),
        }
    return result


def select_risk_controlled_threshold(
    rows: list[dict[str, Any]],
    thresholds: list[float],
    max_risk: float,
    confidence_level: float,
    min_coverage: float,
) -> dict[str, Any]:
    if not thresholds:
        raise ValueError("threshold grid is empty")
    if not 0.0 <= max_risk <= 1.0:
        raise ValueError("max_risk must be between 0 and 1")
    if not 0.0 < confidence_level < 1.0:
        raise ValueError("confidence_level must be between 0 and 1")
    if not 0.0 <= min_coverage <= 1.0:
        raise ValueError("min_coverage must be between 0 and 1")

    family_alpha = 1.0 - confidence_level
    alpha_pointwise = family_alpha / len(thresholds)

    candidates = [
        evaluate_threshold(rows, threshold, alpha_pointwise)
        for threshold in thresholds
    ]
    feasible = [
        row for row in candidates
        if row["accepted"] > 0
        and row["coverage"] >= min_coverage
        and row["upper_risk_bound"] is not None
        and row["upper_risk_bound"] <= max_risk
    ]
    feasible.sort(
        key=lambda row: (
            -row["coverage"],
            row["threshold"],
        )
    )
    selected = feasible[0] if feasible else None

    result: dict[str, Any] = {
        "decisions": len(rows),
        "max_risk": max_risk,
        "confidence_level": confidence_level,
        "family_alpha": family_alpha,
        "candidate_count": len(thresholds),
        "pointwise_alpha": alpha_pointwise,
        "correction": "bonferroni",
        "min_coverage": min_coverage,
        "candidates": candidates,
        "selected": selected,
    }
    if selected is not None:
        result["per_file_at_selected"] = per_file_at_threshold(
            rows,
            float(selected["threshold"]),
        )
    else:
        result["per_file_at_selected"] = None
    return result


def format_optional(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}"


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Select a confidence threshold whose accepted error risk has a "
            "Bonferroni-corrected one-sided exact binomial upper bound below "
            "a requested target on development evidence"
        )
    )
    ap.add_argument(
        "--details",
        type=Path,
        nargs="+",
        required=True,
        help="development *-details.jsonl files; rows are pooled for policy development",
    )
    ap.add_argument("--model", required=True, help="model to analyze")
    ap.add_argument(
        "--thresholds",
        default="0.50:0.99:0.01",
        help="fixed candidate threshold grid; supports start:stop:step",
    )
    ap.add_argument(
        "--max-risk",
        type=float,
        required=True,
        help="maximum accepted error rate allowed by the simultaneous upper bound",
    )
    ap.add_argument(
        "--confidence-level",
        type=float,
        default=0.95,
        help="family-wise confidence level across the threshold grid",
    )
    ap.add_argument(
        "--min-coverage",
        type=float,
        default=0.0,
        help="optional minimum development coverage for a feasible policy",
    )
    ap.add_argument(
        "--output",
        type=Path,
        default=None,
        help="optional JSON output path",
    )
    args = ap.parse_args()

    try:
        thresholds = parse_threshold_grid(args.thresholds)
        rows = load_development_rows(args.details, args.model)
        result = select_risk_controlled_threshold(
            rows,
            thresholds,
            args.max_risk,
            args.confidence_level,
            args.min_coverage,
        )
    except ValueError as exc:
        ap.error(str(exc))

    print(
        f"Risk control: model={args.model} decisions={result['decisions']} "
        f"candidates={result['candidate_count']} "
        f"max_risk={args.max_risk:.4f} "
        f"confidence={args.confidence_level:.4f} "
        f"correction={result['correction']}"
    )
    print(
        f"Family alpha={result['family_alpha']:.6g} "
        f"pointwise alpha={result['pointwise_alpha']:.6g}"
    )

    selected = result["selected"]
    if selected is None:
        print(
            "\nNo threshold satisfies the requested simultaneous risk bound "
            "and minimum coverage."
        )
    else:
        print("\nSelected maximum-coverage policy:")
        print(
            f"threshold={selected['threshold']:.2f} "
            f"coverage={selected['coverage']:.4f} "
            f"accepted={selected['accepted']} "
            f"errors={selected['errors']} "
            f"empirical_risk={selected['empirical_risk']:.4f} "
            f"upper_risk_bound={selected['upper_risk_bound']:.4f}"
        )
        print("\nPer-file diagnostics at selected threshold:")
        for path, metrics in result["per_file_at_selected"].items():
            print(
                f"  {Path(path).name}: "
                f"coverage={metrics['coverage']:.4f} "
                f"accepted={metrics['accepted']} "
                f"errors={metrics['errors']} "
                f"risk={format_optional(metrics['empirical_risk'])}"
            )

    print("\nCandidate grid:")
    print(
        "threshold  coverage  accepted  errors  empirical_risk  upper_risk_bound"
    )
    for candidate in result["candidates"]:
        print(
            f"{candidate['threshold']:>9.2f}  "
            f"{candidate['coverage']:>8.4f}  "
            f"{candidate['accepted']:>8}  "
            f"{candidate['errors']:>6}  "
            f"{format_optional(candidate['empirical_risk']):>14}  "
            f"{format_optional(candidate['upper_risk_bound']):>16}"
        )

    output = {
        "model": args.model,
        "detail_files": [str(path) for path in args.details],
        "threshold_grid": thresholds,
        **result,
        "methodology": {
            "bound": "one-sided exact Clopper-Pearson binomial upper bound",
            "multiple_testing": (
                "Bonferroni correction across the fixed threshold grid"
            ),
            "scope": (
                "Development-sample bound under i.i.d./exchangeability assumptions. "
                "It does not guarantee robustness to dataset or production shift."
            ),
            "validation_requirement": (
                "Freeze any selected threshold before evaluating a new untouched "
                "fresh holdout."
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
