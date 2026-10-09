# День 5 — Генератор манифестов + Kubernetes/k3s

## Что построено

- `tools/k8sgen.py` — генератор: словарь Python → JSON-манифест (`k8s/deployment.yaml`, `k8s/service.yaml`).
  JSON — подмножество YAML, поэтому kubectl читает такие файлы без правок.
- `tools/header_echo.py` — HTTP-сервис из дня 3, доработан: версия берётся из переменной окружения `APP_VERSION` (приходит из манифеста).
- Образ `echo-svc:0.1.0` собран, экспортирован (`docker save`) и загружен в k3s (`k3s ctr images import`) — у k3s свой containerd, docker-образы ему не видны.

## Три урока, найденные на практике

**1. Контейнер для Deployment обязан жить вечно.**
Первый выкат ушёл в `Completed`: `devcheck` — CLI-инструмент, он отработал и завершился. Deployment поднимает под заново, снова `Completed`, и так по кругу. В Deployment запускают сервер, а не разовый скрипт.

**2. В поде слушать `0.0.0.0`, не `127.0.0.1`.**
`header_echo.py` сначала слушал `127.0.0.1` — внутри пода это только loopback самого контейнера, Service до него не достучится (`curl: (7) Failed to connect`). Правка на `0.0.0.0` — и запросы пошли.

**3. Образ, который выкатываешь, должен существовать в containerd кластера.**
Выкат образа `echo-svc:0.1.1`, которого в k3s нет, даёт:
```
kubectl get pods → ImagePullBackOff / ErrImagePull
kubectl rollout status → Waiting for deployment "devcheck" rollout to finish: 1 out of 2 new replicas have been updated...
```
Роллаут не падает — он ждёт: Deployment поднимает 1 новый под и ждёт его готовности, старые не гасит. Правило: сначала `k3s ctr images list | grep <образ>`, потом выкат.

## Выкат и откат версии (проверено)

Версия вынесена в `env` манифеста — откат видно глазами в ответе сервиса:

```bash
cd /home/rafael/devops-sprint

# версия v2
python3 tools/k8sgen.py --image echo-svc:0.1.0 --replicas 2 --port 8080 --version v2
sudo k3s kubectl apply -f k8s/deployment.yaml
sudo k3s kubectl rollout status deployment devcheck          # successfully rolled out
sudo k3s kubectl run curl-test --rm -i --restart=Never --image=curlimages/curl:latest \
  -- sh -c 'curl -s --max-time 5 http://devcheck:8080/ping | head -2'
# → "version": "v2",

# откат
sudo k3s kubectl rollout undo deployment devcheck
sudo k3s kubectl rollout status deployment devcheck
sudo k3s kubectl run curl-test --rm -i --restart=Never --image=curlimages/curl:latest \
  -- sh -c 'curl -s --max-time 5 http://devcheck:8080/ping | head -2'
# → "version": "v1",
```

`rollout undo` откатывает **шаблон пода** (образ, env, лимиты) — сам образ из реестра никуда не девается и не «откатывается».

## Про предупреждение kubectl

```
Warning: resource deployments/devcheck was previously managed with 'kubectl apply'.
Rolling back will not update the 'last-applied-configuration' annotation...
```
`undo` меняет шаблон пода, но не обновляет аннотацию «что было применено последним». Поэтому если после отката применить старый файл — kubectl не увидит разницы и может оставить расхождение. В продакшене откат делают через git (revert коммита + apply), а `rollout undo` — быстрый инструмент для отладки.

Нумерация ревизий бывает с пропусками (1, 3, 4, 6, 7) — `undo` переназначает номера репликасетам, часть номеров исчезает. Смотреть конкретную ревизию: `kubectl rollout history deployment devcheck --revision=N`, а текущий шаблон — `kubectl get deployment devcheck -o yaml`.

## Шпаргалка

- `kubectl get pods -o wide` — список, IP, нода
- `kubectl describe pod <name>` — события и причина (ImagePullBackOff, CrashLoopBackOff)
- `kubectl logs -l app=devcheck` — stdout контейнера
- `kubectl scale deployment devcheck --replicas=3` — масштабирование
- `kubectl rollout status|undo|history deployment devcheck` — выкат, откат, история
- `kubectl get rs -l app=devcheck` — репликасеты по ревизиям (видно, что реально выкатывалось)
- `sudo k3s ctr images list | grep <образ>` — какие образы видит кластер


## вывод get pods -o wide + describe pod + история про 127.0.0.1 (главный урок)

rafael@vm-hermes:~/devops-sprint$ sudo k3s kubectl get pods -w                  NAME                        READY   STATUS        RESTARTS   AGE
devcheck-7cd9c96664-2rz4n   1/1     Running       0          39m
devcheck-7cd9c96664-kqf29   1/1     Terminating   0          77s
devcheck-7cd9c96664-n2wvj   1/1     Running       0          39m

rafael@vm-hermes:~/devops-sprint$ sudo k3s kubectl describe pod -l app=devcheck | tail -15
  Initialized                 True
  Ready                       True
  ContainersReady             True
  PodScheduled                True
Volumes:
  kube-api-access-fj8w4:
    Type:                    Projected (a volume that contains injected data from multiple sources)
    TokenExpirationSeconds:  3607
    ConfigMapName:           kube-root-ca.crt
    Optional:                false
    DownwardAPI:             true
QoS Class:                   Burstable
Node-Selectors:              <none>
Tolerations:                 node.kubernetes.io/not-ready:NoExecute op=Exists for 300s
                             node.kubernetes.io/unreachable:NoExecute op=Exists for 300s
