from __future__ import annotations

import argparse
import json
import os
import platform
import re
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import psutil

from systemone_bench.cli import (
    answer_confidence,
    answer_value,
    correct,
    load_jsonl,
    percentile,
)


@dataclass(frozen=True)
class Provider:
    name: str
    url: str
    model: str | None = None
    health_url: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    request_fields: dict[str, Any] = field(default_factory=dict)
    response_path: tuple[str, ...] = ()


ENV_REFERENCE_RE = re.compile(
    r"\$(?:\{(?P<braced>[A-Za-z_][A-Za-z0-9_]*)\}|"
    r"(?P<plain>[A-Za-z_][A-Za-z0-9_]*))"
)


def expand_environment(value: str, *, provider_name: str, field_name: str) -> str:
    missing = {
        match.group("braced") or match.group("plain")
        for match in ENV_REFERENCE_RE.finditer(value)
        if os.environ.get(match.group("braced") or match.group("plain")) is None
    }
    if missing:
        names = ", ".join(sorted(missing))
        raise ValueError(
            f"provider {provider_name!r} {field_name} references unset "
            f"environment variable(s): {names}"
        )
    return os.path.expandvars(value)


def response_payload(provider: Provider, body: Any) -> dict[str, Any]:
    current = body
    for key in provider.response_path:
        if not isinstance(current, dict) or key not in current:
            dotted = ".".join(provider.response_path)
            raise ValueError(
                f"provider {provider.name!r} response is missing "
                f"configured response_path {dotted!r}"
            )
        current = current[key]
    if not isinstance(current, dict):
        raise ValueError(
            f"provider {provider.name!r} response payload must be an object"
        )
    return current


def load_providers(path: Path) -> list[Provider]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw = payload.get("providers")
    if not isinstance(raw, list) or not raw:
        raise ValueError("provider config must contain a non-empty providers list")

    providers: list[Provider] = []
    names: set[str] = set()
    for index, item in enumerate(raw, 1):
        if not isinstance(item, dict):
            raise ValueError(f"provider #{index} must be an object")
        name = str(item.get("name") or "").strip()
        url = str(item.get("url") or "").strip()
        if not name:
            raise ValueError(f"provider #{index} is missing name")
        if not url:
            raise ValueError(f"provider {name!r} is missing url")
        if name in names:
            raise ValueError(f"duplicate provider name: {name}")
        names.add(name)

        model_value = item.get("model")
        model = str(model_value).strip() if model_value is not None else None
        if model == "":
            model = None

        health_value = item.get("health_url")
        health_url = (
            str(health_value).strip()
            if health_value is not None
            else None
        )
        if health_url == "":
            health_url = None

        headers = item.get("headers") or {}
        request_fields = item.get("request_fields") or {}
        response_path_value = item.get("response_path") or []
        if not isinstance(headers, dict):
            raise ValueError(f"provider {name!r} headers must be an object")
        if not isinstance(request_fields, dict):
            raise ValueError(
                f"provider {name!r} request_fields must be an object"
            )
        if not isinstance(response_path_value, list) or not all(
            isinstance(part, str) and part
            for part in response_path_value
        ):
            raise ValueError(
                f"provider {name!r} response_path must be an array of strings"
            )

        url = expand_environment(
            url,
            provider_name=name,
            field_name="url",
        )
        if health_url is not None:
            health_url = expand_environment(
                health_url,
                provider_name=name,
                field_name="health_url",
            )
        expanded_headers = {
            str(key): expand_environment(
                str(value),
                provider_name=name,
                field_name=f"headers.{key}",
            )
            for key, value in headers.items()
        }

        providers.append(
            Provider(
                name=name,
                url=url,
                model=model,
                health_url=health_url,
                headers=expanded_headers,
                request_fields=dict(request_fields),
                response_path=tuple(response_path_value),
            )
        )
    return providers


def select_providers(
    providers: list[Provider],
    only: str | None,
) -> list[Provider]:
    if not only:
        return providers
    wanted = [value.strip() for value in only.split(",") if value.strip()]
    available = {provider.name: provider for provider in providers}
    missing = [name for name in wanted if name not in available]
    if missing:
        raise ValueError(
            "unknown provider(s): " + ", ".join(missing)
        )
    return [available[name] for name in wanted]


