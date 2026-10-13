# День 7 — подробное задание (13.10.2026): отчёт о кластере из скрипта + хранилище, Job/CronJob, разбор сбоев

Стартовое состояние (проверено): кластер k3s v1.36.5+k3s1 жив, узел `vm-hermes` Ready; `kubectl` работает **без sudo**;
StorageClass `local-path` (default, WaitForFirstConsumer); PVC/PV в кластере пока нет; в `lab` крутятся 2 пода `app` из дня 6.
В k3s containerd есть образы: `app:0.1.0`, `echo-svc:0.1.0`, `nginx:alpine`, `curlimages/curl:latest`, `devcheck:0.1.0/0.1.1`.
В docker есть `postgres:16-alpine` (294 МБ) — для расширения его надо будет занести в k3s.

Раскладка: ядро 150 мин = Python 60 + инфраструктура 60 + конспект 30, плюс расширение 60.

Рабочая папка: `/home/rafael/devops-sprint`

---

## Шаг 0. Проверка старта (3 мин)

```bash
cd /home/rafael/devops-sprint && git pull
kubectl get nodes
kubectl get pods -A | grep -Ev 'kube-system'
kubectl get sc
kubectl -n lab get pods -o wide
```

Ожидаемо: узел Ready, `local-path (default)`, 2 пода `app` в Running.

---

# ЧАСТЬ 1. PYTHON (60 мин) — отчёт о состоянии кластера

📚 https://docs.python.org/3/library/subprocess.html

## 1.1 Теория (15 мин)

1. **`subprocess.run`** — запуск внешней команды: `subprocess.run(["kubectl", "get", "pods"], capture_output=True, text=True)`. Возвращает объект с `returncode`, `stdout`, `stderr`. Без `capture_output=True` вывод уйдёт в консоль и в переменную не попадёт.
2. **Список аргументов, а не строка** — `["kubectl", "-n", "lab", "get", "pods"]`. Со `shell=True` и склейкой строк ловишь инъекции и проблемы с пробелами; в норме — список.
3. **`text=True`** (или `encoding="utf-8"`) — иначе получишь `bytes` и придётся декодировать руками.
4. **Коды возврата** — `returncode == 0` успех; иначе смотреть `stderr`. Полезно `check=False` (по умолчанию) и **своя** обработка, а не падение трейсом.
5. **Машинный вывод kubectl** — `-o json`: разбирать структуру (`items`, `metadata.name`, `status.phase`, `status.containerStatuses[].restartCount`) надёжнее, чем парсить колонки текста.
6. **Ошибки окружения** — `FileNotFoundError`, если `kubectl` нет в PATH; `TimeoutExpired` — если задать `timeout=10`. Оба случая нужно переводить в понятное сообщение и код возврата 1.
7. **`json.dumps(..., ensure_ascii=False, indent=2)`** — отчёт, который приятно читать человеку и удобно сравнивать глазами.

## 1.2 Код — `tools/clustercheck.py` (30 мин)

```bash
cd /home/rafael/devops-sprint
nano tools/clustercheck.py
python3 tools/clustercheck.py
```

Что должен делать скрипт:

1. Двумя вызовами собрать данные: `kubectl get nodes -o json` и `kubectl get pods -A -o json`.
2. Разобрать JSON и посчитать:
   - узлы: имя + есть ли условие `Ready=True` (это `status.conditions[]` с `type: Ready`, `status: "True"`)
   - поды: только проблемные — фаза не `Running`/`Succeeded` ИЛИ есть `containerStatuses[].restartCount > 0`
   - суммарное число рестартов
3. Вывести человекочитаемый отчёт: узел(ы), список проблемных подов `namespace/имя (фаза, рестарты)`, итог.
4. Флаги: `--json` (печатать JSON вместо текста), `--out FILE` (записать отчёт в файл, например `cluster-report.json`).
5. Обработка ошибок: нет `kubectl` → «kubectl не найден в PATH», код возврата 1; команда вернула не 0 → показать `stderr` и код возврата 1.
6. Код возврата: 0 — проблем нет, 2 — проблемы найдены (удобно для cron/CI).

Проверка:

```bash
python3 tools/clustercheck.py                 # видим узлы и проблемные поды (или «проблем нет»)
python3 tools/clustercheck.py --json | head -20
python3 tools/clustercheck.py --out /tmp/report.json && head -5 /tmp/report.json
echo "код возврата: $?"                       # 0 или 2
PATH=/nonexistent python3 tools/clustercheck.py; echo "код: $?"    # 1 и внятное сообщение
```

