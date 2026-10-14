# День 8 — подробное задание (15.10.2026, перенесено с 14.10): CI/CD — пайплайн скриптом и в GitHub Actions

Стартовое состояние (проверено 14.10, 11:26 МСК): HEAD `1cc1b84`, день 7 зачтён, серия 27.
Спринт сдвинут на день: 14.10 — перенос (занятие не проводится), дедлайн спринта 23.10.
Кластер k3s жив, в `lab` только `deployment/app` 2/2 (мусор от дня 7 убран). `gh` авторизован как `Akhmra`
(есть scope `workflow`, `write:packages`). В `.github/workflows/ci.yml` лежит рабочий минимум:
`setup-python 3.11` → `compileall tools/` → `python tools/devcheck.py --json` → `pytest tests/` (3 passed).
`~/devops-sprint/.venv/bin/pytest` есть, `sudo` для rafael — NOPASSWD, поэтому шаги деплоя в CI могут
делать `sudo k3s ctr images import`.

Раскладка дня: ядро 150 мин = Python 60 + инфраструктура 60 + конспект 30, плюс расширение 60 (добровольно:
гейт по расширениям не пройден — 3 из 6, поэтому норматив 150 мин).

Рабочая папка: `/home/rafael/devops-sprint`

---

## Шаг 0. Проверка старта (3 мин)

```bash
cd /home/rafael/devops-sprint && git pull
kubectl -n lab get deploy,pods
gh auth status | head -3
gh run list --limit 3
```

Ожидаемо: `deployment.apps/app 2/2`, последний ран `success`, аккаунт `Akhmra`.

---

# ЧАСТЬ 1. PYTHON (60 мин) — пайплайн как скрипт

📚 https://docs.python.org/3/library/subprocess.html

## 1.1 Теория (15 мин)

1. **Пайплайн = последовательность стадий**, где каждая — либо «зелёная», либо «красная». Ключевое правило:
   **остановка на первой красной** — не запускать `deploy`, если упал `test` (иначе ломаем то, что работает).
2. **Признак стадии — код возврата**, а не текст в выводе: `subprocess.run(cmd, check=False).returncode == 0`.
   Проверять текст (`if "error" in out`) — типичная ошибка новичка: вывод меняется, логика ломается.
3. **`subprocess.run(..., capture_output=True, text=True)`** — вывод в переменную, а не в консоль; список
   аргументов вместо строки с `shell=True`; `timeout=` защищает от вечно висящей стадии (у нас актуально:
   `rollout status` может висеть, если образ не подхватился).
4. **Логирование шагов**: писать в отчёт «стадия → команда → код возврата → сколько заняла». Иначе
   пайплайн — чёрный ящик, и после красного прогона непонятно, что чинить.
5. **Единый путь локально и в CI.** Скрипт и workflow выполняют одни и те же команды — тогда красный локальный
   прогон объясняет красный CI, а не «в CI почему-то не так».
6. **Тег образа = идентификатор версии**: `app:<короткий sha>` (`git rev-parse --short HEAD`), а не `latest`.
   По тегу видно, что именно выкачено, и есть куда откатываться.

## 1.2 Код — `scripts/ci.py` (30 мин)

```bash
cd /home/rafael/devops-sprint
mkdir -p scripts
nano scripts/ci.py
```

Требования к скрипту:

1. Список стадий: `lint`, `test`, `build`, `push`, `deploy` — каждая с человекочитаемым именем и командами.
2. Команды стадий (эти конкретные — проверены, работают в нашем окружении):

| стадия | команда |
|---|---|
| lint | `python3 -m compileall -q tools/ service/` |
| test | `.venv/bin/python -m pytest tests/ -q` |
| build | `sg docker -c 'docker build -t app:<sha> service/'` |
| push | `sg docker -c 'docker push ghcr.io/akhmra/devops-sprint:<sha>'` (после `docker tag`) |
| deploy | `sg docker -c 'docker save app:<sha>' \| sudo k3s ctr images import -`, затем `kubectl -n lab set image deployment/app app=app:<sha>`, затем `kubectl -n lab rollout status deployment/app --timeout=90s` |

3. `sha` — короткий хеш `git rev-parse --short HEAD`, один на весь прогон (все стадии работают с одним тегом).
4. Остановка на первой красной стадии: дальше не идём, код возврата скрипта ≠ 0.
5. Итоговый отчёт: по каждой стадии статус (`OK`/`FAIL`), код возврата и время; упавшая стадия — последняя строка.
6. Флаг `--skip lint,test` (или `--from build`) — чтобы повторять с нужной стадии, а не гонять всё заново.
7. Ошибка в команде должна читаться: печатать стадию, команду и `stderr`, без голого трейса.

Проверка (ожидаемые факты — из реального прогона):

