"""k8sgen — генератор манифестов Kubernetes: Python как источник правды.

    python3 tools/k8sgen.py --image devcheck:0.1.0 --replicas 2 --port 8080
    → создаёт k8s/deployment.yaml и k8s/service.yaml

Проверка (без кластера): k3s kubectl apply --dry-run=client -f k8s/
"""
import argparse
import json
import os

K8S_DIR = os.path.join(os.path.dirname(__file__), "..", "k8s")


def build_deployment(image: str, replicas: int, port: int, version: str = "v1") -> dict:
    """Deployment: N реплик одного контейнера. Задаём всё словарём —
    никакого ручного YAML: структура = правда, json.dump её сериализует."""
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": "devcheck", "labels": {"app": "devcheck"}},
        "spec": {
            "replicas": replicas,
            "selector": {"matchLabels": {"app": "devcheck"}},
            "template": {
                "metadata": {"labels": {"app": "devcheck"}},
                "spec": {
                    "containers": [{
                        "name": "devcheck",
                        "image": image,
                        "ports": [{"containerPort": port}],
                        "env": [{"name": "APP_VERSION", "value": version}],
                        "resources": {
                            "requests": {"cpu": "50m", "memory": "32Mi"},
                            "limits": {"cpu": "200m", "memory": "128Mi"},
                        },
                    }]
                },
            },
        },
    }


def build_service(port: int) -> dict:
    """Service типа ClusterIP: стабильный адрес на группу подов."""
    return {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {"name": "devcheck", "labels": {"app": "devcheck"}},
        "spec": {
            "type": "ClusterIP",
            "selector": {"app": "devcheck"},
            "ports": [{"port": port, "targetPort": port, "protocol": "TCP"}],
        },
    }


def write_json(path: str, doc: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"записан {path}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Генератор k8s-манифестов для devcheck")
    ap.add_argument("--image", required=True, help="образ, напр. devcheck:0.1.0")
    ap.add_argument("--replicas", type=int, default=2)
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--version", default="v1", help="значение env APP_VERSION в поде")
    args = ap.parse_args()

    if args.replicas < 1:
        ap.error("--replicas должен быть >= 1")

    write_json(os.path.join(K8S_DIR, "deployment.yaml"),
               build_deployment(args.image, args.replicas, args.port, args.version))
    write_json(os.path.join(K8S_DIR, "service.yaml"),
               build_service(args.port))


if __name__ == "__main__":
    main()