## 1.3 Практика руками — `practice/s07.py` (15 мин)

Функции: `parse_size('10Gi')` → байты (`Ki`=1024, `Mi`=1024², `Gi`=1024³) и `fmt_size(10737418240)` → `'10Gi'`.

Подсказки: `text.endswith(unit)`, `text[:-len(unit)]`, `float(...)`, и для обратного перевода — сортировка единиц по убыванию множителя.

```bash
nano practice/s07.py
python3 practice/s07.py
python3 today.py drill 7        # эталон — после своей попытки
```

---

# ЧАСТЬ 2. ИНФРАСТРУКТУРА (60 мин) — хранилище, Job/CronJob, разбор сбоев

📚 https://kubernetes.io/docs/concepts/storage/persistent-volumes/

## 2.1 Теория (15 мин)

1. **Volume** — каталог, живущий, пока жив под (данные умирают вместе с подом). **PV** — том в кластере. **PVC** — заявка на том («хочу 1 Gi, режим RWO»). **StorageClass** — как создавать PV: у нас `local-path` (том-каталог на узле).
2. **`volumeBindingMode: WaitForFirstConsumer`** — том не создаётся, пока его не смонтирует первый под. Поэтому только что созданный PVC в статусе `Pending` — **это нормально**, а не сбой.
3. **Режимы доступа**: `ReadWriteOnce` (RWO) — том монтируется на один узел; у `local-path` данные лежат на конкретной ноде, поэтому в мультиузловом кластере под может уехать на другой узел и тома не увидеть.
4. **StatefulSet** — как Deployment, но с предсказуемыми именами (`pg-0`, `pg-1`) и своими PVC на каждую реплику. Нужен базам и всему, что хранит состояние.
5. **Job / CronJob** — разовые и по расписанию задачи: `backoffLimit` (сколько раз повторить), `concurrencyPolicy: Forbid` (не запускать новый запуск, пока идёт предыдущий), `successfulJobsHistoryLimit`/`failedJobsHistoryLimit` (чистка истории), `spec.timeZone` (наши 1.36+ это умеют: `Europe/Moscow`; без него расписание в UTC).
6. **Диагностика сбоев — три команды** (это ответ на вопрос дня):
   - `kubectl get pods` — что за статус: `ImagePullBackOff`, `CrashLoopBackOff`, `Pending`, `OOMKilled` (в `get` видно как частые RESTARTS)
   - `kubectl describe pod` — блоки `Events`, `Last State`, `Limits`, `Conditions`: причина словами
   - `kubectl logs <под> --previous` — лог **предыдущего** контейнера (у упавшего уже нет текущего лога)
7. **Расшифровка статусов**: `ImagePullBackOff`/`ErrImageNeverPull` — образа нет; `CrashLoopBackOff` — процесс падает (код возврата из `logs --previous`); `OOMKilled` — превышен memory-limit; `Pending` — расписание/ресурсы/том.

## 2.2 Задача (30 мин)

### а) PVC и подключение к своему сервису

```bash
cd /home/rafael/devops-sprint
mkdir -p k8s/day07
nano k8s/day07/pvc.yaml
```

Содержимое: `kind: PersistentVolumeClaim`, `name: app-data`, `namespace: lab`, `accessModes: [ReadWriteOnce]`, `resources.requests.storage: 1Gi`, `storageClassName: local-path`.

Подключить том к поду сервиса из дня 6 — дописать в `k8s/day06/deployment.yaml` в контейнер и в `spec`:

```yaml
# внутри containers[0]:
          volumeMounts:
            - name: app-data
              mountPath: /data
# в spec.template.spec:
      volumes:
        - name: app-data
          persistentVolumeClaim:
            claimName: app-data
```

```bash
kubectl apply -f k8s/day07/pvc.yaml
kubectl -n lab get pvc                 # Pending — это норма (ждёт потребителя)
kubectl apply -f k8s/day06/deployment.yaml
kubectl -n lab get pods -o wide        # rollout 2/2
kubectl -n lab get pvc                 # теперь Bound
kubectl -n lab exec deploy/app -- sh -c 'date > /data/heartbeat.txt; cat /data/heartbeat.txt'
kubectl -n lab delete pod -l app=app
kubectl -n lab get pods -w             # новый под, Ctrl+C
kubectl -n lab exec deploy/app -- cat /data/heartbeat.txt   # данные на месте — вот и доказательство
```

### б) CronJob по расписанию

```bash
nano k8s/day07/cronjob.yaml
```

