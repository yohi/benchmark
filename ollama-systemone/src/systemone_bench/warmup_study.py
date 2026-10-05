from __future__ import annotations

import argparse
import json
import shlex
import statistics
import subprocess
import time
from pathlib import Path
from typing import Any

import httpx
import psutil

from systemone_bench.cli import (
    answer_confidence,
    answer_value,
    correct,
    load_jsonl,
)
from systemone_bench.latency_tail import (
    late_tail_count,
    latency_summary,
    prefix_analysis,
)
from systemone_bench.telemetry import (
    capture_request_telemetry,
    derive_request_telemetry,
)


PROFILE_SYNTHETIC = "synthetic-1"
PROFILE_REPRESENTATIVE = "representative-7"
PROFILES = (PROFILE_SYNTHETIC, PROFILE_REPRESENTATIVE)

REPRESENTATIVE_TASKS = {
    "implementation": (
        "Implement a small validation change in a sample repository and add "
        "a regression test."
    ),
    "debug": (
        "A test started failing unexpectedly. Diagnose the root cause before "
        "changing code."
    ),
    "review": (
        "Review an existing patch for correctness and risks without modifying it."
    ),
    "research": (
        "Research the current official documentation for a technical feature "
        "and compare the available options."
    ),
    "planning": (
        "Create an implementation and rollout plan without making the changes."
    ),
    "documentation": (
        "Write a developer guide describing an existing workflow without "
        "changing product behavior."
    ),
    "deterministic": (
        "Extract warning lines from a provided log and preserve their original order."
    ),
}


def build_profile_schedule(repeats: int) -> list[tuple[int, str]]:
    if repeats < 1:
        raise ValueError("repeats must be >= 1")

    schedule: list[tuple[int, str]] = []
    for repeat in range(1, repeats + 1):
        order = PROFILES if repeat % 2 == 1 else tuple(reversed(PROFILES))
        for profile in order:
            schedule.append((repeat, profile))
    return schedule


def synthetic_warmup_payload(model: str, keep_alive: str) -> dict[str, Any]:
    return {
        "model": model,
        "state": {"task": "Warm up the decision model before measurement."},
        "questions": {
            "warmup": {
                "type": "choice",
                "instructions": "Classify this synthetic warm-up request.",
                "criteria": {
                    "warmup": "A benchmark warm-up request.",
                    "other": "Any non-warm-up request.",
                },
            }
        },
        "keep_alive": keep_alive,
    }


def representative_warmup_payloads(
    model: str,
    route_question: dict[str, Any],
    keep_alive: str,
) -> list[dict[str, Any]]:
    criteria = route_question.get("criteria")
    if not isinstance(criteria, dict):
        raise ValueError("route question must contain criteria")

    missing = set(REPRESENTATIVE_TASKS) - set(criteria)
    if missing:
        raise ValueError(
            "route question is missing representative labels: "
            + ", ".join(sorted(missing))
        )

    payloads = []
    for label, task in REPRESENTATIVE_TASKS.items():
        payloads.append(
            {
                "model": model,
                "state": {"task": task},
                "questions": {
                    "route": {
                        "type": route_question["type"],
                        "instructions": route_question["instructions"],
                        "criteria": criteria,
                    }
                },
                "keep_alive": keep_alive,
                "_warmup_label": label,
            }
        )
    return payloads


def warmup_payloads(
    profile: str,
    model: str,
    route_question: dict[str, Any],
    keep_alive: str,
) -> list[dict[str, Any]]:
    if profile == PROFILE_SYNTHETIC:
        return [synthetic_warmup_payload(model, keep_alive)]
    if profile == PROFILE_REPRESENTATIVE:
        return representative_warmup_payloads(
            model,
            route_question,
            keep_alive,
        )
    raise ValueError(f"unknown profile: {profile}")


