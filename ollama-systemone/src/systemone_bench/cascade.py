from __future__ import annotations

import argparse
import itertools
import json
import math
import statistics
from pathlib import Path
from typing import Any

DecisionKey = tuple[str, int, str]


def percentile(values: list[float], p: float) -> float:
    if not values:
        return math.nan
    xs = sorted(values)
    k = (len(xs) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return xs[lo]
    return xs[lo] * (hi - k) + xs[hi] * (k - lo)


def parse_threshold_grid(spec: str) -> list[float]:
    values: list[float] = []
    for raw in spec.split(","):
        token = raw.strip()
        if not token:
            continue
        if ":" not in token:
            values.append(float(token))
            continue

        parts = token.split(":")
        if len(parts) not in (2, 3):
            raise ValueError(f"invalid threshold range: {token}")
        start = float(parts[0])
        stop = float(parts[1])
        step = float(parts[2]) if len(parts) == 3 else 0.01
        if step <= 0:
            raise ValueError(f"threshold step must be > 0: {token}")
        current = start
        while current <= stop + 1e-12:
            values.append(round(current, 10))
            current += step

    unique = sorted(set(values))
    if not unique:
        raise ValueError("threshold grid is empty")
    if any(v < 0.0 or v > 1.0 for v in unique):
        raise ValueError("thresholds must be between 0 and 1")
    return unique


def load_details(paths: list[Path]) -> dict[str, dict[DecisionKey, dict[str, Any]]]:
    by_model: dict[str, dict[DecisionKey, dict[str, Any]]] = {}
    request_questions: dict[tuple[str, str, int], set[str]] = {}

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
                    raise ValueError(f"{path}:{line_no}: missing required field {exc.args[0]!r}") from exc

                key = (case_id, pass_no, question)
                model_rows = by_model.setdefault(model, {})
                if key in model_rows:
                    raise ValueError(
                        f"duplicate decision for model={model!r}, case={case_id!r}, "
                        f"pass={pass_no}, question={question!r}; do not mix duplicate runs"
                    )
                if row.get("correct") is None:
                    raise ValueError(
                        f"{path}:{line_no}: cascade analysis requires labeled decisions "
                        f"(correct must not be null)"
                    )
                confidence = row.get("confidence")
                if not isinstance(confidence, (int, float)):
                    raise ValueError(
                        f"{path}:{line_no}: cascade analysis requires numeric confidence"
                    )
                latency = row.get("latency_ms")
                if not isinstance(latency, (int, float)):
                    raise ValueError(
                        f"{path}:{line_no}: cascade analysis requires numeric latency_ms"
                    )

                model_rows[key] = row
                request_questions.setdefault((model, case_id, pass_no), set()).add(question)

    if not by_model:
        raise ValueError("no detail rows found")

    multi_question = [
        (model, case_id, pass_no, questions)
        for (model, case_id, pass_no), questions in request_questions.items()
        if len(questions) != 1
    ]
    if multi_question:
        model, case_id, pass_no, questions = multi_question[0]
        raise ValueError(
            "cascade latency simulation currently requires one decision per HTTP request; "
            f"found {len(questions)} questions for model={model!r}, case={case_id!r}, "
            f"pass={pass_no}"
        )

    return by_model


def validate_selected_models(
    by_model: dict[str, dict[DecisionKey, dict[str, Any]]],
    models: list[str],
) -> list[DecisionKey]:
    if not models:
        raise ValueError("at least one model is required")
    if len(set(models)) != len(models):
        raise ValueError("model order contains duplicates")

    missing = [model for model in models if model not in by_model]
    if missing:
        raise ValueError(
            f"missing model(s) in supplied detail files: {', '.join(missing)}; "
            f"available: {', '.join(sorted(by_model))}"
        )

    baseline_keys = set(by_model[models[0]])
    for model in models[1:]:
        keys = set(by_model[model])
        if keys != baseline_keys:
            missing_keys = baseline_keys - keys
            extra_keys = keys - baseline_keys
            raise ValueError(
                f"model {model!r} does not contain the same decision set as {models[0]!r}: "
                f"missing={len(missing_keys)}, extra={len(extra_keys)}"
            )

    for key in baseline_keys:
        expected = by_model[models[0]][key].get("expected")
        for model in models[1:]:
            if by_model[model][key].get("expected") != expected:
                raise ValueError(f"expected label differs across models for decision {key!r}")

    return sorted(baseline_keys)


def simulate(
    by_model: dict[str, dict[DecisionKey, dict[str, Any]]],
    keys: list[DecisionKey],
    models: list[str],
    thresholds: tuple[float, ...],
    fallback_latency_ms: float | None,
) -> dict[str, Any]:
    accepted = 0
    accepted_correct = 0
    fallback_count = 0
    local_calls = 0
    local_latencies: list[float] = []
    end_to_end_latencies: list[float] = []
    route_signature: list[str] = []
    stages: dict[str, dict[str, int]] = {
        model: {"reached": 0, "accepted": 0, "correct": 0}
        for model in models
    }

    for key in keys:
        local_latency = 0.0
        accepted_here = False

        for model, threshold in zip(models, thresholds, strict=True):
            row = by_model[model][key]
            stages[model]["reached"] += 1
            local_calls += 1
            local_latency += float(row["latency_ms"])

            if float(row["confidence"]) >= threshold:
                accepted_here = True
                accepted += 1
                stages[model]["accepted"] += 1
                if bool(row["correct"]):
                    accepted_correct += 1
                    stages[model]["correct"] += 1
                break

        local_latencies.append(local_latency)
        if accepted_here:
            route_signature.append(model)
            end_to_end_latencies.append(local_latency)
        else:
            route_signature.append("fallback")
            fallback_count += 1
            if fallback_latency_ms is not None:
                end_to_end_latencies.append(local_latency + fallback_latency_ms)

    total = len(keys)
    coverage = accepted / total if total else 0.0
    accepted_accuracy = accepted_correct / accepted if accepted else None
    avg_local_latency = statistics.mean(local_latencies) if local_latencies else math.nan

    stage_summary: dict[str, dict[str, float | int | None]] = {}
    for model in models:
        stage = stages[model]
        stage_summary[model] = {
            "reached": stage["reached"],
            "accepted": stage["accepted"],
            "acceptance_of_total": stage["accepted"] / total if total else 0.0,
            "acceptance_of_reached": stage["accepted"] / stage["reached"] if stage["reached"] else 0.0,
            "accepted_accuracy": stage["correct"] / stage["accepted"] if stage["accepted"] else None,
        }

    result: dict[str, Any] = {
        "thresholds": {model: threshold for model, threshold in zip(models, thresholds, strict=True)},
        "decisions": total,
        "local_accepted": accepted,
        "local_coverage": coverage,
        "accepted_accuracy": accepted_accuracy,
        "fallback_count": fallback_count,
        "fallback_rate": fallback_count / total if total else 0.0,
        "avg_local_latency_ms": avg_local_latency,
        "p50_local_latency_ms": percentile(local_latencies, 0.50),
        "p95_local_latency_ms": percentile(local_latencies, 0.95),
        "local_calls_per_request": local_calls / total if total else 0.0,
        "fallback_calls_per_request": fallback_count / total if total else 0.0,
        "total_calls_per_request": (local_calls + fallback_count) / total if total else 0.0,
        "stages": stage_summary,
        "_route_signature": route_signature,
    }
    if fallback_latency_ms is not None:
        result.update(
            {
                "fallback_latency_ms": fallback_latency_ms,
                "avg_end_to_end_latency_ms": statistics.mean(end_to_end_latencies),
                "p50_end_to_end_latency_ms": percentile(end_to_end_latencies, 0.50),
                "p95_end_to_end_latency_ms": percentile(end_to_end_latencies, 0.95),
            }
        )
    return result


def dominates(a: dict[str, Any], b: dict[str, Any]) -> bool:
    at_least_as_good = (
        a["local_coverage"] >= b["local_coverage"]
        and a["avg_local_latency_ms"] <= b["avg_local_latency_ms"]
        and a["local_calls_per_request"] <= b["local_calls_per_request"]
    )
    strictly_better = (
        a["local_coverage"] > b["local_coverage"]
        or a["avg_local_latency_ms"] < b["avg_local_latency_ms"]
        or a["local_calls_per_request"] < b["local_calls_per_request"]
    )
    return at_least_as_good and strictly_better


def pareto_frontier(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    frontier = []
    for candidate in rows:
        if not any(dominates(other, candidate) for other in rows if other is not candidate):
            frontier.append(candidate)
    return sorted(
        frontier,
        key=lambda row: (
            -row["local_coverage"],
            row["avg_local_latency_ms"],
            row["local_calls_per_request"],
        ),
    )


def collapse_equivalent(
    rows: list[dict[str, Any]],
    models: list[str],
) -> list[dict[str, Any]]:
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for row in rows:
        signature = tuple(row["_route_signature"])
        groups.setdefault(signature, []).append(row)

    collapsed: list[dict[str, Any]] = []
    for group in groups.values():
        # Prefer the highest thresholds as the representative of an identical
        # routing plateau while preserving the full equivalent range.
        representative = max(
            group,
            key=lambda row: tuple(row["thresholds"][model] for model in models),
        )
        item = {key: value for key, value in representative.items() if key != "_route_signature"}
        item["threshold_ranges"] = {
            model: {
                "min": min(row["thresholds"][model] for row in group),
                "max": max(row["thresholds"][model] for row in group),
            }
            for model in models
        }
        item["equivalent_configurations"] = len(group)
        collapsed.append(item)
    return collapsed


def best_single_model_baselines(
    by_model: dict[str, dict[DecisionKey, dict[str, Any]]],
    keys: list[DecisionKey],
    models: list[str],
    grid: list[float],
    min_accepted_accuracy: float,
    fallback_latency_ms: float | None,
) -> dict[str, dict[str, Any] | None]:
    baselines: dict[str, dict[str, Any] | None] = {}
    for model in models:
        rows = [
            simulate(by_model, keys, [model], (threshold,), fallback_latency_ms)
            for threshold in grid
        ]
        feasible = [
            row
            for row in rows
            if row["accepted_accuracy"] is not None
            and row["accepted_accuracy"] >= min_accepted_accuracy
        ]
        collapsed = collapse_equivalent(feasible, [model])
        ranked = sorted(
            collapsed,
            key=lambda row: (
                -row["local_coverage"],
                row["avg_local_latency_ms"],
                row["local_calls_per_request"],
            ),
        )
        baselines[model] = ranked[0] if ranked else None
    return baselines


def print_table(rows: list[dict[str, Any]], models: list[str]) -> None:
    if not rows:
        print("No configurations satisfy the requested accepted-accuracy constraint.")
        return

    header = (
        "rank  thresholds  coverage  accepted_acc  fallback  "
        "avg_local_ms  p95_local_ms  local_calls"
    )
    print(header)
    for index, row in enumerate(rows, 1):
        ranges = row.get("threshold_ranges", {})
        threshold_parts = []
        for model in models:
            threshold_range = ranges.get(model)
            if threshold_range and threshold_range["min"] != threshold_range["max"]:
                threshold_parts.append(
                    f"{model}={threshold_range['min']:.2f}..{threshold_range['max']:.2f}"
                )
            else:
                threshold_parts.append(f"{model}={row['thresholds'][model]:.2f}")
        threshold_text = ",".join(threshold_parts)
        accuracy = row["accepted_accuracy"]
        accuracy_text = "n/a" if accuracy is None else f"{accuracy:.4f}"
        print(
            f"{index:>4}  {threshold_text:<35} "
            f"{row['local_coverage']:.4f}    {accuracy_text:>12}  "
            f"{row['fallback_rate']:.4f}    "
            f"{row['avg_local_latency_ms']:>12.1f}  "
            f"{row['p95_local_latency_ms']:>12.1f}  "
            f"{row['local_calls_per_request']:.3f}"
        )


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Simulate confidence-gated System One model cascades from benchmark detail JSONL"
    )
    ap.add_argument(
        "--details",
        type=Path,
        nargs="+",
        required=True,
        help="one or more *-details.jsonl files; duplicate model/case rows are rejected",
    )
    ap.add_argument(
        "--models",
        required=True,
        help="comma-separated cascade order, e.g. tev1:4b,nimble",
    )
    ap.add_argument(
        "--thresholds",
        default="0.60:0.95:0.05,0.98,0.99",
        help="threshold grid shared by all stages; supports start:stop:step syntax",
    )
    ap.add_argument(
        "--min-accepted-accuracy",
        type=float,
        default=1.0,
        help="minimum accuracy required among locally accepted decisions",
    )
    ap.add_argument(
        "--fallback-latency-ms",
        type=float,
        default=None,
        help="optional assumed paid/fallback latency for end-to-end latency estimates",
    )
    ap.add_argument("--top", type=int, default=20, help="number of coverage-ranked rows to print/store")
    ap.add_argument(
        "--max-combinations",
        type=int,
        default=100000,
        help="guard against accidental combinatorial explosions",
    )
    ap.add_argument("--output", type=Path, default=None, help="optional JSON output path")
    args = ap.parse_args()

    if not 0.0 <= args.min_accepted_accuracy <= 1.0:
        ap.error("--min-accepted-accuracy must be between 0 and 1")
    if args.fallback_latency_ms is not None and args.fallback_latency_ms < 0:
        ap.error("--fallback-latency-ms must be >= 0")
    if args.top < 1:
        ap.error("--top must be >= 1")

    try:
        models = [item.strip() for item in args.models.split(",") if item.strip()]
        grid = parse_threshold_grid(args.thresholds)
        combinations = len(grid) ** len(models)
        if combinations > args.max_combinations:
            raise ValueError(
                f"threshold grid would evaluate {combinations} combinations; "
                f"increase --max-combinations or reduce the grid"
            )

        by_model = load_details(args.details)
        keys = validate_selected_models(by_model, models)
    except ValueError as exc:
        ap.error(str(exc))

    all_results = [
        simulate(by_model, keys, models, thresholds, args.fallback_latency_ms)
        for thresholds in itertools.product(grid, repeat=len(models))
    ]
    feasible = [
        row
        for row in all_results
        if row["accepted_accuracy"] is not None
        and row["accepted_accuracy"] >= args.min_accepted_accuracy
    ]
    collapsed_feasible = collapse_equivalent(feasible, models)
    coverage_ranked = sorted(
        collapsed_feasible,
        key=lambda row: (
            -row["local_coverage"],
            row["avg_local_latency_ms"],
            row["local_calls_per_request"],
        ),
    )
    frontier = pareto_frontier(collapsed_feasible)
    baselines = best_single_model_baselines(
        by_model,
        keys,
        models,
        grid,
        args.min_accepted_accuracy,
        args.fallback_latency_ms,
    )

    print(
        f"Cascade: {' -> '.join(models)} | decisions={len(keys)} | "
        f"grid={len(grid)} threshold(s)/stage | combinations={len(all_results)} | "
        f"min accepted accuracy={args.min_accepted_accuracy:.4f}"
    )
    print("\nSingle-model baselines:")
    for model in models:
        baseline = baselines[model]
        if baseline is None:
            print(f"  {model}: no configuration satisfies the accuracy constraint")
            continue
        threshold_range = baseline["threshold_ranges"][model]
        if threshold_range["min"] == threshold_range["max"]:
            threshold_text = f"{threshold_range['min']:.2f}"
        else:
            threshold_text = f"{threshold_range['min']:.2f}..{threshold_range['max']:.2f}"
        print(
            f"  {model}: threshold={threshold_text} "
            f"coverage={baseline['local_coverage']:.4f} "
            f"accepted_acc={baseline['accepted_accuracy']:.4f} "
            f"fallback={baseline['fallback_rate']:.4f} "
            f"avg_local_ms={baseline['avg_local_latency_ms']:.1f}"
        )

    print("\nTop configurations by local coverage:")
    print_table(coverage_ranked[: args.top], models)
    print("\nPareto frontier (coverage vs local latency/calls):")
    print_table(frontier[: args.top], models)

    output = {
        "models": models,
        "detail_files": [str(path) for path in args.details],
        "decisions": len(keys),
        "threshold_grid": grid,
        "combinations_evaluated": len(all_results),
        "min_accepted_accuracy": args.min_accepted_accuracy,
        "fallback_latency_ms": args.fallback_latency_ms,
        "single_model_baselines": baselines,
        "top_by_coverage": coverage_ranked[: args.top],
        "pareto_frontier": frontier,
    }

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
        print(f"\nJSON: {args.output}")


if __name__ == "__main__":
    main()
