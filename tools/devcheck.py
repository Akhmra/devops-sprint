#!/usr/bin/env python3
"""
devcheck.py — lightweight system resource checker
"""

import argparse
import json
import shutil
import sys


def cpu_cores() -> int:
    """Считает строки 'processor' в /proc/cpuinfo."""
    count = 0
    with open("/proc/cpuinfo", "r") as fh:
        for line in fh:
            if line.startswith("processor"):
                count += 1
    return count if count > 0 else 1


def cpu_load() -> dict:
    """load1 и load1_pct = load1 / cores * 100."""
    with open("/proc/loadavg", "r") as fh:
        load1 = float(fh.read().split()[0])

    cores     = cpu_cores()
    load1_pct = round(load1 / cores * 100, 1)

    return {
        "load1":     round(load1, 1),
        "load1_pct": load1_pct,
    }


def mem_used_pct() -> float:
    """(MemTotal - MemAvailable) / MemTotal * 100."""
    data = {}
    with open("/proc/meminfo", "r") as fh:
        for line in fh:
            key, _, value = line.partition(":")
            key = key.strip()
            if key in ("MemTotal", "MemAvailable"):
                data[key] = int(value.split()[0])

    total    = data["MemTotal"]
    avail    = data["MemAvailable"]
    return round((total - avail) / total * 100, 1)


def disk_used_pct(path: str = "/") -> float:
    """used / total * 100 через shutil.disk_usage."""
    usage = shutil.disk_usage(path)
    return round(usage.used / usage.total * 100, 1)


def collect(path: str = "/") -> dict:
    """Собирает все метрики в словарь."""
    load_info = cpu_load()

    return {
        "cpu_load":      load_info["load1"],
        "cpu_load_pct":  load_info["load1_pct"],
        "cpu_cores":     cpu_cores(),
        "mem_used_pct":  mem_used_pct(),
        "disk_used_pct": disk_used_pct(path),
    }

    def pct(used, total):
        return f"{used / total * 100:.1f}"        # '38.5' — строка с одним знаком

    def is_over(value, limit):
        return value > limit                       # True/False


def main() -> int:
    parser = argparse.ArgumentParser(description="Check CPU / memory / disk usage")
    parser.add_argument("--json",      action="store_true", help="вывод в JSON")
    parser.add_argument("--threshold", type=float, default=90.0, metavar="PCT",
                        help="порог предупреждения в %% (по умолчанию: 90)")
    parser.add_argument("--path",      default="/", metavar="PATH",
                        help="путь для проверки диска (по умолчанию: /)")
    args = parser.parse_args()

    m = collect(args.path)

    # ── предупреждения ───────────────────────────────────────────────────────
    warnings: list[str] = []

    if m["cpu_load_pct"] > args.threshold:
        warnings.append(f"загрузка CPU {m['cpu_load_pct']}% > {args.threshold}%")

    if m["mem_used_pct"] > args.threshold:
        warnings.append(f"память {m['mem_used_pct']}% > {args.threshold}%")

    if m["disk_used_pct"] > args.threshold:
        warnings.append(f"диск {m['disk_used_pct']}% > {args.threshold}%")

    ok = len(warnings) == 0

    # ── вывод ────────────────────────────────────────────────────────────────
    if args.json:
        result = {
            "cpu_load":      m["cpu_load"],
            "cpu_load_pct":  m["cpu_load_pct"],
            "cpu_cores":     m["cpu_cores"],
            "mem_used_pct":  m["mem_used_pct"],
            "disk_used_pct": m["disk_used_pct"],
            "ok":            ok,
            "warnings":      warnings,
        }
        print(json.dumps(result, ensure_ascii=False))

    else:
        print(f"CPU:  load1={m['cpu_load']} ({m['cpu_cores']} ядер, {m['cpu_load_pct']}%)")
        print(f"RAM:  занято {m['mem_used_pct']}%")
        print(f"Диск {args.path}: занято {m['disk_used_pct']}%")

        if warnings:
            for w in warnings:
                print(f"ВНИМАНИЕ: {w}")
            print("статус: ПРЕВЫШЕНИЕ ПОРГА")   # сохраняем опечатку из задания
        else:
            print("статус: OK")

        print(f"код выхода: {0 if ok else 1}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
