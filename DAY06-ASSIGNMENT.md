# День 6 — подробное задание (11.10.2026): HTTP-сервис на stdlib + конфиг/секреты в k8s

Общая раскладка: **150 мин ядро** = Python 60 + инфраструктура 60 + конспект 30. Блок расширения 60 мин —
сегодня добровольный (гейт не пройден), но по теме совпадает с задачей дня.

---
# ЧАСТЬ 1. PYTHON (60 мин)

## 1.1 Теория (15 мин)

📚 https://docs.python.org/3/library/http.server.html

1. **`http.server`** — сервер в стандартной библиотеке: `HTTPServer` (по одному запросу за раз) и
   `ThreadingHTTPServer` (поток на запрос). Он даёт готовый HTTP-парсер, а логику маршрутов пишем сами.
2. **`BaseHTTPRequestHandler`** — класс, который вызывается на каждый запрос. Свой метод `do_GET(self)`
   отвечает на GET. Путь запроса — `self.path` (включая query-строку: `/metrics?x=1`).
3. **Роутинг руками** — разводим ветки по `self.path`: `if self.path == "/health": ... elif ... else: 404`.
   Никаких фреймворков: смысл дня — увидеть, что фреймворк делает за нас.
4. **Ответ** — три шага: `self.send_response(200)`, `self.send_header("Content-Type", "application/json")`,
   `self.end_headers()`, затем `self.wfile.write(body.encode("utf-8"))`. Заголовок `Content-Length` лучше
   ставить явно — тогда curl и браузер не подвисают.
5. **`self.server.metrics`** — счётчики удобно держать на объекте сервера, а не в глобальной переменной:
   так их видит каждый обработчик и видно, что метрики живут дольше одного запроса.
6. **Конфиг через окружение** — `os.environ.get("APP_PORT", "8080")`: один и тот же код, разные среды.
   Дефолты обязательны, иначе сервис упадёт там, где переменной нет.
7. **Формат метрик Prometheus** — построчный текст: `имя значение` и `имя{метка="значение"} значение`,
   плюс строки `# HELP` и `# TYPE`. Content-Type: `text/plain; version=0.0.4`.
8. **Почему `/health` делают «дешёвым»** — никаких внешних вызовов и БД: иначе проба в k8s начнёт падать
   вместе с зависимостью и Kubernetes будет перезапускать здоровый под по кругу.

## 1.2 Код — `service/app.py` (30 мин)

Файл создаём в репозитории: `~/devops-sprint/service/app.py` (папка `service/` новая).

```bash
cd /home/rafael/devops-sprint
mkdir -p service
nano service/app.py
```

Каркас (детали дописываешь сам — это ядро дня, не копипаст):

```python
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("APP_PORT", "8080"))
VERSION = os.environ.get("APP_VERSION", "0.1.0")
ENV_NAME = os.environ.get("APP_ENV", "local")


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self.server.requests += 1
        if self.path == "/health":
            self._send(200, json.dumps({"status": "ok"}))
        elif self.path == "/metrics":
            # счётчик + info-метрика с версией (метка в фигурных скобках)
            ...
        elif self.path == "/":
            self._send(200, json.dumps({"version": VERSION, "env": ENV_NAME, "port": PORT}))
        else:
            self._send(404, json.dumps({"error": "not found"}))


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)   # 0.0.0.0, не 127.0.0.1!
    server.requests = 0
    print("listening on %s" % PORT)
    server.serve_forever()
```

⚠️ **Два грабля из прошлых дней:** слушать `0.0.0.0` (иначе из пода сервис недоступен), и не занимать
порты 80/443/8090 (Traefik/nginx/gpt2giga). Для локальной проверки 8080 свободен.

Проверка (сервер молчит в консоли — это нормально, он слушает):

```bash
python3 service/app.py &
curl -s localhost:8080/health            # → {"status": "ok"}
curl -s localhost:8080/metrics | head -5 # строки метрик с # HELP/# TYPE и счётчиком
curl -s localhost:8080/                   # → версия, env, порт
curl -s -o /dev/null -w '%{http_code}
' localhost:8080/nope   # → 404
kill %1
```

Если `Connection refused` — сервер не поднялся (смотрите трейс), если `404` на `/health` — опечатка в пути.

## 1.3 Практика руками — `practice/s06.py` (15 мин)

Задание: `parse_env(text)` → словарь `KEY=VALUE` из строк, игнорируя пустые строки и комментарии с `#`.
Ожидаемо: `parse_env('A=1\n# ком\nB=2')` → `{'A': '1', 'B': '2'}`.

Три подсказки: `text.splitlines()`, `line.strip()`, `line.split("=", 1)` (именно `1` — иначе значения со знаком
«равно» внутри порежутся). Комментарий отличается от пустой строки: начинается с `#` после `strip()`.

```bash
nano practice/s06.py
python3 practice/s06.py
python3 today.py drill 6      # эталон — сверять ПОСЛЕ своей попытки
```

---
# ЧАСТЬ 2. ИНФРАСТРУКТУРА (60 мин)

## 2.1 Теория (15 мин)

📚 https://kubernetes.io/docs/concepts/configuration/configmap/

1. **Namespace** — логическая изоляция объектов внутри кластера (имена уникальны внутри namespace).
2. **Service** — стабильное имя и балансировка на поды, которые живут и умирают.
   `ClusterIP` — только внутри кластера, `NodePort` — порт на каждой ноде (30000–32767),
   `LoadBalancer` — внешний балансировщик.
