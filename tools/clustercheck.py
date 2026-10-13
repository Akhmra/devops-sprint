#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class KubectlNotFoundError(Exception):
    pass


class KubectlCommandError(Exception):
    def __init__(self, cmd: List[str], returncode: int, stderr: str):
        self.cmd = cmd
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(f"Command '{' '.join(cmd)}' failed with code {returncode}: {stderr.strip()}")


def run_kubectl(args: List[str]) -> str:
    """Выполняет kubectl и возвращает stdout. 
    Генерирует исключения вместо трейса при ошибках."""
    try:
        result = subprocess.run(
            ["kubectl"] + args,
            capture_output=True,
            text=True,
            check=False
        )
    except FileNotFoundError:
        print("kubectl не найден в PATH", file=sys.stderr)
        sys.exit(1)

    if result.returncode != 0:
        raise KubectlCommandError(["kubectl"] + args, result.returncode, result.stderr)
    
    return result.stdout


def parse_nodes(json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Извлекает имя узла и его статус Ready."""
    nodes = []
    for item in json_data.get("items", []):
        name = item.get("metadata", {}).get("name", "unknown")
        ready_status = "Unknown"
        for condition in item.get("status", {}).get("conditions", []):
            if condition.get("type") == "Ready":
                ready_status = "True" if condition.get("status") == "True" else "False"
                break
        nodes.append({"name": name, "ready": ready_status})
    return nodes


def parse_pods(json_data: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], int]:
    """Ищет проблемные поды и суммирует рестарты.
    Проблемный под: фаза не Running/Succeeded ИЛИ есть рестарты контейнеров."""
    problematic = []
    total_restarts = 0

    for item in json_data.get("items", []):
        ns = item.get("metadata", {}).get("namespace", "unknown")
        name = item.get("metadata", {}).get("name", "unknown")
        phase = item.get("status", {}).get("phase", "Unknown")
        
        # Считаем суммарные рестарты всех контейнеров
        restarts = sum(
            cs.get("restartCount", 0) 
            for cs in item.get("status", {}).get("containerStatuses", [])
        )
        total_restarts += restarts

        # Проверяем условия проблемности
        if phase not in ["Running", "Succeeded"] or restarts > 0:
            problematic.append({
                "namespace": ns,
                "name": name,
                "phase": phase,
                "restarts": restarts
            })

    return problematic, total_restarts


def generate_text_report(nodes: List[Dict[str, Any]], 
                         pods: List[Dict[str, Any]], 
                         total_restarts: int) -> str:
    """Формирует человекочитаемый текстовый отчёт."""
    lines = []
    lines.append("=== Отчёт по кластеру ===\n")
    
    lines.append("Узлы:")
    for n in nodes:
        lines.append(f"  - {n['name']}: Ready={n['ready']}")
    lines.append("")

    lines.append("Проблемные поды:")
    if not pods:
        lines.append("  (нет)")
    else:
        for p in pods:
            lines.append(f"  - {p['namespace']}/{p['name']}: Phase={p['phase']}, Restarts={p['restarts']}")
    lines.append("")

    lines.append(f"Итог: узлов={len(nodes)}, проблемных подов={len(pods)}, суммарных рестартов={total_restarts}")
    return "\n".join(lines)


def generate_json_report(nodes: List[Dict[str, Any]], 
                         pods: List[Dict[str, Any]], 
                         total_restarts: int) -> str:
    """Формирует отчёт в формате JSON."""
    report = {
        "nodes": nodes,
        "problematic_pods": pods,
        "summary": {
            "total_nodes": len(nodes),
            "problematic_pods_count": len(pods),
            "total_restarts": total_restarts
        }
    }
    return json.dumps(report, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Отчёт по состоянию узлов и подов Kubernetes")
    parser.add_argument("--json", action="store_true", help="Вывести отчёт в JSON вместо текста")
    parser.add_argument("--out", type=str, help="Записать отчёт в файл (иначе в stdout)")
    
    args = parser.parse_args()

    try:
        nodes_json = run_kubectl(["get", "nodes", "-o", "json"])
        pods_json = run_kubectl(["get", "pods", "-A", "-o", "json"])
    except KubectlCommandError as e:
        print(f"Ошибка выполнения kubectl: {e.stderr.strip()}", file=sys.stderr)
        sys.exit(1)

    try:
        nodes_data = json.loads(nodes_json)
        pods_data = json.loads(pods_json)
    except json.JSONDecodeError as e:
        print(f"Ошибка парсинга JSON: {e}", file=sys.stderr)
        sys.exit(1)

    nodes = parse_nodes(nodes_data)
    pods, total_restarts = parse_pods(pods_data)

    # Выбор формата отчёта
    if args.json:
        report_content = generate_json_report(nodes, pods, total_restarts)
    else:
        report_content = generate_text_report(nodes, pods, total_restarts)

    # Вывод или запись в файл
    if args.out:
        try:
            Path(args.out).write_text(report_content + "\n", encoding="utf-8")
        except OSError as e:
            print(f"Не удалось записать в файл {args.out}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(report_content)

    # Код возврата: 0 — проблем нет, 2 — проблемы найдены
    if len(pods) > 0 or total_restarts > 0:
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
