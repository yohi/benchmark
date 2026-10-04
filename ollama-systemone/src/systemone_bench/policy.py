from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
from typing import Any

from systemone_bench.cascade import DecisionKey, parse_threshold_grid


def load_policy_details(
    paths: list[Path],
) -> dict[str, dict[DecisionKey, dict[str, Any]]]:
    by_model: dict[str, dict[DecisionKey, dict[str, Any]]] = {}

    for path in paths:
        with path.open(encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                try:
                    model = str(row["model"])
                    case_id = str(row["case_id"])
                    pass_no = int(row["pass"])
                    question = str(row["question"])
                except KeyError as exc:
                    raise ValueError(
                        f"{path}:{line_no}: missing required field "
                        f"{exc.args[0]!r}"
                    ) from exc

                if row.get("correct") is None:
                    raise ValueError(
                        f"{path}:{line_no}: policy analysis requires "
                        "labeled decisions (correct must not be null)"
                    )
                if not isinstance(row.get("confidence"), (int, float)):
                    raise ValueError(
                        f"{path}:{line_no}: policy analysis requires "
                        "numeric confidence"
                    )
                if row.get("prediction") is None:
                    raise ValueError(
                        f"{path}:{line_no}: policy analysis requires "
                        "a non-null prediction"
                    )

                key = (case_id, pass_no, question)
                model_rows = by_model.setdefault(model, {})
                if key in model_rows:
                    raise ValueError(
                        f"duplicate decision for model={model!r}, "
                        f"case={case_id!r}, pass={pass_no}, "
                        f"question={question!r}; do not mix duplicate runs"
                    )
                model_rows[key] = row

    if not by_model:
        raise ValueError("no detail rows found")
    return by_model


def parse_label_grid(spec: str) -> tuple[str, list[float]]:
    if "=" not in spec:
        raise ValueError(
            f"invalid label grid {spec!r}; expected LABEL=THRESHOLDS"
        )
    label, raw_grid = spec.split("=", 1)
    label = label.strip()
    raw_grid = raw_grid.strip()
    if not label:
        raise ValueError(f"invalid label grid {spec!r}; label is empty")
    if not raw_grid:
        raise ValueError(
            f"invalid label grid {spec!r}; threshold grid is empty"
        )
    return label, parse_threshold_grid(raw_grid)


def validate_model(
    by_model: dict[str, dict[DecisionKey, dict[str, Any]]],
    model: str,
) -> tuple[list[DecisionKey], set[str]]:
    if model not in by_model:
        raise ValueError(
            f"missing model {model!r} in supplied detail files; "
            f"available: {', '.join(sorted(by_model))}"
        )

    rows = by_model[model]
    labels: set[str] = set()
    for key, row in rows.items():
        prediction = row.get("prediction")
        if prediction is None:
            raise ValueError(
                f"decision {key!r} has null prediction; "
                "predicted-label thresholding requires categorical predictions"
            )
        labels.add(str(prediction))

    return sorted(rows), labels


def simulate_policy(
    rows: dict[DecisionKey, dict[str, Any]],
    keys: list[DecisionKey],
    default_threshold: float,
    label_thresholds: dict[str, float],
) -> dict[str, Any]:
    accepted = 0
    accepted_correct = 0
    route_signature: list[str] = []
    accepted_errors: list[dict[str, Any]] = []
    by_predicted: dict[str, dict[str, Any]] = {}

    for key in keys:
        row = rows[key]
        prediction = str(row["prediction"])
        threshold = label_thresholds.get(prediction, default_threshold)
        confidence = float(row["confidence"])
        is_accepted = confidence >= threshold

        label_stats = by_predicted.setdefault(
            prediction,
            {
                "decisions": 0,
                "threshold": threshold,
                "accepted": 0,
                "accepted_correct": 0,
            },
        )
        label_stats["decisions"] += 1

        if is_accepted:
            accepted += 1
            label_stats["accepted"] += 1
            if bool(row["correct"]):
                accepted_correct += 1
                label_stats["accepted_correct"] += 1
            else:
                accepted_errors.append(
                    {
                        "case_id": key[0],
                        "pass": key[1],
                        "question": key[2],
                        "expected": row.get("expected"),
                        "prediction": row.get("prediction"),
                        "confidence": confidence,
                        "threshold": threshold,
                    }
                )
            route_signature.append("accept")
        else:
            route_signature.append("fallback")

    total = len(keys)
    summary_by_predicted: dict[str, dict[str, Any]] = {}
    for label, stats in sorted(by_predicted.items()):
        decisions = int(stats["decisions"])
        label_accepted = int(stats["accepted"])
        label_correct = int(stats["accepted_correct"])
        summary_by_predicted[label] = {
            "decisions": decisions,
            "threshold": float(stats["threshold"]),
            "accepted": label_accepted,
            "acceptance_rate": label_accepted / decisions if decisions else 0.0,
            "accepted_accuracy": (
                label_correct / label_accepted if label_accepted else None
            ),
        }

    return {
        "thresholds": {
            "default": default_threshold,
            "by_predicted": dict(sorted(label_thresholds.items())),
        },
        "decisions": total,
        "local_accepted": accepted,
        "local_coverage": accepted / total if total else 0.0,
        "accepted_accuracy": (
            accepted_correct / accepted if accepted else None
        ),
        "fallback_count": total - accepted,
        "fallback_rate": (total - accepted) / total if total else 0.0,
        "accepted_errors": accepted_errors,
        "by_predicted": summary_by_predicted,
        "_route_signature": route_signature,
    }


def collapse_equivalent_policies(
    rows: list[dict[str, Any]],
    labels: list[str],
) -> list[dict[str, Any]]:
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(tuple(row["_route_signature"]), []).append(row)

    collapsed: list[dict[str, Any]] = []
    for group in groups.values():
        representative = max(
            group,
            key=lambda row: tuple(
                row["thresholds"]["by_predicted"].get(label, row["thresholds"]["default"])
                for label in labels
            ),
        )
        item = {
            key: value
            for key, value in representative.items()
            if key != "_route_signature"
        }
        item["threshold_ranges"] = {
            label: {
                "min": min(
                    row["thresholds"]["by_predicted"].get(
                        label, row["thresholds"]["default"]
                    )
                    for row in group
                ),
                "max": max(
                    row["thresholds"]["by_predicted"].get(
                        label, row["thresholds"]["default"]
                    )
                    for row in group
                ),
            }
            for label in labels
        }
        item["equivalent_configurations"] = len(group)
        collapsed.append(item)
    return collapsed


def explore_policies(
    rows: dict[DecisionKey, dict[str, Any]],
    keys: list[DecisionKey],
    default_threshold: float,
    label_grids: dict[str, list[float]],
    min_accepted_accuracy: float,
) -> tuple[list[dict[str, Any]], int]:
    labels = sorted(label_grids)
    combinations = (
        list(itertools.product(*(label_grids[label] for label in labels)))
        if labels
        else [()]
    )

    evaluated = []
    for values in combinations:
        overrides = dict(zip(labels, values, strict=True))
        evaluated.append(
            simulate_policy(
                rows,
                keys,
                default_threshold,
                overrides,
            )
        )

    feasible = [
        row
        for row in evaluated
        if row["accepted_accuracy"] is not None
        and row["accepted_accuracy"] >= min_accepted_accuracy
    ]
    collapsed = collapse_equivalent_policies(feasible, labels)
    ranked = sorted(
        collapsed,
        key=lambda row: (
            -row["local_coverage"],
            -row["accepted_accuracy"],
            row["fallback_rate"],
        ),
    )
    return ranked, len(evaluated)


def format_thresholds(row: dict[str, Any], labels: list[str]) -> str:
    parts = [f"default={row['thresholds']['default']:.2f}"]
    ranges = row.get("threshold_ranges", {})
    for label in labels:
        threshold_range = ranges.get(label)
        if threshold_range and threshold_range["min"] != threshold_range["max"]:
            parts.append(
                f"{label}={threshold_range['min']:.2f}.."
                f"{threshold_range['max']:.2f}"
            )
        else:
            value = row["thresholds"]["by_predicted"].get(
                label,
                row["thresholds"]["default"],
            )
            parts.append(f"{label}={value:.2f}")
    return ",".join(parts)


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Explore predicted-label-specific confidence thresholds from "
            "System One benchmark detail JSONL without rerunning Ollama"
        )
    )
    ap.add_argument(
        "--details",
        type=Path,
        nargs="+",
        required=True,
        help="one or more *-details.jsonl files",
    )
    ap.add_argument("--model", required=True, help="model to analyze")
    ap.add_argument(
        "--default-threshold",
        type=float,
        required=True,
        help="threshold used for predicted labels without an override",
    )
    ap.add_argument(
        "--label-grid",
        action="append",
        default=[],
        metavar="LABEL=GRID",
        help=(
            "predicted-label threshold grid; repeatable, e.g. "
            "--label-grid planning=0.60:0.90:0.01"
        ),
    )
    ap.add_argument(
        "--min-accepted-accuracy",
        type=float,
        default=1.0,
        help="minimum accepted accuracy for feasible policies",
    )
    ap.add_argument(
        "--max-combinations",
        type=int,
        default=100000,
        help="guard against accidental combinatorial explosions",
    )
    ap.add_argument(
        "--top",
        type=int,
        default=20,
        help="number of coverage-ranked feasible policies to print/store",
    )
    ap.add_argument(
        "--output",
        type=Path,
        default=None,
        help="optional JSON output path",
    )
    args = ap.parse_args()

    if not 0.0 <= args.default_threshold <= 1.0:
        ap.error("--default-threshold must be between 0 and 1")
    if not 0.0 <= args.min_accepted_accuracy <= 1.0:
        ap.error("--min-accepted-accuracy must be between 0 and 1")
    if args.max_combinations < 1:
        ap.error("--max-combinations must be >= 1")
    if args.top < 1:
        ap.error("--top must be >= 1")

    try:
        label_grids: dict[str, list[float]] = {}
        for raw_spec in args.label_grid:
            label, grid = parse_label_grid(raw_spec)
            if label in label_grids:
                raise ValueError(f"duplicate --label-grid for {label!r}")
            label_grids[label] = grid

        combinations = 1
        for grid in label_grids.values():
            combinations *= len(grid)
        if combinations > args.max_combinations:
            raise ValueError(
                f"label grids would evaluate {combinations} combinations; "
                "increase --max-combinations or reduce the grids"
            )

        by_model = load_policy_details(args.details)
        keys, observed_labels = validate_model(by_model, args.model)
        unknown_labels = sorted(set(label_grids) - observed_labels)
        if unknown_labels:
            raise ValueError(
                "label grid references prediction label(s) not present in details: "
                + ", ".join(unknown_labels)
            )
    except ValueError as exc:
        ap.error(str(exc))

    model_rows = by_model[args.model]
    baseline = simulate_policy(
        model_rows,
        keys,
        args.default_threshold,
        {},
    )
    ranked, evaluated_count = explore_policies(
        model_rows,
        keys,
        args.default_threshold,
        label_grids,
        args.min_accepted_accuracy,
    )

    print(
        f"Policy analysis: model={args.model} decisions={len(keys)} "
        f"default={args.default_threshold:.2f} combinations={evaluated_count} "
        f"min accepted accuracy={args.min_accepted_accuracy:.4f}"
    )
    baseline_accuracy = baseline["accepted_accuracy"]
    baseline_accuracy_text = (
        "n/a" if baseline_accuracy is None else f"{baseline_accuracy:.4f}"
    )
    print(
        "Baseline: "
        f"coverage={baseline['local_coverage']:.4f} "
        f"accepted_acc={baseline_accuracy_text} "
        f"fallback={baseline['fallback_rate']:.4f} "
        f"accepted_errors={len(baseline['accepted_errors'])}"
    )

    labels = sorted(label_grids)
    print("\nTop feasible policies by local coverage:")
    if not ranked:
        print("No policy satisfies the requested accepted-accuracy constraint.")
    else:
        for index, row in enumerate(ranked[: args.top], 1):
            print(
                f"{index:>4}  {format_thresholds(row, labels):<60} "
                f"coverage={row['local_coverage']:.4f} "
                f"accepted_acc={row['accepted_accuracy']:.4f} "
                f"fallback={row['fallback_rate']:.4f} "
                f"accepted_errors={len(row['accepted_errors'])}"
            )

    output = {
        "model": args.model,
        "detail_files": [str(path) for path in args.details],
        "decisions": len(keys),
        "default_threshold": args.default_threshold,
        "label_grids": label_grids,
        "combinations_evaluated": evaluated_count,
        "min_accepted_accuracy": args.min_accepted_accuracy,
        "baseline": {
            key: value
            for key, value in baseline.items()
            if key != "_route_signature"
        },
        "top_by_coverage": ranked[: args.top],
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
