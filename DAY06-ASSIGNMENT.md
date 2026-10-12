# День 6 — подробное задание (12.10.2026): HTTP-сервис на stdlib + конфиг/секреты/пробы в k3s

Состояние на старт: день 6 в очереди (переносился 10.10 и 11.10), серия 25, дедлайн 22.10.
В репозитории по дню 6 пока **ничего нет**: нет `service/`, нет `practice/s06.py`, нет `labs/day06.md`.
В k3s живёт вчерашний `devcheck` (образ `echo-svc:0.1.0`, 2 реплики) — его не ломаем, делаем рядом новое имя.

Раскладка: **ядро 150 мин** = Python 60 + инфраструктура 60 + конспект 30. Расширение 60 мин — добровольное (гейт не пройден).

Рабочая папка везде: `/home/rafael/devops-sprint`

---

# ПОСЛЕДОВАТЕЛЬНОСТЬ ДЕЙСТВИЙ

## Шаг 0. Проверка стартового состояния (3 мин)

```bash
cd /home/rafael/devops-sprint
git pull                      # убедиться, что локально последняя версия
sudo k3s kubectl get pods -o wide      # должно быть 2 пода devcheck в Running
sudo k3s ctr images ls -q | grep -Ei 'echo-svc|python'   # какие образы видит k3s
docker images | head -5       # если «permission denied» — команды docker через: sg docker -c '...'
```

Ожидаемо: 2 пода `devcheck` в Running, в k3s есть `echo-svc:0.1.0`. Если кластер лежит — `sudo systemctl status k3s`.

---

## ЧАСТЬ 1. PYTHON (60 мин)

### 1.1 Теория (15 мин) — прочитать, не конспектировать

📚 https://docs.python.org/3/library/http.server.html

1. **`http.server`** — HTTP-сервер в стандартной библиотеке: `HTTPServer` (по одному запросу за раз) и `ThreadingHTTPServer` (поток на запрос). Парсинг HTTP готовый, маршруты пишем сами.
2. **`BaseHTTPRequestHandler`** — обрабатывает один запрос; метод `do_GET(self)` отвечает на GET; путь лежит в `self.path` (вместе с query-строкой).
3. **Роутинг руками** — ветки по `self.path`: `/health`, `/metrics`, `/`, `else → 404`. Смысл дня — увидеть, что фреймворк делает за нас.
4. **Ответ из трёх шагов** — `send_response(200)` → `send_header("Content-Type", ...)` → `end_headers()` → `wfile.write(body.encode("utf-8"))`. `Content-Length` ставим явно, иначе curl подвисает.
5. **Счётчики на объекте сервера** (`self.server.requests`), а не в глобальной переменной — так метрики живут дольше одного запроса и видны всем обработчикам.
6. **Конфиг через окружение** — `os.environ.get("APP_PORT", "8080")`. Дефолт обязателен, иначе сервис упадёт там, где переменной нет.
7. **Формат метрик Prometheus** — построчный текст: `имя значение` и `имя{метка="значение"} значение` + строки `# HELP`/`# TYPE`. Content-Type: `text/plain; version=0.0.4`.
8. **Почему `/health` делают «дешёвым»** — без внешних вызовов и БД: иначе проба падает вместе с зависимостью, и k8s перезапускает полностью здоровый под.

### 1.2 Код — `service/app.py` (30 мин)

```bash
cd /home/rafael/devops-sprint
mkdir -p service
nano service/app.py
```

Требования к сервису (детали дописываешь сам):

- `PORT` из `APP_PORT` (дефолт 8080), `VERSION` из `APP_VERSION`, `ENV_NAME` из `APP_ENV`, `SECRET` из `APP_SECRET` (дефолт `none`)
- `GET /health` → `{"status":"ok"}` — ничего внешнего не трогает
- `GET /metrics` → Prometheus-текст: `app_requests_total` (счётчик), `app_info{version="...",env="..."} 1`, `app_uptime_seconds`
- `GET /` → версия, окружение, порт (пароль в вывод **не** отдаём)
- любой другой путь → 404
- сервер слушает **`0.0.0.0`** (не `127.0.0.1` — иначе из пода не достучаться)

Локальная проверка:

