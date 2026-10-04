from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from systemone_bench.cli import percentile


def load_request_rows(path: Path, model: str) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()

    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if str(row.get("model")) != model:
                continue

            case_id = str(row.get("case_id"))
            pass_no = int(row.get("pass", 1))
            key = (case_id, pass_no)
            if key in seen:
                continue
            seen.add(key)

            latency = row.get("latency_ms")
            if not isinstance(latency, (int, float)):
                raise ValueError(
                    f"{path}:{line_no}: latency_ms must be numeric"
                )

            requests.append(
                {
                    "position": len(requests) + 1,
                    "case_id": case_id,
                    "pass": pass_no,
                    "latency_ms": float(latency),
                    "expected": row.get("expected"),
                    "prediction": row.get("prediction"),
                    "correct": row.get("correct"),
                    "confidence": row.get("confidence"),
                    "cpu_percent_before": row.get("cpu_percent_before"),
                    "cpu_percent_after": row.get("cpu_percent_after"),
                    "memory_delta_mb": row.get("memory_delta_mb"),
                    "metadata": row.get("metadata") or {},
                }
            )

    if not requests:
        raise ValueError(f"{path}: no request rows found for model {model!r}")
    return requests


def latency_summary(rows: list[dict[str, Any]]) -> dict[str, float | int]:
    values = [float(row["latency_ms"]) for row in rows]
    return {
        "requests": len(values),
        "mean_ms": statistics.mean(values),
        "median_ms": statistics.median(values),
        "p90_ms": percentile(values, 0.90),
        "p95_ms": percentile(values, 0.95),
        "p99_ms": percentile(values, 0.99),
        "min_ms": min(values),
        "max_ms": max(values),
    }