3. **ConfigMap** — несекретный конфиг (ключ→значение, целиком файл или env). **Secret** — то же, но для
   секретов; хранится в base64, поэтому это не шифрование, а отдельный тип объекта с другим доступом.
4. **Подключение** — `envFrom.configMapRef` / `envFrom.secretRef` (все ключи как переменные) либо
   `env.valueFrom` (точечно). Так конфиг не вшивается в образ.
5. **requests / limits** — гарантия и потолок ресурсов. Превышение memory-limit → контейнер убивается (OOMKilled).
6. **livenessProbe** — «процесс жив?»: при падении kubelet перезапускает контейнер.
   **readinessProbe** — «готов принимать трафик?»: при падении под исключается из Service, но не перезапускается.
   Отсюда ответ на вопрос дня: неверная liveness = бесконечные рестарты, неверная readiness = пустой Service
   без трафика при живых подах.
7. **Ingress** — HTTP-правила снаружи (в k3s из коробки Traefik на 443). Нам сегодня проще NodePort.

## 2.2 Задача (30 мин) — выложить сервис в k3s

Работаем в `~/devops-sprint/k8s/`. Шесть шагов.

**Шаг 1. Образ в кластере.** k3s (containerd) не видит образы docker напрямую:

```bash
docker images | grep -E 'echo-svc|devcheck'         # что есть у docker
sudo k3s ctr images ls | grep echo-svc              # что уже видит k3s
# если нужного нет — сохранить docker-образ и импортировать:
docker save echo-svc:0.1.0 -o /tmp/echo.tar
sudo k3s ctr images import /tmp/echo.tar
```

**Шаг 2. ConfigMap и Secret** (можно императивно — быстрее для проверки):

```bash
sudo k3s kubectl create configmap app-config --from-literal=APP_VERSION=0.1.0 --from-literal=APP_ENV=k3s
sudo k3s kubectl create secret generic app-secret --from-literal=DB_PASSWORD='s3cret'
sudo k3s kubectl get configmap app-config -o yaml | head -20
```

**Шаг 3. Deployment** — `k8s/app-deployment.yaml`: `replicas: 2`, контейнер с образом из шага 1,
порт 8080, `envFrom` на ConfigMap и Secret, `resources.requests/limits`, обе пробы `httpGet` на `/health`
(порт 8080, `initialDelaySeconds: 3`, `periodSeconds: 5`).

**Шаг 4. Service** — `k8s/app-service.yaml`: `type: NodePort`, `port: 8080`, `targetPort: 8080`,
`nodePort: 30080`, селектор совпадает с метками пода.

**Шаг 5. Применить и проверить:**

```bash
cd /home/rafael/devops-sprint
sudo k3s kubectl apply -f k8s/
sudo k3s kubectl get pods -o wide          # ждём 2/2 Running
sudo k3s kubectl get svc                   # видим NodePort 8080:30080
sudo k3s kubectl describe pod -l app=app   # Events: пробы проходят, образа нет ошибок
curl -s localhost:30080/health             # → {"status": "ok"}  (снаружи кластера)
curl -s localhost:30080/metrics | head -5
```

**Шаг 6. Проверка самовосстановления (это в критерии дня):**

```bash
sudo k3s kubectl delete pod -l app=app
sudo k3s kubectl get pods -w               # видим Terminating → новый ContainerCreating → Running, Ctrl+C
curl -s localhost:30080/health             # сервис отвечает, пока под пересоздаётся
```

## 2.3 Что записать в конспект (30 мин)

`devops-notes.md` или `interview-notes.md`: разница liveness/readiness своими словами, что делает
`kubectl delete pod` при `replicas: 2` (Deployment добивает до нужного числа), зачем `envFrom` вместо
переменных в образе. Ответ на вопрос дня — в `interview-notes.md`.

---
# ЧАСТЬ 3. РАСШИРЕНИЕ (60 мин, добровольно)

То же, но по-взрослому: `labs/day06.md` — манифесты в репозитории + вывод `kubectl get pods` **до и после**
`kubectl delete pod`, плюс `kubectl describe` с пробами. Бонус (+15 мин): поставить заведомо неверную
readiness-пробу (например, `path: /healthz`) и объяснить по `describe`/`get endpoints`, что сделал кластер.

---
# ЧАСТЬ 4. ФИНАЛ

```bash
cd /home/rafael/devops-sprint
git add -A
git commit -m "день 6: /health и /metrics на stdlib, ConfigMap+Secret+пробы в k3s, NodePort"
git push
python3 today.py check     # или дождаться 22:30 — зачёт по коммиту за сегодня
```

**ГОТОВО, ЕСЛИ:** коммит за сегодня; манифесты `ConfigMap`/`Secret`/`Ingress` (или `Service`); `/health` и
`/metrics` отвечают снаружи кластера.

**Если что-то не поднимается:** посмотреть `kubectl describe pod` (Events), затем `kubectl logs`.
Классика: `ImagePullBackOff` — образа нет в containerd (шаг 1); `CrashLoopBackOff` — падает приложение
(sudo k3s kubectl logs); под `Running`, но curl молчит — проба/порт/селектор Service не совпадают.

**🧱 Летит день?** Минимум 15 минут и один коммит — напиши «мини», серия сохранится.