```bash
python3 scripts/ci.py                 # все стадии зелёные, в конце отчёт, код возврата 0
echo "EXIT=$?"
# ломаем тест и убеждаемся, что пайплайн встаёт на нём:
printf '\ndef test_fail():\n    assert False\n' >> tests/test_devcheck.py
python3 scripts/ci.py; echo "EXIT=$?"  # стоп после test, deploy НЕ выполняется, EXIT != 0
git checkout tests/test_devcheck.py
docker build -q -t app:citest service/   # проверено: сборка из service/ находит свой Dockerfile
sg docker -c 'docker rmi app:citest'
```

## 1.3 Практика руками — `practice/s08.py` (15 мин)

Функция `pipeline(stages)` → `(ok, пройдено, упавшая)`, где `stages` — список пар `(имя, True/False)`;
остановка на первой `False`.

Ожидаемый результат: `pipeline([('lint', True), ('test', False), ('build', True)])` → `(False, ['lint'], 'test')`
(проверено сверкой с эталоном движка).

```bash
nano practice/s08.py
python3 practice/s08.py
python3 today.py drill 8        # эталон — после своей попытки
```

---

# ЧАСТЬ 2. ИНФРАСТРУКТУРА (60 мин) — GitHub Actions, раннер, деплой в k3s

📚 https://docs.github.com/en/actions/get-started/quickstart

## 2.1 Теория (15 мин)

1. **Workflow** = YAML в `.github/workflows/`; `on` — события; **job** — набор шагов на одной машине;
   **step** — одна команда или `uses:`-экшен; `needs` задаёт порядок и запускает job по зависимости.
2. **`runs-on`** — где выполнять: `ubuntu-latest` (облако GitHub) или `[self-hosted, linux, x64]` — раннер
   на нашей ВМ. Self-hosted нужен, потому что наша ВМ сама является целью деплоя и в кластер образ из
   интернета не тянется.
3. **`permissions:`** — по умолчанию токен job'а read-only: чтобы пушить в GHCR, нужен
   `packages: write`. Это самая частая причина `denied: installation not allowed to Create organization package`.