def prefix_analysis(
    rows: list[dict[str, Any]],
    prefixes: list[int],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    total = len(rows)
    for size in prefixes:
        if size < 1 or size >= total:
            continue
        prefix = rows[:size]
        remainder = rows[size:]
        prefix_summary = latency_summary(prefix)
        remainder_summary = latency_summary(remainder)
        result.append(
            {
                "prefix_requests": size,
                "prefix": prefix_summary,
                "remainder": remainder_summary,
                "mean_ratio": (
                    float(prefix_summary["mean_ms"])
                    / float(remainder_summary["mean_ms"])
                ),
                "median_ratio": (
                    float(prefix_summary["median_ms"])
                    / float(remainder_summary["median_ms"])
                ),
            }
        )
    return result


def position_buckets(
    rows: list[dict[str, Any]],
    buckets: int,
) -> list[dict[str, Any]]:
    if buckets < 1:
        raise ValueError("buckets must be >= 1")

    total = len(rows)
    result: list[dict[str, Any]] = []
    for bucket in range(buckets):
        start = math.floor(bucket * total / buckets)
        end = math.floor((bucket + 1) * total / buckets)
        chunk = rows[start:end]
        if not chunk:
            continue
        result.append(
            {
                "bucket": bucket + 1,
                "start_position": int(chunk[0]["position"]),
                "end_position": int(chunk[-1]["position"]),
                **latency_summary(chunk),
            }
        )
    return result


def top_outliers(
    rows: list[dict[str, Any]],
    count: int,
) -> list[dict[str, Any]]:
    ranked = sorted(
        rows,
        key=lambda row: float(row["latency_ms"]),
        reverse=True,
    )[:count]
    result = []
    for row in ranked:
        metadata = row.get("metadata") or {}
        result.append(
            {
                "position": row["position"],
                "case_id": row["case_id"],
                "latency_ms": row["latency_ms"],
                "expected": row.get("expected"),
                "prediction": row.get("prediction"),
                "confidence": row.get("confidence"),
                "source_family": metadata.get("source_family"),
                "scenario_family": metadata.get("scenario_family"),
                "cpu_percent_before": row.get("cpu_percent_before"),
                "cpu_percent_after": row.get("cpu_percent_after"),
                "memory_delta_mb": row.get("memory_delta_mb"),
            }
        )
    return result


def group_latency(
    rows: list[dict[str, Any]],
    field: str,
) -> dict[str, dict[str, float | int]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if field.startswith("metadata."):
            key = (row.get("metadata") or {}).get(field.split(".", 1)[1])
        else:
            key = row.get(field)
        grouped[str(key)].append(row)
    return {
        key: latency_summary(group)
        for key, group in sorted(grouped.items())
    }


def late_tail_count(
    rows: list[dict[str, Any]],
    start_position: int,
    multiplier: float,
) -> dict[str, Any]:
    if multiplier <= 1.0:
        raise ValueError("tail multiplier must be > 1")

    median = statistics.median(
        float(row["latency_ms"]) for row in rows
    )
    threshold = median * multiplier
    late = [
        row for row in rows
        if int(row["position"]) >= start_position
        and float(row["latency_ms"]) >= threshold
    ]
    return {
        "baseline_median_ms": median,
        "multiplier": multiplier,
        "tail_threshold_ms": threshold,
        "start_position": start_position,
        "tail_count": len(late),
        "tail_positions": [int(row["position"]) for row in late],
        "tail_case_ids": [str(row["case_id"]) for row in late],
    }


def analyze(
    path: Path,
    model: str,
    prefixes: list[int],
    buckets: int,
    top: int,
    late_start: int,
    tail_multiplier: float,
) -> dict[str, Any]:
    rows = load_request_rows(path, model)
    overall = latency_summary(rows)
    prefix = prefix_analysis(rows, prefixes)
    position = position_buckets(rows, buckets)
    outliers = top_outliers(rows, top)
    late_tail = late_tail_count(
        rows,
        start_position=late_start,
        multiplier=tail_multiplier,
    )

    first_bucket = position[0] if position else None
    remaining_buckets = position[1:] if len(position) > 1 else []
    warmup_like = False
    if first_bucket and remaining_buckets:
        remainder_median = statistics.median(
            float(bucket["median_ms"]) for bucket in remaining_buckets
        )
        warmup_like = (
            float(first_bucket["median_ms"]) >= remainder_median * 1.25
        )

    return {
        "detail_file": str(path),
        "model": model,
        "overall": overall,
        "prefix_analysis": prefix,
        "position_buckets": position,
        "top_outliers": outliers,
        "by_expected": group_latency(rows, "expected"),
        "by_source_family": group_latency(rows, "metadata.source_family"),
        "by_scenario_family": group_latency(rows, "metadata.scenario_family"),
        "late_tail": late_tail,
        "diagnostics": {
            "first_bucket_warmup_like": warmup_like,
            "note": (
                "warmup-like means the first position bucket median is at "
                "least 25% slower than the median of later bucket medians. "
                "This is a heuristic, not causal proof."
            ),
        },
    }


def parse_int_list(raw: str) -> list[int]:
    values = []
    for item in raw.split(","):
        item = item.strip()
        if item:
            value = int(item)
            if value < 1:
                raise ValueError("prefix sizes must be >= 1")
            values.append(value)
    if not values:
        raise ValueError("at least one prefix size is required")
    return values


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Analyze request-latency tails from existing System One detail JSONL"
        )
    )
    ap.add_argument("--details", type=Path, required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument(
        "--prefixes",
        default="1,5,10,20,50",
        help="comma-separated prefix sizes compared against the remainder",
    )
    ap.add_argument(
        "--buckets",
        type=int,
        default=10,
        help="number of equal-position buckets",
    )
    ap.add_argument(
        "--top",
        type=int,
        default=20,
        help="number of highest-latency requests to report",
    )
    ap.add_argument(
        "--late-start",
        type=int,
        default=21,
        help="first request position considered 'late' for tail counting",
    )
    ap.add_argument(
        "--tail-multiplier",
        type=float,
        default=1.5,
        help="tail threshold as a multiple of the overall median",
    )
    ap.add_argument("--output", type=Path, default=None)
    args = ap.parse_args()

    try:
        result = analyze(
            args.details,
            args.model,
            parse_int_list(args.prefixes),
            args.buckets,
            args.top,
            args.late_start,
            args.tail_multiplier,
        )
    except ValueError as exc:
        ap.error(str(exc))

    overall = result["overall"]
    print(
        f"Latency tail analysis: model={args.model} "
        f"requests={overall['requests']} "
        f"median={overall['median_ms']:.1f}ms "
        f"p95={overall['p95_ms']:.1f}ms "
        f"p99={overall['p99_ms']:.1f}ms "
        f"max={overall['max_ms']:.1f}ms"
    )

    print("\nPrefix vs remainder:")
    for item in result["prefix_analysis"]:
        print(
            f"  first {item['prefix_requests']:>3}: "
            f"mean={item['prefix']['mean_ms']:.1f}ms "
            f"remainder={item['remainder']['mean_ms']:.1f}ms "
            f"ratio={item['mean_ratio']:.3f}"
        )

    print("\nPosition buckets:")
    for bucket in result["position_buckets"]:
        print(
            f"  {bucket['start_position']:>3}-{bucket['end_position']:<3}: "
            f"mean={bucket['mean_ms']:.1f}ms "
            f"median={bucket['median_ms']:.1f}ms "
            f"p95={bucket['p95_ms']:.1f}ms"
        )

    print("\nTop latency requests:")
    for row in result["top_outliers"]:
        print(
            f"  #{row['position']:>3} {row['case_id']} "
            f"{row['latency_ms']:.1f}ms "
            f"expected={row['expected']} "
            f"source={row['source_family']}"
        )

    late = result["late_tail"]
    print(
        "\nLate-tail diagnostic: "
        f"threshold={late['tail_threshold_ms']:.1f}ms "
        f"start_position={late['start_position']} "
        f"count={late['tail_count']}"
    )
    print(
        "First position bucket warmup-like: "
        f"{result['diagnostics']['first_bucket_warmup_like']}"
    )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"\nWrote {args.output}")


if __name__ == "__main__":
    main()
