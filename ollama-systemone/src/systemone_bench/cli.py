from __future__ import annotations

import argparse
import json
import math
import platform
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

import httpx
import psutil


def percentile(values: list[float], p: float) -> float:
    if not values:
        return math.nan
    xs = sorted(values)
    k = (len(xs) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return xs[lo]
    return xs[lo] * (hi - k) + xs[hi] * (k - lo)


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if line:
                row = json.loads(line)
                row.setdefault("id", f"line-{line_no}")
                rows.append(row)
    if not rows:
        raise ValueError(f"dataset is empty: {path}")
    return rows


def answer_value(answer: dict, qtype: str):
    if qtype == "choice":
        return answer.get("choice")
    if qtype == "noul":
        v = answer.get("noul")
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            return v >= 0.5
        return v
    if qtype == "score":
        return answer.get("score")
    return None


def answer_confidence(answer: dict, qtype: str) -> float | None:
    c = answer.get("confidence")
    if isinstance(c, (int, float)):
        return float(c)
    if qtype == "noul" and isinstance(answer.get("noul"), (int, float)):
        p = float(answer["noul"])
        return max(p, 1.0 - p)
    return None


def correct(pred, expected, qtype: str) -> bool | None:
    if expected is None:
        return None
    if qtype == "score" and isinstance(expected, (int, float)) and isinstance(pred, (int, float)):
        return round(float(pred)) == round(float(expected))
    return pred == expected


def main() -> None:
    ap = argparse.ArgumentParser(description="Benchmark Ollama /v1/systemone decision models")
    ap.add_argument("--models", default="clef-flash", help="comma-separated model names")
    ap.add_argument("--dataset", type=Path, default=Path("datasets/smoke.jsonl"))
    ap.add_argument("--base-url", default="http://localhost:11434")
    ap.add_argument("--iterations", type=int, default=1, help="dataset passes")
    ap.add_argument("--warmup", type=int, default=2)
    ap.add_argument("--timeout", type=float, default=300)
    ap.add_argument("--keep-alive", default="10m")
    ap.add_argument("--thresholds", default="0.90,0.95,0.98,0.99")
    ap.add_argument("--output", type=Path, default=Path("results"))
    args = ap.parse_args()

    rows = load_jsonl(args.dataset)
    models = [x.strip() for x in args.models.split(",") if x.strip()]
    thresholds = [float(x) for x in args.thresholds.split(",")]
    args.output.mkdir(parents=True, exist_ok=True)
    run_id = time.strftime("%Y%m%d-%H%M%S")
    details: list[dict] = []
    total_requests = len(models) * len(rows) * args.iterations
    completed_requests = 0
    print(
        f"Benchmark: {len(models)} model(s), {len(rows)} case(s), "
        f"{args.iterations} pass(es), {total_requests} measured request(s)",
        flush=True,
    )

    with httpx.Client(timeout=args.timeout) as client:
        for model_index, model in enumerate(models, 1):
            warm = rows[0]
            warm_payload = {"model": model, "state": warm["state"], "questions": warm["questions"], "keep_alive": args.keep_alive}
            if args.warmup:
                print(
                    f"[{model_index}/{len(models)}] {model}: warming up ({args.warmup} request(s))...",
                    flush=True,
                )
            for warmup_no in range(1, args.warmup + 1):
                warmup_started = time.perf_counter()
                print(
                    f"[{model_index}/{len(models)}] {model}: warmup {warmup_no}/{args.warmup} started...",
                    flush=True,
                )
                r = client.post(f"{args.base_url.rstrip('/')}/v1/systemone", json=warm_payload)
                warmup_elapsed = time.perf_counter() - warmup_started
                r.raise_for_status()
                print(
                    f"[{model_index}/{len(models)}] {model}: warmup {warmup_no}/{args.warmup} "
                    f"complete ({warmup_elapsed:.1f}s)",
                    flush=True,
                )

            model_total_requests = len(rows) * args.iterations
            model_completed_requests = 0
            model_started = time.perf_counter()
            print(f"[{model_index}/{len(models)}] {model}: benchmark started", flush=True)
            for pass_no in range(args.iterations):
                for row in rows:
                    payload = {"model": model, "state": row["state"], "questions": row["questions"], "keep_alive": args.keep_alive}
                    cpu_before = psutil.cpu_percent(interval=None)
                    mem_before = psutil.virtual_memory().used
                    t0 = time.perf_counter()
                    r = client.post(f"{args.base_url.rstrip('/')}/v1/systemone", json=payload)
                    elapsed_ms = (time.perf_counter() - t0) * 1000
                    cpu_after = psutil.cpu_percent(interval=None)
                    mem_after = psutil.virtual_memory().used
                    r.raise_for_status()
                    body = r.json()
                    for name, question in row["questions"].items():
                        ans = body.get("answers", {}).get(name, {})
                        qtype = question["type"]
                        pred = answer_value(ans, qtype)
                        expected = row.get("expected", {}).get(name)
                        details.append({
                            "model": model, "case_id": row["id"], "pass": pass_no + 1,
                            "question": name, "type": qtype, "prediction": pred,
                            "expected": expected, "correct": correct(pred, expected, qtype),
                            "confidence": answer_confidence(ans, qtype),
                            "latency_ms": elapsed_ms, "cpu_percent_before": cpu_before,
                            "cpu_percent_after": cpu_after, "memory_delta_mb": (mem_after - mem_before) / 1024 / 1024,
                            "answer": ans,
                        })
                    completed_requests += 1
                    elapsed_run = time.perf_counter() - run_started
                    avg_seconds = elapsed_run / completed_requests
                    remaining = total_requests - completed_requests
                    eta_seconds = max(0, round(avg_seconds * remaining))
                    percent = completed_requests / total_requests * 100 if total_requests else 100.0
                    print(
                        f"\\r[{completed_requests:>{len(str(total_requests))}}/{total_requests}] "
                        f"{percent:6.2f}% model={model} pass={pass_no + 1}/{args.iterations} "
                        f"case={row['id']} latency={elapsed_ms:.1f}ms ETA={eta_seconds}s",
                        end="", file=sys.stderr, flush=True,
                    )
            if total_requests:
                print(file=sys.stderr, flush=True)
            print(f"[{model_index}/{len(models)}] {model}: complete", flush=True)

    detail_path = args.output / f"{run_id}-details.jsonl"
    with detail_path.open("w", encoding="utf-8") as f:
        for d in details:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    summary = {"run_id": run_id, "environment": {
        "platform": platform.platform(), "python": platform.python_version(),
        "cpu_count_logical": psutil.cpu_count(), "cpu_count_physical": psutil.cpu_count(logical=False),
        "memory_gib": round(psutil.virtual_memory().total / 1024**3, 2),
    }, "models": {}}

    for model in models:
        ds = [d for d in details if d["model"] == model]
        # One request may contain multiple questions; de-duplicate latency by case/pass.
        req_latency = {}
        for d in ds:
            req_latency[(d["case_id"], d["pass"])] = d["latency_ms"]
        lats = list(req_latency.values())
        labeled = [d for d in ds if d["correct"] is not None]
        m = {
            "requests": len(lats), "decisions": len(ds),
            "latency_ms": {k: round(v, 3) for k, v in {
                "mean": statistics.mean(lats), "p50": percentile(lats, .50),
                "p90": percentile(lats, .90), "p95": percentile(lats, .95), "p99": percentile(lats, .99)
            }.items()},
            "requests_per_second": round(1000 / statistics.mean(lats), 3),
            "accuracy": round(sum(d["correct"] for d in labeled) / len(labeled), 6) if labeled else None,
            "thresholds": {},
            "cases": {},
        }
        case_ids = sorted({d["case_id"] for d in ds})
        for case_id in case_ids:
            case_ds = [d for d in ds if d["case_id"] == case_id]
            case_req_latency = {}
            for d in case_ds:
                case_req_latency[d["pass"]] = d["latency_ms"]
            case_lats = list(case_req_latency.values())
            case_labeled = [d for d in case_ds if d["correct"] is not None]
            m["cases"][case_id] = {
                "requests": len(case_lats),
                "decisions": len(case_ds),
                "latency_ms": {
                    "mean": round(statistics.mean(case_lats), 3),
                    "p50": round(percentile(case_lats, .50), 3),
                    "p95": round(percentile(case_lats, .95), 3),
                },
                "accuracy": round(sum(d["correct"] for d in case_labeled) / len(case_labeled), 6) if case_labeled else None,
                "mean_confidence": round(statistics.mean(d["confidence"] for d in case_ds if d["confidence"] is not None), 6) if any(d["confidence"] is not None for d in case_ds) else None,
            }
        for t in thresholds:
            eligible = [d for d in labeled if d["confidence"] is not None and d["confidence"] >= t]
            m["thresholds"][str(t)] = {
                "coverage": round(len(eligible) / len(labeled), 6) if labeled else None,
                "accuracy": round(sum(d["correct"] for d in eligible) / len(eligible), 6) if eligible else None,
                "escalation_rate": round(1 - len(eligible) / len(labeled), 6) if labeled else None,
                "n": len(eligible),
            }
        summary["models"][model] = m

    summary_path = args.output / f"{run_id}-summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nDetails: {detail_path}\nSummary: {summary_path}")


if __name__ == "__main__":
    main()