def summarize_trial(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise ValueError("trial rows must not be empty")

    summary = latency_summary(rows)
    prefixes = prefix_analysis(rows, [1, 5, 10, 20])
    prefix_map = {
        int(item["prefix_requests"]): item
        for item in prefixes
    }
    late = late_tail_count(
        rows,
        start_position=21,
        multiplier=1.5,
    )

    result: dict[str, Any] = {
        **summary,
        "late_tail_count": int(late["tail_count"]),
        "late_tail_threshold_ms": float(late["tail_threshold_ms"]),
    }
    for size in (1, 5, 10, 20):
        item = prefix_map.get(size)
        if item is None:
            continue
        result[f"first_{size}_mean_ms"] = float(item["prefix"]["mean_ms"])
        result[f"after_{size}_mean_ms"] = float(item["remainder"]["mean_ms"])
        result[f"first_{size}_mean_ratio"] = float(item["mean_ratio"])

    first20 = prefix_map.get(20)
    result["prefix_concentrated_tail"] = bool(
        first20 is not None
        and float(first20["mean_ratio"]) >= 1.25
        and int(late["tail_count"]) == 0
    )
    return result


def aggregate_profile_trials(
    trials: list[dict[str, Any]],
) -> dict[str, Any]:
    if not trials:
        raise ValueError("profile must contain at least one trial")

    metrics = [
        "mean_ms",
        "median_ms",
        "p95_ms",
        "p99_ms",
        "first_1_mean_ms",
        "first_5_mean_ms",
        "first_10_mean_ms",
        "first_20_mean_ms",
        "after_20_mean_ms",
        "first_20_mean_ratio",
    ]
    result: dict[str, Any] = {
        "trials": len(trials),
        "prefix_concentrated_tail_trials": sum(
            1 for trial in trials
            if trial["summary"]["prefix_concentrated_tail"]
        ),
        "late_tail_events_total": sum(
            int(trial["summary"]["late_tail_count"])
            for trial in trials
        ),
    }
    for metric in metrics:
        values = [
            float(trial["summary"][metric])
            for trial in trials
            if metric in trial["summary"]
        ]
        if values:
            result[f"{metric}_mean_across_trials"] = statistics.mean(values)
            result[f"{metric}_median_across_trials"] = statistics.median(values)
    return result


def compare_profiles(
    synthetic: dict[str, Any],
    representative: dict[str, Any],
) -> dict[str, Any]:
    metrics = [
        "first_1_mean_ms_mean_across_trials",
        "first_5_mean_ms_mean_across_trials",
        "first_10_mean_ms_mean_across_trials",
        "first_20_mean_ms_mean_across_trials",
        "after_20_mean_ms_mean_across_trials",
        "median_ms_mean_across_trials",
        "p95_ms_mean_across_trials",
    ]

    comparison: dict[str, Any] = {}
    for metric in metrics:
        base = synthetic.get(metric)
        candidate = representative.get(metric)
        if not isinstance(base, (int, float)) or not isinstance(
            candidate,
            (int, float),
        ):
            continue
        ratio = float(candidate) / float(base) if float(base) else None
        comparison[metric] = {
            "synthetic": float(base),
            "representative": float(candidate),
            "representative_over_synthetic": ratio,
            "reduction_fraction": (
                1.0 - ratio if ratio is not None else None
            ),
        }
    return comparison


def unload_model(
    client: httpx.Client,
    base_url: str,
    model: str,
) -> None:
    response = client.post(
        f"{base_url.rstrip('/')}/api/generate",
        json={"model": model, "keep_alive": 0},
    )
    response.raise_for_status()


def wait_for_ollama(
    client: httpx.Client,
    base_url: str,
    timeout: float,
) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        try:
            response = client.get(
                f"{base_url.rstrip('/')}/api/tags",
                timeout=min(5.0, timeout),
            )
            response.raise_for_status()
            return
        except (httpx.HTTPError, OSError) as exc:
            last_error = exc
            time.sleep(0.25)

    raise RuntimeError(
        f"Ollama did not become ready within {timeout}s"
    ) from last_error


def reset_runtime(
    client: httpx.Client,
    base_url: str,
    model: str,
    reset_mode: str,
    restart_command: str,
    restart_wait: float,
    timeout: float,
) -> dict[str, Any]:
    if reset_mode == "unload":
        unload_model(client, base_url, model)
        return {
            "mode": "unload",
            "restart_command": None,
            "restart_wait_seconds": None,
        }

    if reset_mode != "restart":
        raise ValueError(f"unknown reset mode: {reset_mode}")

    if not restart_command.strip():
        raise ValueError("restart mode requires --restart-command")

    command = shlex.split(restart_command)
    if not command:
        raise ValueError("restart command must not be empty")

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            "restart command failed with "
            f"exit status {exc.returncode}: {restart_command}"
        ) from exc

    if restart_wait > 0:
        time.sleep(restart_wait)

    wait_for_ollama(client, base_url, timeout)
    return {
        "mode": "restart",
        "restart_command": restart_command,
        "restart_wait_seconds": restart_wait,
    }


