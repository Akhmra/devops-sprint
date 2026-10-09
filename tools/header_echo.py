#!/usr/bin/env python3
"""header_echo — микросервис, который возвращает полученные заголовки в JSON.

Нужен, чтобы увидеть, какие заголовки добавляет nginx-прокси (X-Real-IP, X-Forwarded-For).
    python3 tools/header_echo.py 8090
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

APP_VERSION = os.environ.get("APP_VERSION", "v1")   # версия приходит из Deployment (env)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        headers = {k: v for k, v in self.headers.items()}
        body = json.dumps({"version": APP_VERSION, "path": self.path,
                           "client": self.client_address[0],
                           "headers": headers}, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8091
    print(f"header_echo слушает {port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
