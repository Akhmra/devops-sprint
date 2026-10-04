#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Движок плана обучения (две дорожки: автоматизация на Python + инфраструктура/DevOps).

Спринт-редакция: тот же движок, что в ~/ai-roadmap, но план — 16-дневный DevOps-спринт
(подготовка к стажировке, 3–18 октября 2026, 150 минут в день).

Режимы:
  brief   — утренний брифинг (что делать сегодня)
  ping    — короткое напоминание вечером
  check   — проверка по коммитам: зачесть день или напомнить
  done    — зачесть день вручную
  mini    — зачесть «минимальный день» (15 минут, день не продвигается)
  drill   — упражнение дня (с эталоном, сверять после своей попытки)
  status  — состояние: день, серия, история
  weekly  — сводка для недельного отчёта
  finish  — итог спринта и порядок возврата к 84-дневному плану

Данные: plan.json (задания), state.json (прогресс). Переменные: AI_ROADMAP_DIR (папка git,
по умолчанию — папка скрипта).
"""
import json, os, subprocess, sys
from datetime import date, datetime, timedelta

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("AI_ROADMAP_DIR", ROOT)


def _load(name, default):
    p = os.path.join(ROOT, name)
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def load_plan():
    return _load("plan.json", {"days": []})


def load_drill(day):
    """Упражнение дня из drills.json (для механической отработки кода)."""
    d = _load("drills.json", {})
    return d.get(str(day)) or {}


def load_state():
    st = _load("state.json", None)
    if st is None:
        st = {"current_day": 1, "streak": 0, "best_streak": 0, "last_credited": None,
              "history": [], "mini_count": 0,
              "started": load_plan().get("start_date", date.today().isoformat())}
        save_state(st)
    return st


def save_state(st):
    with open(os.path.join(ROOT, "state.json"), "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)


def today_str():
    return date.today().isoformat()


def plural(n, one="день", few="дня", many="дней"):
    n = int(n)
    if n % 10 == 1 and n % 100 != 11:
        return "%d %s" % (n, one)
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return "%d %s" % (n, few)
    return "%d %s" % (n, many)


def day_entry(plan, n):
    for d in plan["days"]:
        if d["day"] == n:
            return d
    return plan["days"][-1] if plan["days"] else None


INTRO_BLOCK = ("🎬 ВВОДНОЕ ЗАНЯТИЕ — 30 минут (лёгкий вход, ещё не закрыто)\n"
              "Шаги: INTRO-DAY.md в папке курса\n\n"
              "1) 5 мин — осмотреть папку проекта (ls -la, README)\n"
              "2) 7 мин — 6 команд терминала → intro-notes.md\n"
              "3) 10 мин — первый Python: hello.py\n"
              "4) 5 мин — ответ на вопрос дня в intro-notes.md\n"
              "5) 3 мин — коммит: git add -A && git commit -m \"intro: вводное занятие\"\n\n"
              "✅ Зачёт: коммит за сегодня (вечерняя проверка зачтёт сама).\n"
              "Завтра — день 1: %s")


def theme_of(d):
    if not d:
        return "—"
    py = (d.get("python") or {}).get("topic", "—")
    inf = (d.get("infra") or {}).get("topic", "—")
    return "Python: %s | Инфра: %s" % (py, inf)


def git(args):
    try:
        out = subprocess.run(["git", "-C", REPO] + args, capture_output=True, text=True, timeout=15)
        return out.stdout.strip()
    except Exception:
        return ""


def commits_today():
    """Коммиты пользователя за сегодня. Служебные (subject начинается с 'system:') не считаются."""
    out = git(["log", "--since=%s 00:00" % today_str(), "--pretty=%h|%ad|%s", "--date=format:%H:%M"])
    if not out:
        return 0, None
    rows = []
    for line in out.splitlines():
        parts = line.split("|", 2)
        if len(parts) < 3:
            continue
        if parts[2].strip().lower().startswith("system:"):
            continue
        rows.append(parts)
    return len(rows), (rows[0][1] if rows else None)


def uncommitted_today():
    out = git(["status", "--porcelain"])
    return len([l for l in out.splitlines() if l.strip()]) if out else 0


def days_missed(st):
    """Сколько ПОЛНЫХ дней подряд остались незачёными (сегодняшний день не считается)."""
    ref = st.get("last_credited") or st.get("started") or today_str()
    try:
        d0 = datetime.strptime(ref, "%Y-%m-%d").date()
    except Exception:
        return 0
    delta = (date.today() - d0).days
    return max(0, delta - 1 if st.get("last_credited") else delta)


def credit(st, status="done"):
    t = today_str()
    if st.get("last_credited") == t:
        return False
    st["streak"] = int(st.get("streak", 0)) + 1
    st["best_streak"] = max(int(st.get("best_streak", 0)), st["streak"])
    st["last_credited"] = t
    st["history"] = (st.get("history") or [])[-180:] + [{"date": t, "day": st.get("current_day", 1), "status": status}]
    if status == "done":
        st["current_day"] = int(st.get("current_day", 1)) + 1
    elif status == "intro":
        st["intro_pending"] = False
    else:
        st["mini_count"] = int(st.get("mini_count", 0)) + 1
    save_state(st)
    return True


def header(plan, st, d):
    end = plan.get("end_date")
    tail = ""
    if end:
        try:
            left = (datetime.strptime(end, "%Y-%m-%d").date() - date.today()).days
            tail = "\n⏳ Спринт до %s — осталось %s" % (end, plural(max(left, 0), "день", "дня", "дней"))
        except Exception:
            tail = ""
    return ("🎯 День %d из %d · неделя %d · серия: %s\n📌 %s%s" % (
        d["day"], len(plan["days"]), d["week"], plural(st.get("streak", 0)), theme_of(d), tail))


def brief(plan, st):
    start = st.get("started") or plan.get("start_date")
    if st.get("intro_pending"):
        return INTRO_BLOCK % theme_of(day_entry(plan, 1))
    if start and today_str() < start:
        d1 = day_entry(plan, 1)
        return ("⏳ Старт %s. День 1 — %s.\nСегодня можно только одно: прочитать план и открыть папку %s."
                % (start, theme_of(d1), ROOT))
    d = day_entry(plan, st.get("current_day", 1))
    if not d:
        return "План пуст — проверь plan.json"
    sp = plan.get("minutes_split", {})
    dr = load_drill(d["day"])
    py, inf = d.get("python", {}), d.get("infra", {})
    lines = [
        header(plan, st, d), "",
        "⏱ Сегодня %d минут: %d Python + %d инфраструктура + %d конспект" % (
            plan.get("minutes_total", 60), sp.get("python", 25), sp.get("infra", 25), sp.get("notes", 10)), "",
        "🐍 PYTHON (%d мин) — %s" % (sp.get("python", 25), py.get("topic", "—")),
        "   📚 %s" % py.get("source", ""),
        "   • теория: %s" % py.get("theory", ""),
        "   • код: %s" % py.get("code", ""), "",
        "🛠 ИНФРАСТРУКТУРА (%d мин) — %s" % (sp.get("infra", 25), inf.get("topic", "—")),
        "   📚 %s" % inf.get("source", ""),
        "   • задача: %s" % inf.get("task", ""), "",
        "✍️ ПРАКТИКА КОДА (%d мин, писать руками, не копипастом):" % plan.get("drill_minutes", 15),
        "   • %s" % (dr.get("task", "—")),
        "   • ожидаемый результат: %s" % dr.get("expect", "—"),
        "   • сверить себя: python3 today.py drill",
        "",
        "🎤 ВОПРОС ДНЯ (ответ своими словами в interview-notes.md):",
        "   • %s" % d.get("question", ""), "",
        "✅ ГОТОВО, ЕСЛИ: %s" % d.get("done_criteria", ""),
    ]
    if d.get("bonus"):
        lines.append("⚡ Есть силы? +15 минут: %s" % d["bonus"])
    lines.append("🧱 Летит день? Минимум 15 минут и один коммит — напиши «мини».")
    if days_missed(st) >= 2:
        lines += ["", "⚠️ Два дня без зачёта. Включаем микро-режим: 15 минут в день, пока серия не вернётся."]
    return "\n".join(lines)


def ping(plan, st):
    d = day_entry(plan, st.get("current_day", 1))
    if not d:
        return "План пуст"
    start = st.get("started") or plan.get("start_date")
    if st.get("last_credited") == today_str():
        return "⏰ Учебный день уже закрыт ✅ Серия: %s. Завтра утром — новый день." % plural(st.get("streak", 0))
    if st.get("intro_pending"):
        return ("⏰ Вводное занятие (30 минут, лёгкое): терминал + первый скрипт. "
                "Открой папку курса, файл INTRO-DAY.md — там 5 шагов. Коммит = день закрыт.")
    if start and today_str() < start:
        return "⏰ План стартует %s. День 1 — %s." % (start, theme_of(day_entry(plan, 1)))
    py, inf = d.get("python", {}), d.get("infra", {})
    return ("⏰ День пока не закрыт — время заниматься. День %d · серия: %s\n"
            "🐍 Python: %s\n   • %s\n"
            "🛠 Инфра: %s\n   • %s\n"
            "✅ Критерий: %s\n"
            "Минимум — 15 минут и коммит." % (
                d["day"], plural(st.get("streak", 0)), py.get("topic", "—"), py.get("code", ""),
                inf.get("topic", "—"), inf.get("task", ""), d.get("done_criteria", "")))


def check(plan, st):
    n, t = commits_today()
    dirty = uncommitted_today()
    d = day_entry(plan, st.get("current_day", 1))
    start = st.get("started") or plan.get("start_date")
    hist = st.get("history") or []
    was_intro = (hist[-1].get("status") == "intro") if hist else False
    if st.get("last_credited") == today_str():
        if was_intro:
            return ("🔎 Проверка дня. Вводное занятие зачтено ✅ (коммитов за сегодня: %d)\n"
                    "Серия: %s (рекорд: %s). Завтра утром — день 1: %s." % (
                        n, plural(st.get("streak", 0)), plural(st.get("best_streak", 0)), theme_of(d)))
        return ("🔎 Проверка дня. Коммит(ы) за сегодня: %d ✅\nДень %d уже зачтён. Серия: %s (рекорд: %s).\n"
                "Завтра: день %d — %s." % (n, st.get("current_day", 1) - 1, plural(st.get("streak", 0)),
                                           plural(st.get("best_streak", 0)), st.get("current_day", 1),
                                           theme_of(day_entry(plan, st.get("current_day", 1)))))
    if st.get("intro_pending") and n > 0:
        credit(st, "intro")
        return ("🔎 Проверка дня. Коммитов за сегодня: %d (последний в %s) ✅\n"
                "Вводное занятие зачтено! Серия: %s. Завтра утром — день 1: %s." % (
                    n, t or "—", plural(st.get("streak", 0)), theme_of(d)))
    if st.get("intro_pending"):
        return ("🔎 Проверка дня. Коммитов за сегодня: 0 ❌\n"
                "Вводное занятие ещё не закрыто. Минимум: файл hello.py и один коммит — зачту сразу.\n"
                "Серия пока: %s." % plural(st.get("streak", 0)))
    if start and today_str() < start:
        return ("🔎 Проверка дня. План стартует %s, сегодня коммиты не считаю.\nПервый день — %s."
                % (start, theme_of(day_entry(plan, 1))))
    if n > 0:
        credit(st, "done")
        return ("🔎 Проверка дня. Коммитов за сегодня: %d (последний в %s) ✅\n"
                "День %d зачтён автоматически. Серия: %s (рекорд: %s).\nЗавтра: день %d — %s." % (
                    n, t or "—", st.get("current_day", 1) - 1, plural(st.get("streak", 0)),
                    plural(st.get("best_streak", 0)), st.get("current_day", 1),
                    theme_of(day_entry(plan, st.get("current_day", 1)))))
    msg = ["🔎 Проверка дня. Коммитов за сегодня: 0 ❌"]
    if dirty:
        msg.append("Но в репозитории есть несохранённые изменения (%d). Если работали — закоммитьте, и день зачтётся сам." % dirty)
    if d:
        msg += ["", "Не закрыт день %d (%s)" % (d["day"], theme_of(d)),
                "✅ Критерий: %s" % d.get("done_criteria", ""), "",
                "Ещё есть время: минимум 15 минут и один коммит. Напишите «мини» — зачту как спасательный день."]
    missed = days_missed(st)
    if missed >= 2:
        msg += ["", "⚠️ Уже %d полных %s подряд без зачёта. Переходим в микро-режим: 15 минут в день, "
                    "только чтобы не рвать цепочку." % (missed, plural(missed, "день", "дня", "дней"))]
    msg.append("Серия: %s (рекорд: %s)." % (plural(st.get("streak", 0)), plural(st.get("best_streak", 0))))
    return "\n".join(msg)


def status(plan, st):
    hist = st.get("history") or []
    last7 = [h for h in hist if h["date"] >= (date.today() - timedelta(days=7)).isoformat()]
    return ("📊 Состояние: день %d из %d, серия %s, рекорд %s\nЗачётов за 7 дней: %d\nПоследние зачёты: %s\n"
            "Мини-дней всего: %d\nТекущая тема: %s" % (
                st.get("current_day", 1), len(plan["days"]), plural(st.get("streak", 0)),
                plural(st.get("best_streak", 0)), len(last7),
                ", ".join("%s(%s)" % (h["date"][5:], h["status"]) for h in hist[-5:]) or "нет",
                st.get("mini_count", 0), theme_of(day_entry(plan, st.get("current_day", 1)))))


def weekly(plan, st):
    hist = st.get("history") or []
    last7 = [h for h in hist if h["date"] >= (date.today() - timedelta(days=7)).isoformat()]
    lines = ["Данные для недельного отчёта (сформированы автоматически):",
             "дата: %s" % today_str(),
             "текущий день плана: %d из %d" % (st.get("current_day", 1), len(plan["days"])),
             "серия: %d, рекорд: %d, мини-дней: %d" % (st.get("streak", 0), st.get("best_streak", 0), st.get("mini_count", 0)),
             "зачётов за 7 дней: %d из 7" % len(last7),
             "даты зачётов: %s" % (", ".join(h["date"] for h in last7) or "нет"),
             "следующий день: %s" % theme_of(day_entry(plan, st.get("current_day", 1))),
             "последние зачёты: %s" % (", ".join("%s(%s)" % (h["date"], h["status"]) for h in hist[-7:]) or "нет"),
             "всего зачётов: %d" % len(hist)]
    if len(last7) < 4:
        lines.append("ВЫВОД: менее 4 зачётов за неделю — нагрузка не держится, надо упростить план (15 минут/день, только одна дорожка).")
    return "\n".join(lines)


def finish(plan, st):
    """Итог спринта и порядок возврата к основному 84-дневному плану."""
    hist = st.get("history") or []
    start = plan.get("start_date")
    end = plan.get("end_date")
    in_sprint = [h for h in hist if start and end and start <= h["date"] <= end]
    done = [h for h in in_sprint if h.get("status") == "done"]
    days = len(plan["days"])
    left = max(0, int(st.get("current_day", 1)) - 1)
    lines = [
        "🏁 ИТОГ DEVOPS-СПРИНТА (%s → %s)" % (start, end),
        "Закрыто дней: %d из %d" % (len(done), days),
        "Зачётов за спринт: %d (в т.ч. мини: %d)" % (
            len(in_sprint), len([h for h in in_sprint if h.get("status") == "mini"])),
        "Серия: %s, рекорд: %s" % (plural(st.get("streak", 0)), plural(st.get("best_streak", 0))),
        "Первый незакрытый день спринта: %d" % st.get("current_day", 1),
        "",
        "Что должно быть в ~/devops-sprint: README с архитектурой, k8s/ манифесты, .github/workflows,",
        "мониторинг (compose + dashboard.json), runbook.md, постмортем, interview-notes.md с питчем.",
        "",
        "Возврат к основному плану: 19 октября движок сам переключится на ~/ai-roadmap",
        "(день %d — аннотации типов и mypy + реестр образов), серия переносится автоматически." % 17,
    ]
    if left:
        lines += ["", "⚠️ Незакрытых дней спринта: %d. Пропущенное не догоняется: это очередь, "
                      "а не календарь — при возврате 19.10 основной план остаётся днём 17." % left]
    return "\n".join(lines)


def main():
    mode = (sys.argv[1] if len(sys.argv) > 1 else "brief").strip().lower()
    plan, st = load_plan(), load_state()
    if mode == "brief":
        print(brief(plan, st))
    elif mode == "ping":
        print(ping(plan, st))
    elif mode == "check":
        print(check(plan, st))
    elif mode == "done":
        ok = credit(st, "done")
        print("✅ День зачтён. Серия: %s (рекорд: %s). Завтра: день %d." % (
            plural(st["streak"]), plural(st["best_streak"]), st.get("current_day", 1)) if ok
            else "Сегодня уже зачтено — второй раз не считается.")
    elif mode == "intro":
        print("🎬 ВВОДНОЕ ЗАНЯТИЕ — 30 минут, сегодня\n"
              "Шаги: ~/ai-roadmap/INTRO-DAY.md\n\n"
              "1) 5 мин — осмотреть папку проекта (ls -la, README)\n"
              "2) 7 мин — 6 команд терминала, записать в intro-notes.md\n"
              "3) 10 мин — первый Python: hello.py и запуск\n"
              "4) 5 мин — ответить на вопрос дня в intro-notes.md\n"
              "5) 3 мин — git add -A && git commit -m \"intro: вводное занятие\"\n\n"
              "✅ Зачёт: коммит за сегодня. Проверка в 22:30 зачтёт автоматически.\n"
              "Завтра утром — день 1: %s" % theme_of(day_entry(plan, 1)))
    elif mode in ("intro-done", "intro_done"):
        ok = credit(st, "intro")
        st["intro_pending"] = False
        save_state(st)
        print("✅ Вводное занятие зачтено. Серия: %s. Завтра утром — день 1: %s" % (
            plural(st["streak"]), theme_of(day_entry(plan, 1))) if ok else "Сегодня уже зачтено.")
    elif mode == "mini":
        ok = credit(st, "mini")
        print("🛟 Мини-день зачтён (15 минут, серия: %s). День %d не продвинулся — вернёшься к нему завтра." % (
            plural(st["streak"]), st.get("current_day", 1)) if ok else "Сегодня уже зачтено.")
    elif mode == "drill":
        day = int(sys.argv[2]) if len(sys.argv) > 2 else st.get("current_day", 1)
        dr = load_drill(day)
        if not dr:
            print("Для дня %d упражнение не найдено." % day)
        else:
            print("✍️ ПРАКТИКА ДНЯ %d — напиши код сам, потом сверь\n" % day)
            print("Задание: %s" % dr.get("task", ""))
            print("Ожидаемо: %s\n" % dr.get("expect", ""))
            print("--- ЭТАЛОН (сверять ПОСЛЕ своей попытки) ---")
            print(dr.get("solution", ""))
    elif mode == "status":
        print(status(plan, st))
    elif mode == "weekly":
        print(weekly(plan, st))
    elif mode in ("finish", "итог"):
        print(finish(plan, st))
    else:
        print("Режимы: brief | ping | check | done | mini | drill | status | weekly | finish")


if __name__ == "__main__":
    main()