`kind: CronJob`, `name: health-cron`, `namespace: lab`, `schedule: "*/5 * * * *"`, `timeZone: "Europe/Moscow"`, `concurrencyPolicy: Forbid`, `restartPolicy: Never`, история 3/1, контейнер с образом **`curlimages/curl:latest`** (он уже есть в k3s, тянуть из интернета не нужно), `imagePullPolicy: Never`, команда:

```yaml
          command: ["sh", "-c", "date -u; curl -s -m 3 http://app-service.lab.svc.cluster.local:8080/health; echo"]
```

```bash
kubectl apply -f k8s/day07/cronjob.yaml
kubectl -n lab get cronjob,jobs
kubectl -n lab create job --from=cronjob/health-cron manual-test    # не ждать 5 минут
kubectl -n lab logs job/manual-test                                  # видим дату и {"status": "ok"}
```

### в) Сломать и разобрать три сбоя → `troubleshooting.md`

От тебя тут требуется **три эксперимента + один файл-разбор**. По каждому сбою фиксируешь четыре факта:
1. что показал `kubectl get pods` в колонке STATUS (и растут ли RESTARTS);
2. что написал `kubectl describe pod`: блок `Last State` (`Reason`, `Exit Code`) или сообщение в `Events`;
3. что отдал лог упавшего контейнера (`kubectl logs`);
4. вывод одной фразой: причина → что делать.

Каждый сломанный объект после разбора **удалить** — иначе он будет висеть в `lab` и портить отчёты за следующие дни.

```bash
mkdir -p k8s/day07/broken
# 1) ImagePullBackOff — образа нет в реестре
kubectl -n lab create deployment bad-image --image=nope:0.0.1 --dry-run=client -o yaml > k8s/day07/broken/bad-image.yaml
kubectl apply -f k8s/day07/broken/bad-image.yaml
sleep 40; kubectl -n lab get pods -l app=bad-image      # сначала ErrImagePull, через ~40-60 с ImagePullBackOff
kubectl -n lab describe pod -l app=bad-image | tail -15
kubectl -n lab delete deployment bad-image
```
Проверено: в Events `Failed to pull image "nope:0.0.1": ... pull access denied, repository does not exist or may require authorization: ... insufficient_scope: authorization failed`, затем `Error: ErrImagePull` → `Error: ImagePullBackOff`. Логи смотреть нечего — контейнер не стартовал, это и есть суть.

```bash
# 2) OOMKilled — маленький лимит памяти при растущем потреблении
cat > k8s/day07/broken/oom.yaml <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata: {name: oom-demo, namespace: lab}
spec:
  replicas: 1
  selector: {matchLabels: {app: oom-demo}}
  template:
    metadata: {labels: {app: oom-demo}}
    spec:
      containers:
        - name: mem
          image: app:0.1.0
          imagePullPolicy: Never
          command: ["python", "-c", "a=[]\nwhile True: a.append(bytearray(10_000_000))"]
          resources:
            limits: {memory: 32Mi}
            requests: {memory: 16Mi}
YAML
kubectl apply -f k8s/day07/broken/oom.yaml
sleep 30; kubectl -n lab get pods -l app=oom-demo       # STATUS: OOMKilled, RESTARTS растёт
kubectl -n lab describe pod -l app=oom-demo | grep -A3 'Last State'
kubectl -n lab delete deployment oom-demo
```
Проверено: `Last State: Terminated / Reason: OOMKilled / Exit Code: 137` (137 = 128+9, SIGKILL от ядра). Через несколько перезапусков STATUS может смениться на `CrashLoopBackOff` — это нормально, причина та же. `logs` пусто: контейнер убит до того, как что-то напечатать.
Образ именно `app:0.1.0` — он уже в containerd k3s. `python:3.11-slim` есть только в docker, в кластер не занесён: с `imagePullPolicy: Never` получишь `ErrImageNeverPull`, а не OOM. Хочешь «как в доке» — сначала `sg docker -c 'docker save python:3.11-slim -o /tmp/py.tar' && sudo k3s ctr images import /tmp/py.tar`.

