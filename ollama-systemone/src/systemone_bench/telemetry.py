from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any

import psutil


def _finite(value: float | int | None) -> float | None:
    if value is None:
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def cpu_frequency_summary() -> dict[str, float | None]:
    try:
        freqs = psutil.cpu_freq(percpu=True)
    except (AttributeError, NotImplementedError, OSError):
        freqs = None

    if not freqs:
        try:
            single = psutil.cpu_freq()
        except (AttributeError, NotImplementedError, OSError):
            single = None
        if single is None:
            return {
                "current_mhz_mean": None,
                "current_mhz_min": None,
                "current_mhz_max": None,
            }
        values = [_finite(single.current)]
    else:
        values = [_finite(freq.current) for freq in freqs]

    usable = [value for value in values if value is not None]
    if not usable:
        return {
            "current_mhz_mean": None,
            "current_mhz_min": None,
            "current_mhz_max": None,
        }
    return {
        "current_mhz_mean": sum(usable) / len(usable),
        "current_mhz_min": min(usable),
        "current_mhz_max": max(usable),
    }


def load_average() -> dict[str, float | None]:
    try:
        one, five, fifteen = os.getloadavg()
    except (AttributeError, OSError):
        return {"load1": None, "load5": None, "load15": None}
    return {
        "load1": _finite(one),
        "load5": _finite(five),
        "load15": _finite(fifteen),
    }


def temperature_summary() -> dict[str, Any]:
    try:
        sensors = psutil.sensors_temperatures(fahrenheit=False)
    except (AttributeError, NotImplementedError, OSError):
        sensors = {}

    readings: list[dict[str, Any]] = []
    for chip, entries in sorted((sensors or {}).items()):
        for entry in entries:
            current = _finite(getattr(entry, "current", None))
            if current is None:
                continue
            readings.append(
                {
                    "chip": chip,
                    "label": getattr(entry, "label", "") or "",
                    "current_c": current,
                }
            )

    return {
        "max_c": max((r["current_c"] for r in readings), default=None),
        "readings": readings,
    }


def _ollama_name(candidate: str) -> bool:
    value = candidate.lower()
    return value == "ollama" or value.startswith("ollama_")


def _matches_ollama(process: psutil.Process) -> bool:
    try:
        name = process.name() or ""
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        name = ""
    if _ollama_name(name):
        return True

    try:
        exe_name = Path(process.exe() or "").name
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        exe_name = ""
    if _ollama_name(exe_name):
        return True

    try:
        cmdline = process.cmdline()
        argv0 = Path(cmdline[0]).name if cmdline else ""
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        argv0 = ""

    return _ollama_name(argv0)


def ollama_process_snapshot() -> dict[str, Any]:
    processes: list[dict[str, Any]] = []

    for process in psutil.process_iter():
        if not _matches_ollama(process):
            continue
        try:
            cpu_times = process.cpu_times()
            memory = process.memory_info()
            processes.append(
                {
                    "pid": process.pid,
                    "name": process.name(),
                    "create_time": process.create_time(),
                    "rss_bytes": int(memory.rss),
                    "cpu_time_seconds": float(
                        cpu_times.user + cpu_times.system
                    ),
                }
            )
        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
        ):
            continue

    processes.sort(key=lambda item: item["pid"])
    return {
        "processes": processes,
        "process_count": len(processes),
        "rss_bytes_total": sum(
            process["rss_bytes"] for process in processes
        ),
        "cpu_time_seconds_total": sum(
            process["cpu_time_seconds"] for process in processes
        ),
        "pids": [process["pid"] for process in processes],
        "create_times": [
            {
                "pid": process["pid"],
                "create_time": process["create_time"],
            }
            for process in processes
        ],
    }


def capture_request_telemetry() -> dict[str, Any]:
    return {
        "cpu_frequency": cpu_frequency_summary(),
        "load_average": load_average(),
        "temperature": temperature_summary(),
        "ollama": ollama_process_snapshot(),
        "system_memory": {
            "available_bytes": int(psutil.virtual_memory().available),
        },
    }


def derive_request_telemetry(
    before: dict[str, Any],
    after: dict[str, Any],
    elapsed_ms: float,
) -> dict[str, Any]:
    before_ollama = before.get("ollama") or {}
    after_ollama = after.get("ollama") or {}

    cpu_before = _finite(before_ollama.get("cpu_time_seconds_total"))
    cpu_after = _finite(after_ollama.get("cpu_time_seconds_total"))
    elapsed_seconds = elapsed_ms / 1000.0

    process_cpu_percent = None
    if (
        cpu_before is not None
        and cpu_after is not None
        and cpu_after >= cpu_before
        and elapsed_seconds > 0
    ):
        process_cpu_percent = (
            (cpu_after - cpu_before) / elapsed_seconds * 100.0
        )

    rss_before = before_ollama.get("rss_bytes_total")
    rss_after = after_ollama.get("rss_bytes_total")
    rss_delta = None
    if isinstance(rss_before, int) and isinstance(rss_after, int):
        rss_delta = rss_after - rss_before

    before_ids = {
        (item.get("pid"), item.get("create_time"))
        for item in before_ollama.get("create_times", [])
    }
    after_ids = {
        (item.get("pid"), item.get("create_time"))
        for item in after_ollama.get("create_times", [])
    }

    return {
        "before": before,
        "after": after,
        "derived": {
            "ollama_cpu_percent_over_request": process_cpu_percent,
            "ollama_rss_delta_bytes": rss_delta,
            "ollama_process_identity_changed": before_ids != after_ids,
        },
    }
