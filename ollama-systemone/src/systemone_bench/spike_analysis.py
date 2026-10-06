from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Any


def load_rows(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            latency = row.get("latency_ms")
            if not isinstance(latency, (int, float)):
                raise ValueError(
                    f"{path}:{line_no}: latency_ms must be numeric"
                )
            if not isinstance(row.get("request_telemetry"), dict):
                continue
            rows.append(row)
    if not rows:
        raise ValueError(
            f"{path}: no rows with request_telemetry were found"
        )
    return rows


def _path_value(row: dict[str, Any], path: str) -> float | None:
    value: Any = row
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    if not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


METRICS = {
    "cpu_freq_before_mhz": (
        "request_telemetry.before.cpu_frequency.current_mhz_mean"
    ),
    "cpu_freq_after_mhz": (
        "request_telemetry.after.cpu_frequency.current_mhz_mean"
    ),
    "load1_before": "request_telemetry.before.load_average.load1",
    "load1_after": "request_telemetry.after.load_average.load1",
    "temperature_before_c": (
        "request_telemetry.before.temperature.max_c"
    ),
    "temperature_after_c": (
        "request_telemetry.after.temperature.max_c"
    ),
    "ollama_rss_before_bytes": (
        "request_telemetry.before.ollama.rss_bytes_total"
    ),
    "ollama_rss_after_bytes": (
        "request_telemetry.after.ollama.rss_bytes_total"
    ),
    "system_available_before_bytes": (
        "request_telemetry.before.system_memory.available_bytes"
    ),
    "ollama_cpu_percent_over_request": (
        "request_telemetry.derived.ollama_cpu_percent_over_request"
    ),
    "ollama_process_count_before": (
        "request_telemetry.before.ollama.process_count"
    ),
    "ollama_descendant_only_count_before": (
        "request_telemetry.before.ollama.descendant_only_process_count"
    ),
}


def pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3 or len(xs) != len(ys):
        return None

    mean_x = statistics.mean(xs)
    mean_y = statistics.mean(ys)
    dx = [value - mean_x for value in xs]
    dy = [value - mean_y for value in ys]
    denom = math.sqrt(
        sum(value * value for value in dx)
        * sum(value * value for value in dy)
    )
    if denom == 0:
        return None
    return sum(x * y for x, y in zip(dx, dy)) / denom


def metric_summary(
    rows: list[dict[str, Any]],
    metric_path: str,
) -> dict[str, Any]:
    pairs = [
        (float(row["latency_ms"]), _path_value(row, metric_path))
        for row in rows
    ]
    usable = [(latency, value) for latency, value in pairs if value is not None]
    if not usable:
        return {
            "n": 0,
            "mean": None,
            "median": None,
            "latency_pearson_r": None,
        }

    latencies = [item[0] for item in usable]
    values = [float(item[1]) for item in usable]
    return {
        "n": len(values),
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
        "latency_pearson_r": pearson(latencies, values),
    }


def group_diagnostics(
    rows: list[dict[str, Any]],
    spike_threshold: float,
) -> dict[str, Any]:
    if not rows:
        return {
            "requests": 0,
            "median_latency_ms": None,
            "spike_count": 0,
            "spike_rate": None,
            "metrics": {},
        }

    spikes = [
        row for row in rows
        if float(row["latency_ms"]) >= spike_threshold
    ]
    metrics = {
        name: metric_summary(rows, path)
        for name, path in METRICS.items()
    }
    return {
        "requests": len(rows),
        "median_latency_ms": statistics.median(
            float(row["latency_ms"]) for row in rows
        ),
        "spike_count": len(spikes),
        "spike_rate": len(spikes) / len(rows),
        "metrics": metrics,
    }


def analyze(
    rows: list[dict[str, Any]],
    spike_multiplier: float,
    top: int,
) -> dict[str, Any]:
    if spike_multiplier <= 1.0:
        raise ValueError("spike multiplier must be > 1")

    latencies = [float(row["latency_ms"]) for row in rows]
    median_latency = statistics.median(latencies)
    spike_threshold = median_latency * spike_multiplier

    spikes = [
        row for row in rows
        if float(row["latency_ms"]) >= spike_threshold
    ]
    non_spikes = [
        row for row in rows
        if float(row["latency_ms"]) < spike_threshold
    ]

    metric_results: dict[str, Any] = {}
    for name, path in METRICS.items():
        metric_results[name] = {
            "all": metric_summary(rows, path),
            "spikes": metric_summary(spikes, path),
            "non_spikes": metric_summary(non_spikes, path),
        }

    ranked = sorted(
        rows,
        key=lambda row: float(row["latency_ms"]),
        reverse=True,
    )[:top]

    grouped_trials: dict[str, list[dict[str, Any]]] = {}
    grouped_profiles: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        trial_key = str(row.get("trial_order"))
        profile_key = str(row.get("profile"))
        grouped_trials.setdefault(trial_key, []).append(row)
        grouped_profiles.setdefault(profile_key, []).append(row)

    return {
        "requests": len(rows),
        "median_latency_ms": median_latency,
        "spike_multiplier": spike_multiplier,
        "spike_threshold_ms": spike_threshold,
        "spike_count": len(spikes),
        "spike_rate": len(spikes) / len(rows),
        "metrics": metric_results,
        "by_trial": {
            key: group_diagnostics(group, spike_threshold)
            for key, group in sorted(
                grouped_trials.items(),
                key=lambda item: int(item[0]) if item[0].isdigit() else item[0],
            )
        },
        "by_profile": {
            key: group_diagnostics(group, spike_threshold)
            for key, group in sorted(grouped_profiles.items())
        },
        "top_latency_requests": [
            {
                "latency_ms": float(row["latency_ms"]),
                "case_id": row.get("case_id"),
                "repeat": row.get("repeat"),
                "profile": row.get("profile"),
                "trial_order": row.get("trial_order"),
                "position": row.get("position"),
                "telemetry": {
                    name: _path_value(row, path)
                    for name, path in METRICS.items()
                },
                "ollama_process_identity_changed": (
                    row.get("request_telemetry", {})
                    .get("derived", {})
                    .get("ollama_process_identity_changed")
                ),
            }
            for row in ranked
        ],
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Analyze latency spikes against request-level host/Ollama telemetry"
        )
    )
    ap.add_argument("--details", type=Path, required=True)
    ap.add_argument(
        "--spike-multiplier",
        type=float,
        default=1.25,
        help="spike threshold as a multiple of median latency",
    )
    ap.add_argument(
        "--top",
        type=int,
        default=20,
        help="number of highest-latency requests to report",
    )
    ap.add_argument("--output", type=Path, default=None)
    args = ap.parse_args()

    try:
        rows = load_rows(args.details)
        result = analyze(
            rows,
            spike_multiplier=args.spike_multiplier,
            top=args.top,
        )
    except ValueError as exc:
        ap.error(str(exc))

    print(
        "Spike telemetry analysis: "
        f"requests={result['requests']} "
        f"median={result['median_latency_ms']:.1f}ms "
        f"threshold={result['spike_threshold_ms']:.1f}ms "
        f"spikes={result['spike_count']} "
        f"rate={result['spike_rate']:.3f}"
    )

    print("\nMetric correlation / spike comparison:")
    for name, metric in result["metrics"].items():
        all_summary = metric["all"]
        spike_summary = metric["spikes"]
        normal_summary = metric["non_spikes"]
        print(
            f"  {name}: n={all_summary['n']} "
            f"r={all_summary['latency_pearson_r']} "
            f"spike_mean={spike_summary['mean']} "
            f"non_spike_mean={normal_summary['mean']}"
        )

    print("\nBy trial:")
    for trial, summary in result["by_trial"].items():
        print(
            f"  trial={trial}: requests={summary['requests']} "
            f"median={summary['median_latency_ms']:.1f}ms "
            f"spikes={summary['spike_count']} "
            f"rate={summary['spike_rate']:.3f}"
        )

    print("\nTop latency requests:")
    for row in result["top_latency_requests"]:
        print(
            f"  latency={row['latency_ms']:.1f}ms "
            f"trial={row['trial_order']} "
            f"repeat={row['repeat']} "
            f"profile={row['profile']} "
            f"position={row['position']} "
            f"case={row['case_id']}"
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
