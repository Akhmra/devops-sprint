import os
import time
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# --- Конфигурация из переменных окружения ---
PORT = int(os.getenv('APP_PORT', '8080'))
VERSION = os.getenv('APP_VERSION', '1.0.0')
ENV_NAME = os.getenv('APP_ENV', 'development')
SECRET = os.getenv('APP_SECRET', '')
SECRET_LOADED = 1 if SECRET else 0

# Фиксируем время старта для метрики uptime
START_TIME = time.time()

class AppHandler(BaseHTTPRequestHandler):
    # 1. Живой счётчик запросов (атрибут класса)
    requests_total = 0

    def _send_response(self, status_code, data, content_type='application/json'):
        """Вспомогательный метод с Content-Length и корректной кодировкой."""
        if content_type.startswith('text/plain'):
            body = data.encode('utf-8')
        else:
            body = json.dumps(data).encode('utf-8')
        
        self.send_response(status_code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        # 3. Отсекаем query-строку
        path = self.path.split('?', 1)[0]
        
        # Инкремент счётчика при каждом запросе
        AppHandler.requests_total += 1

        if path == '/health':
            self._send_response(200, {"status": "ok"})

        elif path == '/metrics':
            uptime_seconds = int(time.time() - START_TIME)
            # 1. Используем живой счётчик в метриках
            # Опционально: HELP/TYPE для Prometheus
            metrics_data = (
                "# HELP app_requests_total Total number of requests to the application.\n"
                "# TYPE app_requests_total counter\n"
                f"app_requests_total {AppHandler.requests_total}\n"
                "# HELP app_info Application static information.\n"
                "# TYPE app_info gauge\n"
                f'app_info{{version="{VERSION}",env="{ENV_NAME}"}} 1\n'
                "# HELP app_uptime_seconds Seconds since the application started.\n"
                "# TYPE app_uptime_seconds gauge\n"
                f"app_uptime_seconds {uptime_seconds}\n"
                "# HELP app_secret_loaded Indicates if APP_SECRET was loaded from environment.\n"
                "# TYPE app_secret_loaded gauge\n"
                f"app_secret_loaded {SECRET_LOADED}\n"
            )
            self._send_response(200, metrics_data, 'text/plain; version=0.0.4; charset=utf-8')

        elif path == '/':
            info_data = {
                "version": VERSION,
                "env": ENV_NAME,
                "port": PORT
            }
            self._send_response(200, info_data)

        else:
            self._send_response(404, {"error": "Not Found"})

    def log_message(self, format, *args):
        return

def run():
    server_address = ('0.0.0.0', PORT)
    # 4. Многопоточный сервер
    httpd = ThreadingHTTPServer(server_address, AppHandler)
    print(f"Starting server on 0.0.0.0:{PORT}")
    print(f"Environment: {ENV_NAME}, Version: {VERSION}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print("Server stopped.")

if __name__ == '__main__':
    run()
