#!/usr/bin/env python3
"""Анализатор логов syslog."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timedelta

# --- Регулярные выражения ---
SYSLOG_RE = re.compile(r"^(\w{3})\s+(\d{1,2})\s+(\d{2}):(\d{2}):(\d{2})\s+\S+\s+(\w+)(?:\[\d+\])?:\s*(.*)$")


MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4,
    "May": 5, "Jun": 6, "Jul": 7, "Aug": 8,
    "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

DIGITS_RE = re.compile(r"\d+")
ERROR_RE = re.compile(r"\berror\b|\bfail(?:ed|ure)?\b|\bpanic\b", re.IGNORECASE)


def parse_line(line: str, year: int) -> tuple[datetime, str, str] | None:
    """Разбирает строку syslog. Возвращает (время, процесс, сообщение) или None."""
    m = SYSLOG_RE.match(line.strip())
    if not m:
        return None
    mon, day, hh, mm, ss, proc, msg = m.groups()
    month = MONTHS.get(mon)
    if month is None:
        return None
    try:
        dt = datetime(year, month, int(day), int(hh), int(mm), int(ss))
    except ValueError:
        return None
    return dt, proc, msg


def normalize(msg: str) -> str:
    """Заменяет числа на N и схлопывает лишние пробелы."""
    msg = DIGITS_RE.sub("N", msg)
    msg = re.sub(r"\s+", " ", msg).strip()
    return msg


def scan(path: str, hours: int) -> tuple[Counter, Counter, list[str], bool, int, int]:
    """Сканирует лог-файл. Возвращает (счётчик сообщений, счётчик процессов, ошибки, флаг_проблем, всего_строк, строк_в_периоде)."""
    msg_counter: Counter = Counter()
    proc_counter: Counter = Counter()
    errors: list[str] = []
    has_problems = False
    total_lines = 0
    lines_in_period = 0
    year = datetime.now().year
    cutoff = datetime.now() - timedelta(hours=hours)

    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                total_lines += 1
                parsed = parse_line(line, year)
                if parsed is None:
                    has_problems = True
                    continue
                dt, proc, msg = parsed
                if dt < cutoff:
                    continue
                lines_in_period += 1
                proc_counter[proc] += 1
                norm = normalize(msg)
                msg_counter[norm] += 1
                if ERROR_RE.search(msg):
                    errors.append(line.strip())
    except FileNotFoundError:
        print(f"Файл не найден: {path}", file=sys.stderr)
        sys.exit(2)

    return msg_counter, proc_counter, errors, has_problems, total_lines, lines_in_period


def human_size(size: int) -> str:
    """Превращает байты в человекочитаемый размер."""
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if size < 1024:
            return f"{size:.0f} {unit}" if unit == "Б" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} ТБ"


def truncate(msg: str, width: int = 70) -> str:
    """Обрезает сообщение до width символов, добавляя '...' в конце."""
    if len(msg) <= width:
        return msg
    return msg[:width] + "..."


def main() -> None:
    parser = argparse.ArgumentParser(description="Анализатор логов syslog.")
    parser.add_argument("file", help="Путь к лог-файлу")
    parser.add_argument("--top", type=int, default=10, help="Топ-N сообщений (по умолчанию 10)")
    parser.add_argument("--hours", type=int, default=24, help="Анализировать последние N часов (по умолчанию 24)")
    parser.add_argument("--errors", action="store_true", help="Вывести строки с ошибками")
    parser.add_argument("--json", action="store_true", help="Вывод в JSON")
    args = parser.parse_args()

    msg_counter, proc_counter, errors, has_problems, total_lines, lines_in_period = scan(args.file, args.hours)

    # Размер файла
    file_size = os.path.getsize(args.file)

    # Время начала периода
    period_start = datetime.now() - timedelta(hours=args.hours)
    period_str = period_start.strftime("%d.%m %H:%M")

    if args.json:
        output = {
            "file": args.file,
            "size_bytes": file_size,
            "total_lines": total_lines,
            "period_hours": args.hours,
            "period_start": period_str,
            "lines_in_period": lines_in_period,
            "top_messages": [{"msg": msg, "count": count} for msg, count in msg_counter.most_common(args.top)],
            "top_processes": [{"proc": proc, "count": count} for proc, count in proc_counter.most_common(args.top)],
            "errors": errors if args.errors else [],
            "has_problems": has_problems,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        # --- Заголовок ---
        print(f"Файл: {args.file} ({human_size(file_size)}, строк: {total_lines})")
        print(f"Период: последние {args.hours} ч (с {period_str}); строк в периоде: {lines_in_period}")
        print()

        # --- Топ сообщений ---
        print(f"ТОП-{args.top} СООБЩЕНИЙ ПО ЧАСТОТЕ")
        for i, (msg, count) in enumerate(msg_counter.most_common(args.top), 1):
            print(f"  {i}.  {count}×  {truncate(msg)}")
        print()

        # --- Топ процессов ---
        print(f"ТОП-{args.top} ПРОЦЕССОВ ПО ЧАСТОТЕ")
        for i, (proc, count) in enumerate(proc_counter.most_common(args.top), 1):
            print(f"  {i}.  {count}×  {proc}")
        print()

        # --- Ошибки ---
        if args.errors and errors:
            print(f"ОШИБКИ ({len(errors)})")
            for e in errors:
                print(f"  {truncate(e, 100)}")
            print()

        if has_problems:
            print("⚠  Есть нераспознанные строки.")

    sys.exit(1 if (has_problems or errors) else 0)


if __name__ == "__main__":
    main()
