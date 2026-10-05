#!/usr/bin/env python3
"""httpcheck — проверка HTTP-доступности URL с таймаутом и повторами.

    python3 tools/httpcheck.py https://localhost:8443/health
    python3 tools/httpcheck.py --retries 3 --timeout 2 https://example.org
    python3 tools/httpcheck.py --insecure https://localhost:8443/report --json

Код возврата: 0 — все URL ответили 2xx/3xx, 1 — хотя бы один не ответил.
"""
import argparse
import json
import ssl
import sys
import time
import urllib.error
import urllib.request


def timed(url, timeout=5, insecure=False):
    """Возвращает (код, миллисекунды). Ошибку отдаём как (None, -1)."""
    ctx = ssl.create_default_context()
    if insecure:                       # самоподписанный сертификат — только для лаборатории
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    start = time.time()
    try:
        with urllib.request.urlopen(url, timeout=timeout, context=ctx) as r:
            r.read(1)                  # читаем байт, чтобы получить реальное время ответа
            return r.status, int((time.time() - start) * 1000)
    except urllib.error.HTTPError as err:          # сервер ответил, но ошибкой (404/500)
        return err.code, int((time.time() - start) * 1000)
    except Exception:
        return None, -1


def check(url, retries=3, timeout=5, insecure=False, pause=1.0):
    """Пробует несколько раз, возвращает (код, мс, попытки)."""
    last = (None, -1)
    for attempt in range(1, retries + 1):
        code, ms = timed(url, timeout=timeout, insecure=insecure)
        if code is not None and code < 400:
            return code, ms, attempt
        last = (code, ms)
        if attempt < retries:
            time.sleep(pause)
    return last[0], last[1], retries


def main(argv=None):
    p = argparse.ArgumentParser(description="Проверка доступности URL")
    p.add_argument("urls", nargs="+", help="один или несколько URL")
    p.add_argument("--retries", type=int, default=3, help="сколько попыток на URL (по умолчанию 3)")
    p.add_argument("--timeout", type=float, default=5.0, help="таймаут в секундах (по умолчанию 5)")
    p.add_argument("--insecure", action="store_true", help="не проверять сертификат (самоподписанный)")
    p.add_argument("--json", action="store_true", help="вывод в JSON")
    args = p.parse_args(argv)

    results, failed = [], 0
    for url in args.urls:
        code, ms, attempts = check(url, args.retries, args.timeout, args.insecure)
        ok = code is not None and code < 400
        failed += 0 if ok else 1
        results.append({"url": url, "code": code, "ms": ms, "attempts": attempts, "ok": ok})
        if not args.json:
            print("%-45s код=%s время=%s мс попыток=%s %s" % (
                url, code if code is not None else "—", ms if ms >= 0 else "—",
                attempts, "ok" if ok else "FAIL"))

    if args.json:
        print(json.dumps({"results": results, "failed": failed}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