4. **`secrets`** — не в YAML: `${{ secrets.GITHUB_TOKEN }}` есть всегда (на время job'а), остальное — через
   `gh secret set`. Секреты в логах маскируются, но печатать их самому (`echo $TOKEN`) не нужно.
5. **`if:` и условия** — деплоить только с `main`: `if: github.ref == 'refs/heads/main'`; также есть
   `concurrency` (не запускать два деплоя одновременно).
6. **Кэш** — `actions/setup-python` с `cache: pip` ускоряет установку, но требует файла зависимостей
   (`requirements*.txt`/`pyproject.toml`) — у нас его нет, это шаг расширения.
7. **«Сборка один раз, деплой везде»** — артефакт (образ) собирается однократно, дальше один и тот же
   digest едет в окружения. Иначе тестируешь и выкатываешь разные сборки.
8. **Откат** — `kubectl rollout undo deployment/app`: кластер хранит предыдущий ReplicaSet, поэтому откат
   мгновенный и не требует пересборки.

## 2.2 Шаг 1 — self-hosted runner на ВМ (20 мин)

Архив раннера уже скачан и распакован: `~/actions-runner` (v2.338.0, `./bin/Runner.Listener --version`
проверено). Токен регистрации выдаётся на 1 час через API.

```bash
cd ~/actions-runner
TOKEN=$(gh api -X POST repos/Akhmra/devops-sprint/actions/runners/registration-token --jq .token)
./config.sh --url https://github.com/Akhmra/devops-sprint --token "$TOKEN" \
  --name vm-hermes --labels self-hosted,linux,x64,vm-hermes --unattended --replace
sudo ./svc.sh install rafael
sudo ./svc.sh start
gh api repos/Akhmra/devops-sprint/actions/runners \
  --jq '.runners[] | {name, status, busy, labels: [.labels[].name]}'
```

Ожидаемо: раннер `vm-hermes` в статусе `online`. Если job висит в `Queued` — раннер оффлайн, смотреть
`sudo journalctl -u actions.runner.* -n 30` и `~/actions-runner/_diag/`.

## 2.3 Шаг 2 — workflow: lint → test → build → push → deploy (20 мин)

Правим `.github/workflows/ci.yml` (образец ниже — имена и теги сверить со своим репозиторием):

```yaml
name: ci
on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:

permissions:
  contents: read
  packages: write

jobs:
  lint-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Синтаксис
        run: python -m compileall -q tools/ service/
      - name: Тесты
        run: |
          python -m pip install -q pytest
          python -m pytest tests/ -q

  build-push:
    needs: lint-test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Сборка образа
        run: docker build -t ghcr.io/akhmra/devops-sprint:${{ github.sha }} service/
      - name: Вход в GHCR
        run: echo "${{ secrets.GITHUB_TOKEN }}" | docker login ghcr.io -u ${{ github.actor }} --password-stdin
      - name: Push
        run: docker push ghcr.io/akhmra/devops-sprint:${{ github.sha }}

  deploy:
    needs: build-push
    if: github.ref == 'refs/heads/main'
    runs-on: [self-hosted, linux, x64]
    steps:
      - name: Забрать образ из реестра
        run: |
          echo "${{ secrets.GITHUB_TOKEN }}" | sg docker -c "docker login ghcr.io -u ${{ github.actor }} --password-stdin"
          for i in 1 2 3; do
            sg docker -c "docker pull ghcr.io/akhmra/devops-sprint:${{ github.sha }}" && break
            echo "попытка $i не прошла, повтор"; sleep 5
          done
      - name: Занести в containerd и выкатить
        run: |
          sg docker -c "docker save ghcr.io/akhmra/devops-sprint:${{ github.sha }}" | sudo k3s ctr images import -
          kubectl -n lab set image deployment/app app=ghcr.io/akhmra/devops-sprint:${{ github.sha }}
          kubectl -n lab rollout status deployment/app --timeout=90s
```

Грабли, заложенные в образец (проверены):
- **имя образа — только строчными**: `ghcr.io/Akhmra/...` даёт `invalid reference format: repository name must be lowercase`.
  `${{ github.repository }}` = `Akhmra/devops-sprint` — с большой буквы, поэтому в командах пишем литерал `akhmra/devops-sprint`.
- **`sudo k3s ctr images import -` читает tar из stdin** — проверено, работает (`docker save … | sudo k3s ctr images import -`).
- **образ в кластер попадает только так**: containerd k3s в интернет не ходит, GHCR ему недоступен,
  поэтому на раннере `docker pull` → `docker save | ctr import`. Тег при этом тот же sha → «сборка один раз».
- **`docker pull` из GHCR может упасть на TLS-таймауте с первого раза** — поэтому цикл на 3 попытки.
- контейнер в манифесте называется `app` (`kubectl -n lab set image deployment/app app=…`) — сверить со своим
  `k8s/day06/deployment.yaml`, при другом имени подставить его.

## 2.4 Шаг 3 — проверка деплоя и откат (5 мин)

```bash
git add -A && git commit -m "день 8: ci.py и пайплайн GitHub Actions с деплоем в k3s" && git push
gh run list --limit 3
gh run watch $(gh run list --limit 1 --json databaseId --jq '.[0].databaseId')
kubectl -n lab get pods -o jsonpath='{.items[*].spec.containers[*].image}'; echo
kubectl -n lab rollout history deployment/app
kubectl -n lab rollout undo deployment/app        # откат на предыдущую ревизию
kubectl -n lab rollout status deployment/app --timeout=90s
kubectl -n lab get pods -o jsonpath='{.items[*].spec.containers[*].image}'; echo   # вернулся прежний тег
```

Для отката в истории уже есть 2 ревизии — есть куда откатываться. Проверять глазами именно тег образа у пода.

---

# ЧАСТЬ 3. РАСШИРЕНИЕ (60 мин, добровольно)

1. `matrix` по версиям Python (`3.9` и `3.11`) в job'е тестов, чтобы ловить различия версий.
2. `cache: pip` в `setup-python` — сначала создать `requirements-dev.txt` с `pytest` (без файла зависимостей
   кэш не включается).
3. `actions/upload-artifact` — сохранять tar собранного образа и отчёт `scripts/ci.py`.
4. Сознательно сломать тест и увидеть красный CI, затем починить.
5. `labs/day08.md`: ссылки на красный и зелёный прогоны + вывод `gh run list`. Проверка: `python3 today.py extra`.

Бонус (+15): smoke-тест после деплоя внутри пайплайна (`curl -fsS --max-time 5 http://127.0.0.1:30080/health`),
который валит пайплайн при 5xx.

---

# ЧАСТЬ 4. ФИНАЛ

```bash
cd /home/rafael/devops-sprint
git add -A
git commit -m "день 8: ci.py, workflow с деплоем в k3s, откат"
git push
gh run list --limit 2
python3 today.py check
```

**ГОТОВО, ЕСЛИ:** коммит за сегодня; `scripts/ci.py` прогоняет lint → test → build → push → deploy и встаёт
на первой красной стадии; `.github/workflows/ci.yml` зелёный в Actions (все три job'а) и заканчивается
новым тегом образа в k3s; откат `rollout undo` проверен.

**Минимум при загруженном дне:** 15 минут и один коммит (`python3 today.py mini`); полный перенос — `python3 today.py shift`.

**Мелочь на «потом»:** у `k8s/day07/cronjob.yaml` не заданы `successfulJobsHistoryLimit`/`failedJobsHistoryLimit`
(в задании дня 7 было 3/1) — Completed-поды копятся. Добавить 3/1 при следующей правке манифестов.

**Не трогать:** порты 80/443/8090; правило по 22-му порту; секреты в открытом виде в репозиторий не класть.