```bash
# 3) CrashLoopBackOff — процесс стартует и сразу падает с кодом 1
kubectl -n lab create deployment crash-demo --image=app:0.1.0 --dry-run=client -o yaml > k8s/day07/broken/crash.raw.yaml
# правим crash.raw.yaml руками: imagePullPolicy: Never и command:
#   ["python", "-c", "import sys;print('стартую и падаю', flush=True);sys.exit(1)"]
mv k8s/day07/broken/crash.raw.yaml k8s/day07/broken/crash.yaml
kubectl apply -f k8s/day07/broken/crash.yaml
sleep 30; kubectl -n lab get pods -l app=crash-demo      # Error, RESTARTS растёт → CrashLoopBackOff
kubectl -n lab logs -l app=crash-demo                    # «стартую и падаю»
kubectl -n lab describe pod -l app=crash-demo | grep -A4 'Last State'
kubectl -n lab delete deployment crash-demo
```
Проверено: `Last State: Terminated / Reason: Error / Exit Code: 1`, лог `стартую и падаю` отдаёт **обычный `logs` без `--previous`**.

⚠️ Про `--previous` на нашем кластере (важный вывод, впиши его в конспект): лог предыдущего инстанса `containerd` уже удалил, команда отвечает
`unable to retrieve container logs for containerd://...`. Смысл такой: `--previous` нужен, когда контейнер **сейчас работает** (перезапустился и жив), а тебе нужен лог прошлой попытки; а в `CrashLoopBackOff` текущий инстанс и есть последний упавший, поэтому работает обычный `kubectl logs`. Если и он пуст — причина не в логе, а в `describe`: `Last State` (Reason/Exit Code) и `Events`.
Порядок команд в разборе поэтому держи такой: `get pods` (статус) → `describe pod` (Reason/Exit Code/Events) → `logs` (что успел сказать процесс).

## 2.3 Конспект (30 мин)

- `interview-notes.md`: вопрос дня — три первые команды разбора упавшего пода и что показывает каждая.
- `devops-notes.md`: почему PVC `Pending` до первого потребителя; чем StatefulSet отличается от Deployment; что делает `concurrencyPolicy: Forbid`; таблица «статус → причина → что смотреть».

---

# ЧАСТЬ 3. РАСШИРЕНИЕ (60 мин, добровольно) — Postgres с PVC + Job-дамп + labs/day07.md

```bash
sg docker -c 'docker save postgres:16-alpine -o /tmp/pg.tar' && sudo k3s ctr images import /tmp/pg.tar
sudo k3s ctr images ls -q | grep postgres
```

1. `k8s/day07/postgres.yaml`: PVC `pg-data` (1Gi) + Deployment `postgres` (образ `postgres:16-alpine`, `imagePullPolicy: Never`, env `POSTGRES_PASSWORD`, `POSTGRES_DB=lab`, **`PGDATA=/var/lib/postgresql/data/pgdata`** — иначе initdb упирается в непустой каталог), `volumeMounts /var/lib/postgresql/data`, limits 256Mi/512Mi.
2. Записать и проверить данные:

```bash
kubectl -n lab exec deploy/postgres -- psql -U postgres -d lab -c "create table t(id int, note text); insert into t values (1,'до пересоздания');"
kubectl -n lab delete pod -l app=postgres
kubectl -n lab get pods -w            # новый под
kubectl -n lab exec deploy/postgres -- psql -U postgres -d lab -c "select * from t;"   # строка на месте
kubectl -n lab get pvc
```

3. `k8s/day07/dump-job.yaml`: Job `pg-dump` (образ `postgres:16-alpine`, `restartPolicy: Never`) → `pg_dump -U postgres -d lab -t t` (вывод в логи, `kubectl logs job/pg-dump`).
4. `labs/day07.md`: вывод `kubectl get pvc` + результат `select` после пересоздания пода + лог Job. Проверка: `python3 today.py extra`.
5. Бонус (+15): HPA по CPU (`kubectl -n lab autoscale deploy app --min=2 --max=5 --cpu-percent=50`), проверить `kubectl -n lab get hpa` — requests у нас есть, metrics-server в k3s стоит.

---

# ЧАСТЬ 4. ФИНАЛ

```bash
cd /home/rafael/devops-sprint
git add -A
git commit -m "день 7: clustercheck.py, PVC+CronJob, разбор ImagePullBackOff/CrashLoopBackOff/OOMKilled"
git push
gh run list --limit 1
python3 today.py check
```

**ГОТОВО, ЕСЛИ:** коммит за сегодня; PVC подключён к сервису и данные переживают пересоздание пода; CronJob отработал; в `troubleshooting.md` разобран минимум один реальный сбой (лучше три).

**Минимум при загруженном дне:** 15 минут и один коммит (`python3 today.py mini`); полный перенос — `python3 today.py shift`.

**Не трогать:** порты 80/443/8090; правила по 22-му порту; секреты в открытом виде в репозиторий не класть.