```bash
cd /home/rafael/devops-sprint
python3 service/app.py &
curl -s localhost:8080/health                  # {"status": "ok"}
curl -s localhost:8080/metrics | head -5       # # HELP / # TYPE / счётчик
curl -s localhost:8080/                        # версия, env, порт
curl -s -o /dev/null -w '%{http_code}\n' localhost:8080/nope   # 404
kill %1
```

### 1.3 Образ для кластера (10 мин, внутри блока инфры)

k3s (containerd) не видит docker-образы напрямую. Создать `service/Dockerfile`:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY app.py .
ENV APP_PORT=8080
EXPOSE 8080
HEALTHCHECK CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8080/health')" || exit 1
CMD ["python", "app.py"]
```

Сборка и импорт в k3s (образ `python:3.11-slim` уже есть локально, интернет образу не нужен):

```bash
cd /home/rafael/devops-sprint/service
sg docker -c 'docker build -t app:0.1.0 .'          # если docker работает и без sg — просто docker build
sg docker -c 'docker save app:0.1.0 -o /tmp/app.tar'
sudo k3s ctr images import /tmp/app.tar
sudo k3s ctr images ls -q | grep app:0.1.0           # видим образ в k3s
```

### 1.4 Практика руками — `practice/s06.py` (15 мин)

`parse_env(text)` → словарь `KEY=VALUE`, игнорируя пустые строки и комментарии с `#`.
Ожидаемо: `parse_env('A=1\n# ком\nB=2')` → `{'A': '1', 'B': '2'}`

Подсказки: `text.splitlines()`, `line.strip()`, `line.split("=", 1)` (именно `1`), отсев строк, начинающихся с `#`.

```bash
nano practice/s06.py
python3 practice/s06.py
python3 today.py drill 6        # эталон — только ПОСЛЕ своей попытки
```

---

## ЧАСТЬ 2. ИНФРАСТРУКТУРА (60 мин)

### 2.1 Теория (15 мин)

📚 https://kubernetes.io/docs/concepts/configuration/configmap/

1. **Namespace** — изоляция объектов внутри кластера; имена уникальны только внутри него.
2. **Service** — стабильное имя + балансировка на поды, которые живут и умирают. `ClusterIP` — только внутри, `NodePort` — порт на каждой ноде (30000–32767), `LoadBalancer` — внешний балансировщик.
3. **ConfigMap** — несекретный конфиг. **Secret** — то же для секретов; лежит в base64, то есть это **не шифрование**, а отдельный объект с другим доступом и правами.
4. **Как подключить** — `envFrom.configMapRef` / `envFrom.secretRef` (все ключи переменными) или точечно `env.valueFrom`. Конфиг не вшивается в образ.
5. **requests / limits** — гарантия и потолок. Превышение memory-limit → `OOMKilled`.
6. **livenessProbe** — «процесс жив?»: падение → kubelet перезапускает контейнер. **readinessProbe** — «готов принимать трафик?»: падение → под убирается из Service, но **не** перезапускается.
7. **Ingress** — HTTP-правила снаружи; в k3s из коробки Traefik на 443. Сегодня проще и нагляднее NodePort.

### 2.2 Манифесты — папка `k8s/day06/` (20 мин)

```bash
cd /home/rafael/devops-sprint
mkdir -p k8s/day06
```

Создать пять файлов (все — с `namespace: lab`):

1. `k8s/day06/namespace.yaml` — `kind: Namespace`, `metadata.name: lab`
2. `k8s/day06/configmap.yaml` — `app-config`: `APP_ENV=k3s`, `APP_VERSION=0.1.0`, `APP_LOG_LEVEL=info`
3. `k8s/day06/secret.yaml` — `app-secret` через `stringData: {APP_SECRET: "s3cret"}` (закоммитить как пример, реальный пароль в репозиторий не кладём)
4. `k8s/day06/deployment.yaml` — `app`, 2 реплики, `image: app:0.1.0`, `imagePullPolicy: Never` (образ локальный, в реестре его нет), `containerPort: 8080`, `envFrom` на ConfigMap и Secret, requests/limits (`50m/64Mi` … `200m/256Mi`), обе пробы `httpGet /health` (readiness: `initialDelaySeconds: 3`, `periodSeconds: 5`; liveness: `initialDelaySeconds: 10`, `periodSeconds: 10`)
5. `k8s/day06/service.yaml` — `app-service`, `type: NodePort`, `port: 8080`, `targetPort: 8080`, `nodePort: 30080`