def build_payload(
    provider: Provider,
    state: Any,
    questions: dict[str, Any],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "state": state,
        "questions": questions,
    }
    if provider.model is not None:
        payload["model"] = provider.model

    reserved = {"state", "questions", "model"}
    overlap = reserved.intersection(provider.request_fields)
    if overlap:
        raise ValueError(
            f"provider {provider.name!r} request_fields override reserved "
            f"field(s): {', '.join(sorted(overlap))}"
        )
    payload.update(provider.request_fields)
    return payload


def parse_thresholds(spec: str) -> list[float]:
    result: list[float] = []
    for raw in spec.split(","):
        value = raw.strip()
        if not value:
            continue
        threshold = float(value)
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("thresholds must be between 0 and 1")
        result.append(threshold)
    if not result:
        raise ValueError("at least one threshold is required")
    return result


def wait_for_provider(
    client: httpx.Client,
    provider: Provider,
    timeout: float,
) -> None:
    if provider.health_url is None:
        return

    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            response = client.get(
                provider.health_url,
                headers=provider.headers,
                timeout=min(5.0, timeout),
            )
            response.raise_for_status()
            return
        except (httpx.HTTPError, OSError) as exc:
            last_error = exc
            time.sleep(0.25)
    raise RuntimeError(
        f"provider {provider.name!r} did not become ready within {timeout}s"
    ) from last_error


def synthetic_warmup_payload(provider: Provider) -> dict[str, Any]:
    return build_payload(
        provider,
        {"task": "Warm up the decision provider before measurement."},
        {
            "warmup": {
                "type": "choice",
                "instructions": "Classify this synthetic warm-up request.",
                "criteria": {
                    "warmup": "A benchmark warm-up request.",
                    "other": "Any non-warm-up request.",
                },
            }
        },
    )


