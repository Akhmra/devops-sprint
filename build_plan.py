#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Генератор плана DevOps-спринта (16 дней, 3–18 октября 2026), 150 минут в день.

Источник правды. Правишь DAYS → запускаешь `python3 build_plan.py` → plan.json пересобирается,
state.json (прогресс) не трогается.
"""
import json, os, sys
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.abspath(__file__))

START = "2026-10-03"
END = "2026-10-18"
MINUTES_TOTAL = 150          # 2,5 часа: 60 автоматизация + 60 инфра/DevOps + 30 конспект и разбор
SPLIT = {"python": 60, "infra": 60, "notes": 30}
DRILL_MINUTES = 15           # входит в блок автоматизации

# ---------------------------------------------------------------- дни спринта
DAYS = [
 dict(day=1, py=dict(
   topic="CLI devcheck: инвентарь сервера (CPU, RAM, диск) на чистой стандартной библиотеке",
   source="https://docs.python.org/3/library/argparse.html",
   theory="argparse: позиционные аргументы, флаги, --json, код возврата. Чтение /proc/loadavg, /proc/meminfo, shutil.disk_usage.",
   code="tools/devcheck.py --json → {'cpu_load','mem_used_pct','disk_used_pct','ok'} и код возврата 1, если превышен порог"),
   inf=dict(
   topic="Кто такой DevOps/SRE в облачном провайдере: зоны ответственности, CI/CD, IaC, мониторинг, on-call",
   source="https://ru.wikipedia.org/wiki/DevOps",
   task="Репозиторий ~/devops-sprint: git init, .gitignore, README с целью спринта и дедлайном 18.10, "
        "затем GitHub (gh auth login → gh repo create devops-sprint → push) и первый workflow-заготовка; "
        "в devops-notes.md — карта компетенций стажировки: 10 пунктов, у каждого свой уровень 0–3 и чем закрываю"),
   q="Чем DevOps отличается от SRE и от системного администратора? Где в облаке проходит граница ответственности провайдера и клиента?",
   done="коммит за сегодня: README.md + tools/devcheck.py, который запускается и печатает показатели этой ВМ",
   bonus="добавить в devcheck.py ключ --threshold и текст предупреждения"),

 dict(day=2, py=dict(
   topic="Разбор логов: топ сообщений и ошибки за сутки",
   source="https://docs.python.org/3/library/collections.html",
   theory="collections.Counter, re, чтение больших файлов построчно, сортировка по частоте.",
   code="tools/logparse.py /var/log/syslog → топ-5 сообщений по частоте и список строк со словом error"),
   inf=dict(
   topic="Linux как продакшн-платформа: процессы и ресурсы, systemd-юниты и таймеры, journald, диагностика (ps, ss, lsof, strace)",
   source="https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html",
   task="Написать systemd-юнит devcheck.service + devcheck.timer, который раз в час кладёт вывод devcheck в /var/log/devcheck.log; "
        "проверить systemctl list-timers, journalctl -u, посмотреть ресурсы через ps/top"),
   q="Чем systemd-таймер отличается от cron и почему в проде часто выбирают таймер? Как понять, почему сервис упал: порядок действий?",
   done="коммит за сегодня: tools/logparse.py + devcheck.service/.timer; systemctl list-timers показывает твой таймер",
   bonus="лог-парсер читает вывод journalctl -o json через subprocess"),

 dict(day=3, py=dict(
   topic="Сетевой чекер: HTTP с таймаутом и повторными попытками",
   source="https://docs.python.org/3/library/urllib.request.html",
   theory="urllib.request, таймауты, коды ответа, измерение времени ответа, повторные попытки с паузой.",
   code="tools/httpcheck.py URL... → код, время в мс, метка ok/fail; повтор 3 раза при ошибке"),
   inf=dict(
   topic="Сеть, DNS, TLS и вход в сервис: nginx как reverse proxy, порты, сертификаты, диагностика dig/curl -v/ss/tcpdump",
   source="https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/",
   task="Поднять на этой ВМ nginx: 443 (TLS, самоподписанный сертификат) → проксирует на локальный сервис; "
        "проверить openssl s_client и curl -vk, записать в net-sprint.md цепочку запроса"),
   q="Что происходит по шагам, когда браузер открывает https://site? Где ставится TLS, где балансировка, где приложение?",
   done="коммит за сегодня: конфиг nginx + сертификат + tools/httpcheck.py, который зелёный на https://localhost",
   bonus="разобрать, что нужно для настоящего сертификата Let's Encrypt (домен, 80-й порт, certbot)"),

 dict(day=4, py=dict(
   topic="Упаковка инструмента: модуль, тесты и разбор требований",
   source="https://docs.pytest.org/en/stable/",
   theory="структура модуля, pytest: assert, фикстуры, параметризация; запуск тестов в контейнере.",
   code="tests/test_devcheck.py — 3 теста на свои функции, запуск pytest и вывод 'N passed'"),
   inf=dict(
   topic="Контейнеры и реестр образов: multi-stage, non-root, healthcheck, теги semver, сканирование уязвимостей",
   source="https://docs.docker.com/build/building/multi-stage/",
   task="Собрать образ devcheck: multi-stage, non-root, HEALTHCHECK, .dockerignore; поднять локальный реестр (registry:2) "
        "и запушить тег 0.1.0; проверить состав образа и его размер"),
   q="Чем плох тег latest и как правильно версионировать образы? Что показывает сканер уязвимостей?",
   done="коммит за сегодня: Dockerfile + проходящие тесты + образ 0.1.0 в локальном реестре (docker images | grep registry)",
   bonus="сравнить размер образов python:3.9-slim и python:3.9-alpine и объяснить разницу; разобрать, чем GHCR отличается от локального реестра"),

 dict(day=5, py=dict(
   topic="Генератор манифестов: Python как источник правды для Kubernetes",
   source="https://docs.python.org/3/library/json.html",
   theory="шаблонизация словаря → YAML/JSON, проверка манифеста kubectl --dry-run=client.",
   code="tools/k8sgen.py --image devcheck:0.1.0 --replicas 2 → k8s/deployment.yaml и k8s/service.yaml"),
   inf=dict(
   topic="Kubernetes: архитектура (control plane, etcd, kubelet, scheduler), k3s на этой ВМ, Deployment/ReplicaSet, rollout и rollback",
   source="https://kubernetes.io/ru/docs/concepts/overview/",
   task="Установить/проверить k3s, разобрать kubectl get/describe/logs/scale, задеплоить свой образ из Dockerfile "
        "до 2 реплик, сделать rollout и rollback версии"),
   q="Из каких частей состоит кластер k8s и что произойдёт, если упадёт control plane или один worker? Чем Deployment отличается от Pod?",
   done="коммит за сегодня: k8s/ манифесты; kubectl get pods показывает 2/2 Running твоего образа",
   bonus="прокатить новую версию образа и откатиться через kubectl rollout undo"),

 dict(day=6, py=dict(
   topic="HTTP-сервис на стандартной библиотеке: /health и /metrics",
   source="https://docs.python.org/3/library/http.server.html",
   theory="http.server, маршрутизация по пути, переменные окружения как конфиг, формат метрик Prometheus.",
   code="service/app.py: /health → {'status':'ok'}, /metrics → метрики в формате Prometheus, / → версия и конфиг"),
   inf=dict(
   topic="Сервис, конфиг и секреты в k8s: Service, ConfigMap, Secret, probes, requests/limits, namespace, Ingress",
   source="https://kubernetes.io/docs/concepts/configuration/configmap/",
   task="Выложить сервис с liveness/readiness-probe, конфигом из ConfigMap и паролем из Secret, открыть наружу через "
        "Ingress/NodePort; проверить, что pod переживает удаление (kubectl delete pod)"),
   q="Зачем нужны liveness и readiness пробы по отдельности? Что будет, если пробу поставить неверно?",
   done="коммит за сегодня: манифесты ConfigMap/Secret/Ingress + /health и /metrics отвечают снаружи кластера",
   bonus="поставить заведомо неверную readiness-пробу и объяснить поведение кластера"),

 dict(day=7, py=dict(
   topic="Отчёт о состоянии кластера из скрипта",
   source="https://docs.python.org/3/library/subprocess.html",
   theory="subprocess и разбор JSON-вывода kubectl, обработка ошибок и кодов возврата.",
   code="tools/clustercheck.py → сохраняет отчёт: узлы, поды не в Running, рестарты контейнеров"),
   inf=dict(
   topic="Состояние в k8s и разбор сбоев: Volume/PVC, StatefulSet, Job/CronJob, диагностика CrashLoopBackOff, OOMKilled, ImagePullBackOff",
   source="https://kubernetes.io/docs/concepts/storage/persistent-volumes/",
   task="Подключить PVC к своему сервису, сделать CronJob по расписанию; сломать под (несуществующий образ / лишний лимит памяти) "
        "и разобрать сбой по describe + logs + events, записать разбор в troubleshooting.md"),
   q="С чего начинаешь разбор упавшего пода в k8s? Какие три команды идут первыми и что каждая показывает?",
   done="коммит за сегодня: PVC + CronJob + записанный разбор одного реального сбоя",
   bonus="HPA: настроить автомасштабирование по CPU и посмотреть, как меняется число реплик"),

 dict(day=8, py=dict(
   topic="Пайплайн CI/CD как скрипт: стадии, стоп на первой ошибке, отчёт",
   source="https://docs.python.org/3/library/subprocess.html",
   theory="стадии пайплайна, коды возврата, остановка на ошибке, логирование шагов.",
   code="scripts/ci.py: lint → test → build → push → deploy, остановка на первой красной стадии"),
   inf=dict(
   topic="CI/CD: GitHub Actions (jobs, steps, secrets, cache), локальный прогон пайплайна в Docker, деплой в k3s, откат",
   source="https://docs.github.com/en/actions/get-started/quickstart",
   task="Пайплайн в GitHub Actions: lint → test → build → push образа в GHCR → деплой на ВМ (self-hosted runner или SSH-ключ); "
        "секреты, кэш и условия в workflow; тот же путь — локально через scripts/ci.py; проверить откат при падении стадии"),
   q="Какие стадии обязаны быть в пайплайне перед продом? Что такое 'сборка один раз, деплой везде' и зачем это правило?",
   done="коммит за сегодня: .github/workflows/ci.yml + scripts/ci.py; Actions зелёный и заканчивается новой версией в k3s",
   bonus="добавить в пайплайн smoke-тест после деплоя, который валит пайплайн при 500-й ошибке"),

 dict(day=9, py=dict(
   topic="Свой экспортёр метрик для сервиса",
   source="https://prometheus.io/docs/instrumenting/exposition_formats/",
   theory="типы метрик (counter, gauge, histogram), формат exposition, вычисление перцентилей.",
   code="в сервисе: счётчик запросов, время ответа, счётчик ошибок — и /metrics их отдаёт"),
   inf=dict(
   topic="Мониторинг: Prometheus, node-exporter, PromQL, RED/USE, дашборд Grafana, правило алерта",
   source="https://prometheus.io/docs/introduction/overview/",
   task="Поднять в compose Prometheus + node-exporter + Grafana, настроить сбор метрик своего сервиса и ВМ; "
        "сделать дашборд на 6 панелей; написать запрос rate() и histogram_quantile()"),
   q="Чем SLI отличается от SLO и от метрики? Какие метрики ты бы поставил на сервис в первый день?",
   done="коммит за сегодня: compose-файл мониторинга + dashboard.json; в Grafana видны метрики сервиса и ВМ",
   bonus="правило алерта 'сервис недоступен 2 минуты' и проверка его срабатывания"),

 dict(day=10, py=dict(
   topic="Алертер с антидребезгом: порог держится N минут — шлём один раз",
   source="https://docs.python.org/3/library/smtplib.html",
   theory="состояние между запусками (файл), окно подавления, дедупликация, отправка в мессенджер.",
   code="tools/alerter.py: читает цель, держит состояние в JSON, шлёт уведомление один раз на инцидент"),
   inf=dict(
   topic="Логи, алерты и инцидент: сбор логов (Loki/promtail или journald), структурированные логи, Alertmanager → Telegram, разбор по логам",
   source="https://grafana.com/docs/loki/latest/",
   task="Собрать логи сервиса в одном месте, настроить маршрут алерта в Telegram, убить сервис и разобрать инцидент "
        "по логам; результат — runbook на одну страницу (симптом → проверки → действия)"),
   q="Как по логам отличить проблему приложения от проблемы инфраструктуры? Какие поля обязаны быть в структурированном логе?",
   done="коммит за сегодня: runbook.md + сработавший алерт, зафиксированный в notes",
   bonus="постмортем по учебному инциденту: таймлайн, причина, что меняем"),

 dict(day=11, py=dict(
   topic="Инвентарь из данных: генерация конфигов и проверка идемпотентности",
   source="https://docs.python.org/3/library/string.html",
   theory="данные → конфиг (словарь + шаблон), проверка 'ничего не изменилось' повторным прогоном.",
   code="tools/inventory.py hosts.yml → inventory.ini + diff с предыдущей версией"),
   inf=dict(
   topic="Инфраструктура как код: Ansible (инвентарь, playbook, роли, идемпотентность), Terraform верхнеуровнево (state, plan, apply)",
   source="https://docs.ansible.com/ansible/latest/getting_started/index.html",
   task="Playbook, который настраивает эту ВМ (пакеты + nginx + пользователь): первый прогон changed>0, "
        "второй прогон changed=0; записать в iac-notes.md разницу Ansible и Terraform"),
   q="Что такое идемпотентность и почему без неё IaC бесполезен? Где место Ansible, а где Terraform?",
   done="коммит за сегодня: playbook + вывод второго прогона с changed=0",
   bonus="секреты в Ansible: ansible-vault encrypt строки"),

 dict(day=12, py=dict(
   topic="Бэкап и проверка восстановления скриптом",
   source="https://docs.python.org/3/library/gzip.html",
   theory="дампинг данных, архивы, проверка целостности, автоматическая проверка восстановления.",
   code="tools/backup.py: дамп → архив с датой → проверка читаемости → отчёт в лог"),
   inf=dict(
   topic="Данные и надёжность: PostgreSQL (роли, дамп/восстановление, транзакции), бэкапы 3-2-1, репликация верхнеуровнево",
   source="https://www.postgresql.org/docs/current/backup-dump.html",
   task="Postgres в compose + своя таблица, pg_dump по расписанию, восстановление в чистую базу и сверка числа строк; "
        "записать время восстановления (RTO) в notes"),
   q="Чем бэкап отличается от реплики и почему реплика не заменяет бэкап? Что такое RTO и RPO?",
   done="коммит за сегодня: скрипт бэкапа + лог успешного восстановления с совпавшим числом строк",
   bonus="автопроверка: restore в временную базу + count + алерт при расхождении"),

 dict(day=13, py=dict(
   topic="Аудит сервера скриптом: открытые порты, права, устаревшие версии",
   source="https://docs.python.org/3/library/stat.html",
   theory="чтение прав файлов, разбор вывода команд, формирование отчёта-чеклиста.",
   code="tools/audit.py → отчёт: лишние порты, файлы с правами 777, пользователи с sudo"),
   inf=dict(
   topic="Безопасность эксплуатации: SSH и ключи, sudo, fail2ban, nftables, обновления, секреты в репозитории, least privilege в k8s",
   source="https://www.digitalocean.com/community/tutorials/how-to-set-up-a-firewall-using-iptables-on-ubuntu-14-04",
   task="Прогнать аудит: закрыть минимум две находки (например, лишний порт, права файла, секрет в репозитории); "
        "описать принцип наименьших привилегий на примере своего пода/пользователя"),
   q="Что ты проверяешь в первую очередь, приходя на незнакомый сервер? Какие три настройки безопасности самые важные?",
   done="коммит за сегодня: отчёт аудита + две закрытые находки",
   bonus="securityContext и отдельный serviceAccount для своего пода с правами только на get/list pods"),

 dict(day=14, py=dict(
   topic="Сборка таймлайна инцидента из данных",
   source="https://docs.python.org/3/library/datetime.html",
   theory="работа со временем, сортировка событий, генерация markdown-отчёта.",
   code="tools/timeline.py events.json → markdown-таймлайн 'время — событие — вывод'"),
   inf=dict(
   topic="SRE-практики: SLI/SLO/error budget, дежурства и on-call, severity-модель, учения и постмортем (связка с моей работой инцидент-менеджера)",
   source="https://sre.google/sre-book/service-level-objectives/",
   task="Провести учебный инцидент от начала до конца: имитировать отказ сервиса, снять метрики и логи, "
        "провести разбор по таймлайну, написать постмортем (влияние, причина, что меняем, кто отвечает)"),
   q="Как error budget меняет решения о релизах? Кто и зачем пишет постмортем без поиска виноватых?",
   done="коммит за сегодня: постмортем учебного инцидента с таймлайном и тремя действиями",
   bonus="SLO 99% и расчёт допустимого простоя/ошибок на 30 дней"),

 dict(day=15, py=dict(
   topic="Инвентарь облака и расчёт стоимости",
   source="https://docs.python.org/3/library/decimal.html",
   theory="модель инфраструктуры как данные, расчёт стоимости, сравнение вариантов.",
   code="tools/cloudcost.py infra.json prices.json → стоимость в месяц по компонентам"),
   inf=dict(
   topic="Облако Cloud.ru изнутри: IaaS/PaaS, ВМ и образы, диски, сети и балансировщики, managed k8s, объектное хранилище, квоты и экономика",
   source="https://cloud.ru/docs",
   task="Нарисовать свою инфраструктуру блок-схемой (diagram.md), сформулировать 10 отличий IaaS/PaaS/SaaS своими словами, "
        "выписать, что даёт облако предприятию и какие у этого риски (зависимость, цена, безопасность)"),
   q="Что бы ты вынес в managed-сервис, а что оставил на своей ВМ, если бы экономил бюджет? Почему?",
   done="коммит за сегодня: diagram.md + 10 отличий + расчёт стоимости своей ВМ на месяц",
   bonus="посчитать, как меняется стоимость при 8 ГБ/40 ГБ и при отказе от ВМ в пользу managed k8s"),

 dict(day=16, py=dict(
   topic="Финальная сборка: отчёт о состоянии проекта генерируется скриптом",
   source="https://docs.python.org/3/library/os.html",
   theory="сбор фактов о системе (версии, состояние сервисов, метрики) в один отчёт, README-раздел 'как запустить'.",
   code="tools/report.py → отчёт: версии, состояние подов, метрики, последние коммиты"),
   inf=dict(
   topic="Итог спринта: сквозная демонстрация пайплайна и подготовка питча на стажировку",
   source="https://kubernetes.io/ru/docs/tutorials/",
   task="Прогнать сквозной сценарий: коммит → CI → образ → деплой в k3s → метрики в Grafana. README с архитектурой "
        "(схема + почему так). Питч на 3 минуты: что умею, что делал в инцидентах, что готов делать на стажировке. "
        "20 вопросов стажировки DevOps с короткими ответами — в interview-notes.md"),
   q="Расскажи за 3 минуты инженеру: что ты построил за две недели и почему это сделано именно так?",
   done="коммит за сегодня: README с архитектурной схемой + питч + 20 вопросов с ответами",
   bonus="прогнать питч вслух под таймер 3 минуты и записать, что сбилось"),
]

# ------------------------------------------------------------ упражнения рук
DRILLS = {
 "1": dict(task="Функция pct(used, total) → процент с одним знаком ('42.3') и is_over(value, limit) → True/False. "
                "Применить к free -m: посчитать процент занятой памяти.",
            expect="pct(1500, 3900) → '38.5';  is_over(38.5, 90) → False",
            solution="def pct(used, total):\n    return str(round(used * 100.0 / total, 1))\n\n\ndef is_over(value, limit):\n    return float(value) > float(limit)\n\n\nprint(pct(1500, 3900), is_over(38.5, 90))"),
 "2": dict(task="Функция top_messages(lines, n=3) → список кортежей (сообщение, сколько раз). Использовать Counter.",
            expect="top_messages(['a','b','a']) → [('a', 2), ('b', 1)]",
            solution="from collections import Counter\n\n\ndef top_messages(lines, n=3):\n    return Counter(lines).most_common(n)\n\n\nprint(top_messages(['a', 'b', 'a']))"),
 "3": dict(task="Функция timed(url) → (код ответа, миллисекунды) через urllib с таймаутом 5 секунд. Ошибку возвращать как (None, -1).",
            expect="timed('https://example.org') → (200, 137)",
            solution="import time\nimport urllib.request\n\n\ndef timed(url):\n    start = time.time()\n    try:\n        with urllib.request.urlopen(url, timeout=5) as r:\n            return r.status, int((time.time() - start) * 1000)\n    except Exception:\n        return None, -1\n\n\nprint(timed('https://example.org'))"),
 "4": dict(task="Функции image_tag(version, name='app') → 'app:1.2.3' и is_semver(s) → True/False по шаблону X.Y.Z.",
            expect="image_tag('1.2.3') → 'app:1.2.3';  is_semver('1.2') → False",
            solution="import re\n\n\ndef image_tag(version, name='app'):\n    return '%s:%s' % (name, version)\n\n\ndef is_semver(s):\n    return bool(re.match(r'^\\d+\\.\\d+\\.\\d+$', s))\n\n\nprint(image_tag('1.2.3'), is_semver('1.2'))"),
 "5": dict(task="Функция manifest_kind(text) → кортеж (kind, name) из простого YAML-манифеста (строки 'kind: Deployment', '  name: app').",
            expect="manifest_kind('kind: Deployment\\n  name: app') → ('Deployment', 'app')",
            solution="import re\n\n\ndef manifest_kind(text):\n    kind = re.search(r'^kind:\\s*(\\S+)', text, re.M)\n    name = re.search(r'^\\s+name:\\s*(\\S+)', text, re.M)\n    return (kind.group(1) if kind else None, name.group(1) if name else None)\n\n\nprint(manifest_kind('kind: Deployment\\n  name: app'))"),
 "6": dict(task="Функция parse_env(text) → словарь KEY=VALUE из строк, игнорируя пустые строки и комментарии с #.",
            expect="parse_env('A=1\\n# ком\\nB=2') → {'A': '1', 'B': '2'}",
            solution="def parse_env(text):\n    out = {}\n    for line in text.splitlines():\n        line = line.strip()\n        if not line or line.startswith('#'):\n            continue\n        if '=' in line:\n            k, v = line.split('=', 1)\n            out[k] = v\n    return out\n\n\nprint(parse_env('A=1\\n# ком\\nB=2'))"),
 "7": dict(task="Функции parse_size('10Gi') → байты (Gi=1024**3, Mi=1024**2) и fmt_size(байты) → '10Gi'.",
            expect="parse_size('10Gi') → 10737418240;  fmt_size(10737418240) → '10Gi'",
            solution="UNITS = {'Ki': 1024, 'Mi': 1024 ** 2, 'Gi': 1024 ** 3}\n\n\ndef parse_size(text):\n    for unit, mult in UNITS.items():\n        if text.endswith(unit):\n            return int(float(text[:-len(unit)]) * mult)\n    return int(text)\n\n\ndef fmt_size(num):\n    for unit, mult in sorted(UNITS.items(), key=lambda x: -x[1]):\n        if num >= mult and num % mult == 0:\n            return '%d%s' % (num // mult, unit)\n    return str(num)\n\n\nprint(parse_size('10Gi'), fmt_size(10737418240))"),
 "8": dict(task="Функция pipeline(stages) → список пройденных стадий и остановка на первой False; вернуть (ok, пройдено, упавшая).",
            expect="pipeline([('lint', True), ('test', False), ('build', True)]) → (False, ['lint'], 'test')",
            solution="def pipeline(stages):\n    passed = []\n    for name, ok in stages:\n        if not ok:\n            return False, passed, name\n        passed.append(name)\n    return True, passed, None\n\n\nprint(pipeline([('lint', True), ('test', False), ('build', True)]))"),
 "9": dict(task="Функция percentile(values, q) → q-й перцентиль (метод 'ближайшего ранга'). Применить к временам ответа.",
            expect="percentile([10, 20, 30, 40, 100], 95) → 100;  percentile([10, 20], 50) → 10",
            solution="import math\n\n\ndef percentile(values, q):\n    if not values:\n        return None\n    data = sorted(values)\n    k = int(math.ceil(q / 100.0 * len(data))) - 1\n    return data[max(0, k)]\n\n\nprint(percentile([10, 20, 30, 40, 100], 95), percentile([10, 20], 50))"),
 "10": dict(task="Функция alert_state(value, threshold, since_ts, now_ts, window=120) → 'firing', 'pending' или 'ok' (антидребезг: условие держится дольше окна).",
            expect="alert_state(95, 90, 1000, 1100) → 'pending';  alert_state(95, 90, 1000, 1130) → 'firing';  alert_state(80, 90, 1000, 1130) → 'ok'",
            solution="def alert_state(value, threshold, since_ts, now_ts, window=120):\n    if value <= threshold:\n        return 'ok'\n    return 'firing' if now_ts - since_ts >= window else 'pending'\n\n\nprint(alert_state(95, 90, 1000, 1100), alert_state(95, 90, 1000, 1130), alert_state(80, 90, 1000, 1130))"),
 "11": dict(task="Функция inventory_ini(hosts) → текст ini-инвентаря для Ansible: группа [web] и строки 'имя ansible_host=ip'.",
            expect="inventory_ini({'web': [{'name': 'vm1', 'ip': '10.0.0.1'}]}) содержит '[web]' и 'vm1 ansible_host=10.0.0.1'",
            solution="def inventory_ini(hosts):\n    lines = []\n    for group, items in hosts.items():\n        lines.append('[%s]' % group)\n        for h in items:\n            lines.append('%s ansible_host=%s' % (h['name'], h['ip']))\n        lines.append('')\n    return '\\n'.join(lines)\n\n\nprint(inventory_ini({'web': [{'name': 'vm1', 'ip': '10.0.0.1'}]}))"),
 "12": dict(task="Функции backup_name(dt) → 'db-2026-10-14.sql.gz' из datetime и check_restore(expected, actual) → 'ok' или 'lost N rows'.",
            expect="backup_name(datetime(2026, 10, 14)) → 'db-2026-10-14.sql.gz';  check_restore(100, 97) → 'lost 3 rows'",
            solution="from datetime import datetime\n\n\ndef backup_name(dt):\n    return 'db-%s.sql.gz' % dt.strftime('%Y-%m-%d')\n\n\ndef check_restore(expected, actual):\n    if expected == actual:\n        return 'ok'\n    return 'lost %d rows' % (expected - actual)\n\n\nprint(backup_name(datetime(2026, 10, 14)), check_restore(100, 97))"),
 "13": dict(task="Функция extra_ports(opened, allowed) → отсортированный список лишних открытых портов.",
            expect="extra_ports([22, 80, 5432, 9001], [22, 80, 443]) → [5432, 9001]",
            solution="def extra_ports(opened, allowed):\n    return sorted(set(opened) - set(allowed))\n\n\nprint(extra_ports([22, 80, 5432, 9001], [22, 80, 443]))"),
 "14": dict(task="Функция timeline(events) → markdown-строки 'HH:MM — событие', отсортированные по времени. events — список (iso_время, текст).",
            expect="timeline([('2026-10-16T10:05:00', 'рост ошибок'), ('2026-10-16T10:01:00', 'деплой')]) → первая строка '10:01 — деплой'",
            solution="def timeline(events):\n    rows = sorted(events, key=lambda e: e[0])\n    return '\\n'.join('- %s — %s' % (e[0][11:16], e[1]) for e in rows)\n\n\nprint(timeline([('2026-10-16T10:05:00', 'рост ошибок'), ('2026-10-16T10:01:00', 'деплой')]))"),
 "15": dict(task="Функция cost_month(vcpu, ram_gb, disk_gb, price) → стоимость в месяц с округлением до копеек. price — словарь цен за единицу.",
            expect="cost_month(2, 4, 15, {'vcpu': 300, 'ram_gb': 150, 'disk_gb': 10}) → '3750.00'",
            solution="from decimal import Decimal, ROUND_HALF_UP\n\n\ndef cost_month(vcpu, ram_gb, disk_gb, price):\n    total = (vcpu * price.get('vcpu', 0) + ram_gb * price.get('ram_gb', 0)\n             + disk_gb * price.get('disk_gb', 0))\n    d = Decimal(str(total)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)\n    return str(d)\n\n\nprint(cost_month(2, 4, 15, {'vcpu': 300, 'ram_gb': 150, 'disk_gb': 10}))"),
 "16": dict(task="Функция summary(checks) → markdown-таблица 'проверка | результат' из словаря, с ✅/❌ по булеву значению.",
            expect="summary({'тесты': True, 'метрики': False}) содержит '| тесты | ✅ |'",
            solution="def summary(checks):\n    lines = ['| проверка | результат |', '| --- | --- |']\n    for name, ok in checks.items():\n        lines.append('| %s | %s |' % (name, '✅' if ok else '❌'))\n    return '\\n'.join(lines)\n\n\nprint(summary({'тесты': True, 'метрики': False}))"),
}

def main():
    days = []
    for d in DAYS:
        dd = dict(d)
        dd["week"] = ((dd["day"] - 1) // 7) + 1
        dd["python"] = dd.pop("py")
        dd["infra"] = dd.pop("inf")
        dd["question"] = dd.pop("q")
        dd["done_criteria"] = dd.pop("done")
        days.append(dd)
    plan = {
        "title": "DevOps-спринт: подготовка к стажировке (ускоренный курс)",
        "start_date": START,
        "end_date": END,
        "minutes_total": MINUTES_TOTAL,
        "minutes_split": SPLIT,
        "drill_minutes": DRILL_MINUTES,
        "days": days,
    }
    with open(os.path.join(ROOT, "plan.json"), "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=1)
    with open(os.path.join(ROOT, "drills.json"), "w", encoding="utf-8") as f:
        json.dump(DRILLS, f, ensure_ascii=False, indent=1)
    print("plan.json: %d дней (%s → %s)" % (len(days), START, END))
    print("drills.json: %d упражнений" % len(DRILLS))

if __name__ == "__main__":
    main()