Опция «сделать по-взрослому»: шестым файлом `k8s/day06/ingress.yaml` — `Ingress` на хост `app.local` → `app-service:8080` (в k3s обслуживает Traefik на 443; тогда проверка через `curl -k -H 'Host: app.local' https://localhost/health`).

### 2.3 Применить и проверить (15 мин)

```bash
cd /home/rafael/devops-sprint
sudo k3s kubectl apply -f k8s/day06/
sudo k3s kubectl -n lab get pods -o wide           # ждём 2/2 Running
sudo k3s kubectl -n lab get svc                    # app-service NodePort 8080:30080
sudo k3s kubectl -n lab describe pod -l app=app    # Events: пробы проходят, образ не тянется (Never)
curl -s localhost:30080/health                     # {"status":"ok"} — снаружи кластера
curl -s localhost:30080/metrics | head -5
curl -s localhost:30080/                           # версия/окружение из ConfigMap
sudo k3s kubectl -n lab logs -l app=app            # пусто/минимум — норма
```

Диагностика, если не поднялось:
- `ImagePullBackOff` → образа нет в containerd (шаг 1.3) или не стоит `imagePullPolicy: Never`
- `CrashLoopBackOff` → смотри `kubectl -n lab logs -l app=app`
- под `Running`, но curl молчит → порт/селектор Service не совпадают с метками пода, либо слушается `127.0.0.1`

### 2.4 Самовосстановление — это в критерии дня (5 мин)

```bash
sudo k3s kubectl -n lab get pods -o wide                  # снимок «до»
sudo k3s kubectl -n lab delete pod -l app=app
sudo k3s kubectl -n lab get pods -w                       # Terminating → ContainerCreating → Running, Ctrl+C
curl -s localhost:30080/health                            # сервис отвечает и во время пересоздания
```

### 2.5 Конспект (30 мин)

- `interview-notes.md`: ответ на вопрос дня — **зачем liveness и readiness по отдельности и что будет при неверной пробе**. Своими словами, с двумя сценариями: слишком строгая liveness → бесконечные рестарты и застрявший rollout; неверная readiness → под жив, но выведен из балансировки, клиент получает 503.
- `devops-notes.md`: что делает `kubectl delete pod` при `replicas: 2`; зачем `envFrom` вместо переменных в образе; почему Secret в base64 — не защита.

---

## ЧАСТЬ 3. РАСШИРЕНИЕ (60 мин, добровольно) — `labs/day06.md`

Файл `labs/day06.md` в репозитории: ссылка на манифесты + выводы команд:

- `kubectl -n lab get pods -o wide` **до** и **после** `delete pod`
- `kubectl -n lab describe pod` — блок проб (Liveness/Readiness)
- `kubectl -n lab get endpoints app-service` — что происходит с эндпоинтами
- вывод `curl -s localhost:30080/health` и `/metrics`

Проверка блока: `python3 today.py extra`
Бонус (+15 мин): поставить заведомо неверную readiness-пробу (`path: /healthz`) и объяснить по `describe`/`get endpoints`, что сделал кластер.

---

## ЧАСТЬ 4. ФИНАЛ — коммит и зачёт

```bash
cd /home/rafael/devops-sprint
git add -A
git status --short
git commit -m "день 6: /health и /metrics на stdlib, ConfigMap+Secret+пробы, NodePort в k3s"
git push
gh run list --limit 1        # CI должен быть success
python3 today.py check       # если коммит за сегодня есть — день закрывается (авто-зачёт в 22:30)
```

**ГОТОВО, ЕСЛИ:** есть коммит за сегодня; в репозитории манифесты ConfigMap/Secret (+Service/NodePort); `/health` и `/metrics` отвечают снаружи кластера (порт 30080).

**🧱 Летит день (инциденты):** минимум — 15 минут и один коммит, написать «мини» (`python3 today.py mini`). Полный перенос дня — `python3 today.py shift` (день не сгорает, серия сохраняется).

**ЗАПРЕТЫ (повтор):** не занимать порты 80, 443, 8090; в поде слушать `0.0.0.0`; секреты не коммитить в открытом виде; правила nginx-фаервола по 22-му порту не трогать.