def summarize_provider(
    details: list[dict[str, Any]],
    provider_name: str,
    thresholds: list[float],
) -> dict[str, Any]:
    rows = [row for row in details if row["model"] == provider_name]

    request_latency: dict[tuple[str, int], float] = {}
    request_usage: dict[tuple[str, int], dict[str, Any]] = {}
    for row in rows:
        request_key = (row["case_id"], row["pass"])
        request_latency[request_key] = row["latency_ms"]
        usage = row.get("usage")
        if isinstance(usage, dict):
            request_usage[request_key] = usage
    latencies = list(request_latency.values())

    usage_totals: dict[str, float | int] = {}
    for usage in request_usage.values():
        for key, value in usage.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            usage_totals[key] = usage_totals.get(key, 0) + value

    labeled = [row for row in rows if row["correct"] is not None]
    confidences = [
        float(row["confidence"])
        for row in labeled
        if isinstance(row.get("confidence"), (int, float))
    ]

    summary: dict[str, Any] = {
        "requests": len(latencies),
        "decisions": len(rows),
        "latency_ms": {
            key: round(value, 3)
            for key, value in {
                "mean": statistics.mean(latencies),
                "p50": percentile(latencies, 0.50),
                "p90": percentile(latencies, 0.90),
                "p95": percentile(latencies, 0.95),
                "p99": percentile(latencies, 0.99),
            }.items()
        },
        "requests_per_second": round(
            1000.0 / statistics.mean(latencies),
            3,
        ),
        "accuracy": (
            round(
                sum(bool(row["correct"]) for row in labeled) / len(labeled),
                6,
            )
            if labeled
            else None
        ),
        "mean_confidence": (
            round(statistics.mean(confidences), 6)
            if confidences
            else None
        ),
        "thresholds": {},
        "by_expected": {},
        "confusion_matrix": {},
        "usage": {
            "requests_with_usage": len(request_usage),
            "totals": usage_totals,
        },
    }

    for threshold in thresholds:
        eligible = [
            row
            for row in labeled
            if isinstance(row.get("confidence"), (int, float))
            and float(row["confidence"]) >= threshold
        ]
        summary["thresholds"][str(threshold)] = {
            "coverage": (
                round(len(eligible) / len(labeled), 6)
                if labeled
                else None
            ),
            "accuracy": (
                round(
                    sum(bool(row["correct"]) for row in eligible)
                    / len(eligible),
                    6,
                )
                if eligible
                else None
            ),
            "escalation_rate": (
                round(1.0 - len(eligible) / len(labeled), 6)
                if labeled
                else None
            ),
            "n": len(eligible),
        }

    expected_values = sorted(
        {str(row["expected"]) for row in labeled if row["expected"] is not None}
    )
    for expected in expected_values:
        subset = [
            row for row in labeled if str(row["expected"]) == expected
        ]
        subset_confidences = [
            float(row["confidence"])
            for row in subset
            if isinstance(row.get("confidence"), (int, float))
        ]
        summary["by_expected"][expected] = {
            "decisions": len(subset),
            "accuracy": round(
                sum(bool(row["correct"]) for row in subset) / len(subset),
                6,
            ),
            "mean_confidence": (
                round(statistics.mean(subset_confidences), 6)
                if subset_confidences
                else None
            ),
        }
        predicted: dict[str, int] = {}
        for row in subset:
            key = str(row["prediction"])
            predicted[key] = predicted.get(key, 0) + 1
        summary["confusion_matrix"][expected] = dict(sorted(predicted.items()))

    return summary


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Benchmark multiple Jev/System One compatible HTTP providers "
            "with the same labeled dataset"
        )
    )
    ap.add_argument(
        "--providers",
        type=Path,
        required=True,
        help="JSON provider configuration",
    )
    ap.add_argument(
        "--only",
        default=None,
        help="optional comma-separated provider names from the config",
    )
    ap.add_argument(
        "--dataset",
        type=Path,
        default=Path("datasets/smoke.jsonl"),
    )
    ap.add_argument("--iterations", type=int, default=1)
    ap.add_argument("--warmup", type=int, default=1)
    ap.add_argument("--timeout", type=float, default=300.0)
    ap.add_argument(
        "--thresholds",
        default="0.50,0.60,0.70,0.80,0.90",
    )
    ap.add_argument("--output", type=Path, default=Path("results"))
    args = ap.parse_args()

    try:
        providers = select_providers(
            load_providers(args.providers),
            args.only,
        )
        thresholds = parse_thresholds(args.thresholds)
    except ValueError as exc:
        ap.error(str(exc))

    if args.iterations < 1:
        ap.error("--iterations must be >= 1")
    if args.warmup < 0:
        ap.error("--warmup must be >= 0")

    rows = load_jsonl(args.dataset)
    args.output.mkdir(parents=True, exist_ok=True)
    run_id = time.strftime("%Y%m%d-%H%M%S")

    total_requests = len(providers) * len(rows) * args.iterations
    completed = 0
    details: list[dict[str, Any]] = []

    print(
        f"Provider benchmark: providers={len(providers)} cases={len(rows)} "
        f"passes={args.iterations} measured={total_requests}",
        flush=True,
    )

    with httpx.Client(timeout=args.timeout) as client:
        for provider_index, provider in enumerate(providers, 1):
            wait_for_provider(client, provider, args.timeout)
            print(
                f"[{provider_index}/{len(providers)}] "
                f"{provider.name}: ready",
                flush=True,
            )

            warm_payload = synthetic_warmup_payload(provider)
            for warmup_no in range(1, args.warmup + 1):
                started = time.perf_counter()
                response = client.post(
                    provider.url,
                    json=warm_payload,
                    headers=provider.headers,
                )
                elapsed = (time.perf_counter() - started) * 1000.0
                response.raise_for_status()
                print(
                    f"[{provider_index}/{len(providers)}] "
                    f"{provider.name}: warmup {warmup_no}/{args.warmup} "
                    f"{elapsed:.1f}ms",
                    flush=True,
                )

            provider_total = len(rows) * args.iterations
            provider_completed = 0
            provider_started = time.perf_counter()

            for pass_no in range(1, args.iterations + 1):
                for row in rows:
                    payload = build_payload(
                        provider,
                        row["state"],
                        row["questions"],
                    )
                    cpu_before = psutil.cpu_percent(interval=None)
                    memory_before = psutil.virtual_memory().used
                    started = time.perf_counter()
                    response = client.post(
                        provider.url,
                        json=payload,
                        headers=provider.headers,
                    )
                    elapsed_ms = (
                        time.perf_counter() - started
                    ) * 1000.0
                    cpu_after = psutil.cpu_percent(interval=None)
                    memory_after = psutil.virtual_memory().used
                    response.raise_for_status()
                    body = response.json()
                    payload_body = response_payload(provider, body)

                    answers = payload_body.get("answers")
                    if not isinstance(answers, dict):
                        raise ValueError(
                            f"provider {provider.name!r} returned no answers object"
                        )

                    for question_name, question in row["questions"].items():
                        answer = answers.get(question_name)
                        if not isinstance(answer, dict):
                            raise ValueError(
                                f"provider {provider.name!r} returned no answer "
                                f"for question {question_name!r}"
                            )
                        qtype = question["type"]
                        prediction = answer_value(answer, qtype)
                        expected = row.get("expected", {}).get(question_name)
                        details.append(
                            {
                                "model": provider.name,
                                "provider": provider.name,
                                "provider_model": provider.model,
                                "provider_url": provider.url,
                                "case_id": row["id"],
                                "pass": pass_no,
                                "question": question_name,
                                "type": qtype,
                                "prediction": prediction,
                                "expected": expected,
                                "correct": correct(
                                    prediction,
                                    expected,
                                    qtype,
                                ),
                                "confidence": answer_confidence(
                                    answer,
                                    qtype,
                                ),
                                "latency_ms": elapsed_ms,
                                "cpu_percent_before": cpu_before,
                                "cpu_percent_after": cpu_after,
                                "memory_delta_mb": (
                                    memory_after - memory_before
                                )
                                / 1024
                                / 1024,
                                "answer": answer,
                                "usage": payload_body.get("usage"),
                                "metadata": row.get("metadata"),
                            }
                        )

                    completed += 1
                    provider_completed += 1
                    elapsed_provider = (
                        time.perf_counter() - provider_started
                    )
                    avg_seconds = elapsed_provider / provider_completed
                    remaining = provider_total - provider_completed
                    eta = max(0, round(avg_seconds * remaining))
                    overall_pct = completed / total_requests * 100.0
                    provider_pct = (
                        provider_completed / provider_total * 100.0
                    )
                    progress = (
                        f"[{completed}/{total_requests}] "
                        f"{overall_pct:6.2f}% provider={provider.name} "
                        f"[{provider_completed}/{provider_total} "
                        f"{provider_pct:5.1f}%] "
                        f"pass={pass_no}/{args.iterations} "
                        f"case={row['id']} "
                        f"latency={elapsed_ms:.1f}ms ETA={eta}s"
                    )
                    if sys.stderr.isatty():
                        print(
                            f"\r\x1b[2K{progress}",
                            end="",
                            file=sys.stderr,
                            flush=True,
                        )
                    else:
                        print(progress, file=sys.stderr, flush=True)

            if sys.stderr.isatty():
                print(file=sys.stderr, flush=True)
            print(
                f"[{provider_index}/{len(providers)}] "
                f"{provider.name}: complete",
                flush=True,
            )

    detail_path = args.output / f"{run_id}-provider-details.jsonl"
    with detail_path.open("w", encoding="utf-8") as handle:
        for row in details:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary: dict[str, Any] = {
        "run_id": run_id,
        "methodology": {
            "dataset": str(args.dataset),
            "provider_config": str(args.providers),
            "iterations": args.iterations,
            "warmup": args.warmup,
            "thresholds": thresholds,
            "comparison_status": "development-only",
            "warning": (
                "Provider confidence scales are not assumed to be calibrated "
                "or mutually comparable. Freeze each selected provider policy "
                "before evaluating it on a new fresh holdout."
            ),
        },
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "cpu_count_logical": psutil.cpu_count(),
            "cpu_count_physical": psutil.cpu_count(logical=False),
            "memory_gib": round(
                psutil.virtual_memory().total / 1024**3,
                2,
            ),
        },
        "providers": {},
    }

    for provider in providers:
        provider_summary = summarize_provider(
            details,
            provider.name,
            thresholds,
        )
        provider_summary["endpoint"] = provider.url
        provider_summary["provider_model"] = provider.model
        summary["providers"][provider.name] = provider_summary

    summary_path = args.output / f"{run_id}-provider-summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(
        f"\nDetails: {detail_path}\nSummary: {summary_path}",
        flush=True,
    )


if __name__ == "__main__":
    main()