def execute_warmups(
    client: httpx.Client,
    base_url: str,
    payloads: list[dict[str, Any]],
    profile: str,
) -> list[dict[str, Any]]:
    observations = []
    for index, raw_payload in enumerate(payloads, 1):
        payload = dict(raw_payload)
        label = payload.pop("_warmup_label", None)
        started = time.perf_counter()
        response = client.post(
            f"{base_url.rstrip('/')}/v1/systemone",
            json=payload,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        response.raise_for_status()
        observations.append(
            {
                "profile": profile,
                "warmup_index": index,
                "label": label,
                "latency_ms": elapsed_ms,
            }
        )
        print(
            f"    warmup {index}/{len(payloads)} "
            f"label={label or 'synthetic'} latency={elapsed_ms:.1f}ms",
            flush=True,
        )
    return observations


def execute_measured_workload(
    client: httpx.Client,
    base_url: str,
    model: str,
    keep_alive: str,
    rows: list[dict[str, Any]],
    repeat: int,
    profile: str,
    trial_order: int,
    request_telemetry: bool = False,
) -> list[dict[str, Any]]:
    observations = []
    for position, row in enumerate(rows, 1):
        payload = {
            "model": model,
            "state": row["state"],
            "questions": row["questions"],
            "keep_alive": keep_alive,
        }
        cpu_before = psutil.cpu_percent(interval=None)
        memory_before = psutil.virtual_memory().used
        telemetry_before = (
            capture_request_telemetry()
            if request_telemetry
            else None
        )
        started = time.perf_counter()
        response = client.post(
            f"{base_url.rstrip('/')}/v1/systemone",
            json=payload,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        telemetry_after = (
            capture_request_telemetry()
            if request_telemetry
            else None
        )
        cpu_after = psutil.cpu_percent(interval=None)
        memory_after = psutil.virtual_memory().used
        response.raise_for_status()
        body = response.json()

        question_name, question = next(iter(row["questions"].items()))
        answer = body.get("answers", {}).get(question_name, {})
        qtype = question["type"]
        prediction = answer_value(answer, qtype)
        expected = row.get("expected", {}).get(question_name)

        observations.append(
            {
                "model": model,
                "repeat": repeat,
                "profile": profile,
                "trial_order": trial_order,
                "position": position,
                "case_id": row["id"],
                "latency_ms": elapsed_ms,
                "prediction": prediction,
                "expected": expected,
                "correct": correct(prediction, expected, qtype),
                "confidence": answer_confidence(answer, qtype),
                "cpu_percent_before": cpu_before,
                "cpu_percent_after": cpu_after,
                "memory_delta_mb": (
                    memory_after - memory_before
                ) / 1024 / 1024,
                "request_telemetry": (
                    derive_request_telemetry(
                        telemetry_before,
                        telemetry_after,
                        elapsed_ms,
                    )
                    if telemetry_before is not None
                    and telemetry_after is not None
                    else None
                ),
                "metadata": row.get("metadata") or {},
            }
        )
        print(
            f"    measured {position:>2}/{len(rows)} "
            f"case={row['id']} latency={elapsed_ms:.1f}ms",
            flush=True,
        )
    return observations


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Compare current synthetic warmup against representative routing "
            "warmups using the same fixed measured workload"
        )
    )
    ap.add_argument(
        "--dataset",
        type=Path,
        default=Path("datasets/latency-warmup-fixed-workload.jsonl"),
    )
    ap.add_argument("--model", default="nimble")
    ap.add_argument("--repeats", type=int, default=2)
    ap.add_argument("--base-url", default="http://localhost:11434")
    ap.add_argument("--timeout", type=float, default=300)
    ap.add_argument("--keep-alive", default="10m")
    ap.add_argument(
        "--reset-mode",
        choices=("unload", "restart"),
        default="unload",
        help=(
            "trial reset boundary: unload only the model or restart the "
            "Ollama process/service"
        ),
    )
    ap.add_argument(
        "--restart-command",
        default="",
        help=(
            "command used with --reset-mode restart, e.g. "
            "'sudo systemctl restart ollama'"
        ),
    )
    ap.add_argument(
        "--restart-wait",
        type=float,
        default=2.0,
        help="seconds to wait after restart before probing Ollama readiness",
    )
    ap.add_argument(
        "--request-telemetry",
        action="store_true",
        help=(
            "capture lightweight host and Ollama process telemetry before "
            "and after every measured request"
        ),
    )
    ap.add_argument("--output", type=Path, default=Path("results"))

    args = ap.parse_args()

    try:
        schedule = build_profile_schedule(args.repeats)
    except ValueError as exc:
        ap.error(str(exc))

    if args.reset_mode == "restart" and not args.restart_command.strip():
        ap.error("--reset-mode restart requires --restart-command")

    rows = load_jsonl(args.dataset)
    if len(rows) <= 20:
        ap.error("warmup study dataset must contain more than 20 requests")

    route_question = rows[0]["questions"].get("route")
    if not isinstance(route_question, dict):
        ap.error("dataset must contain a 'route' question")

    args.output.mkdir(parents=True, exist_ok=True)
    run_id = time.strftime("%Y%m%d-%H%M%S")
    all_details: list[dict[str, Any]] = []
    trials: list[dict[str, Any]] = []

    print(
        f"Warmup study: model={args.model} measured={len(rows)} "
        f"repeats={args.repeats} trials={len(schedule)}",
        flush=True,
    )

    with httpx.Client(timeout=args.timeout) as client:
        for trial_order, (repeat, profile) in enumerate(schedule, 1):
            print(
                f"\n[{trial_order}/{len(schedule)}] "
                f"repeat={repeat} profile={profile}: "
                f"reset={args.reset_mode}",
                flush=True,
            )
            reset_observation = reset_runtime(
                client=client,
                base_url=args.base_url,
                model=args.model,
                reset_mode=args.reset_mode,
                restart_command=args.restart_command,
                restart_wait=args.restart_wait,
                timeout=args.timeout,
            )

            payloads = warmup_payloads(
                profile,
                args.model,
                route_question,
                args.keep_alive,
            )
            warmups = execute_warmups(
                client,
                args.base_url,
                payloads,
                profile,
            )

            measured = execute_measured_workload(
                client,
                args.base_url,
                args.model,
                args.keep_alive,
                rows,
                repeat,
                profile,
                trial_order,
                request_telemetry=args.request_telemetry,
            )
            all_details.extend(measured)
            summary = summarize_trial(measured)

            trials.append(
                {
                    "repeat": repeat,
                    "profile": profile,
                    "trial_order": trial_order,
                    "reset": reset_observation,
                    "warmups": warmups,
                    "summary": summary,
                }
            )
            print(
                f"  summary profile={profile} repeat={repeat}: "
                f"first5={summary['first_5_mean_ms']:.1f}ms "
                f"first20_ratio={summary['first_20_mean_ratio']:.3f} "
                f"median={summary['median_ms']:.1f}ms "
                f"p95={summary['p95_ms']:.1f}ms "
                f"prefix_tail={summary['prefix_concentrated_tail']}",
                flush=True,
            )

    by_profile: dict[str, dict[str, Any]] = {}
    for profile in PROFILES:
        profile_trials = [
            trial for trial in trials if trial["profile"] == profile
        ]
        by_profile[profile] = aggregate_profile_trials(profile_trials)

    comparison = compare_profiles(
        by_profile[PROFILE_SYNTHETIC],
        by_profile[PROFILE_REPRESENTATIVE],
    )

    result = {
        "run_id": run_id,
        "model": args.model,
        "dataset": str(args.dataset),
        "repeats": args.repeats,
        "schedule": [
            {"repeat": repeat, "profile": profile}
            for repeat, profile in schedule
        ],
        "trials": trials,
        "by_profile": by_profile,
        "comparison": comparison,
        "methodology": {
            "reset": (
                "model unload before every trial"
                if args.reset_mode == "unload"
                else "Ollama process/service restart before every trial"
            ),
            "reset_mode": args.reset_mode,
            "restart_command": (
                args.restart_command
                if args.reset_mode == "restart"
                else None
            ),
            "restart_wait_seconds": (
                args.restart_wait
                if args.reset_mode == "restart"
                else None
            ),
            "synthetic_profile": "one existing generic synthetic warmup request",
            "representative_profile": (
                "seven distinct warmup requests using the same seven-class "
                "routing schema, one per routing label"
            ),
            "measured_workload": (
                "identical 35-request sequence for every trial; warmup tasks "
                "are not measured workload tasks"
            ),
            "order_control": (
                "profile order alternates by repeat to reduce temporal-order bias"
            ),
            "request_telemetry": args.request_telemetry,
            "request_telemetry_fields": (
                [
                    "CPU frequency before/after",
                    "system load before/after",
                    "temperature sensors before/after when available",
                    "Ollama process PID/create time/RSS/CPU time",
                    "system available memory",
                    "derived Ollama CPU percent over request",
                    "derived Ollama RSS delta",
                    "derived Ollama process identity change",
                ]
                if args.request_telemetry
                else []
            ),
        },
    }

    detail_path = args.output / f"{run_id}-warmup-study-details.jsonl"
    detail_path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False) + "\n"
            for row in all_details
        ),
        encoding="utf-8",
    )
    summary_path = args.output / f"{run_id}-warmup-study.json"
    summary_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("\nProfile comparison:")
    for metric, item in comparison.items():
        print(
            f"  {metric}: synthetic={item['synthetic']:.1f} "
            f"representative={item['representative']:.1f} "
            f"ratio={item['representative_over_synthetic']:.3f} "
            f"reduction={item['reduction_fraction']:.3f}"
        )

    print(f"\nDetails: {detail_path}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
