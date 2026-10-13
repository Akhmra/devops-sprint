rafael@vm-hermes:~/devops-sprint$ kubectl apply -f k8s/day07/cronjob.yaml
cronjob.batch/health-cron created
rafael@vm-hermes:~/devops-sprint$ kubectl -n lab get cronjob,jobs
NAME                        SCHEDULE      TIMEZONE        SUSPEND   ACTIVE   LAST SCHEDULE   AGE
cronjob.batch/health-cron   */5 * * * *   Europe/Moscow   False     0        <none>          5s
rafael@vm-hermes:~/devops-sprint$ kubectl -n lab create job --from=cronjob/health-cron manual-test
job.batch/manual-test created
rafael@vm-hermes:~/devops-sprint$ kubectl -n lab logs job/manual-test
Tue Oct 13 17:08:49 UTC 2026
{"status": "ok"}
rafael@vm-hermes:~/devops-sprint$ kubectl get pods
NAME                        READY   STATUS    RESTARTS   AGE
devcheck-666b8f7499-hth85   1/1     Running   0          4d6h
devcheck-666b8f7499-k79nw   1/1     Running   0          4d6h
rafael@vm-hermes:~/devops-sprint$ mkdir -p k8s/day07/broken
rafael@vm-hermes:~/devops-sprint$ kubectl -n lab create deployment bad-image --image=nope:0.0.1 --dry-run=client -o yaml > k8s/day07/broken/bad-image.yaml
rafael@vm-hermes:~/devops-sprint$ kubectl apply -f k8s/day07/broken/bad-image.yaml
sleep 40; kubectl -n lab get pods -l app=bad-image
kubectl -n lab describe pod -l app=bad-image | tail -15
deployment.apps/bad-image created
NAME                         READY   STATUS         RESTARTS   AGE
bad-image-77f8d7489d-mrjmf   0/1     ErrImagePull   0          40s
    Optional:                false
    DownwardAPI:             true
QoS Class:                   BestEffort
Node-Selectors:              <none>
Tolerations:                 node.kubernetes.io/not-ready:NoExecute op=Exists for 300s
                             node.kubernetes.io/unreachable:NoExecute op=Exists for 300s
Events:
  Type     Reason     Age                From               Message
  ----     ------     ----               ----               -------
  Normal   Scheduled  40s                default-scheduler  Successfully assigned lab/bad-image-77f8d7489d-mrjmf to vm-hermes
  Normal   Pulling    24s (x2 over 40s)  kubelet            spec.containers{nope}: Pulling image "nope:0.0.1"
  Warning  Failed     23s (x2 over 38s)  kubelet            spec.containers{nope}: Failed to pull image "nope:0.0.1": failed to pull and unpack image "docker.io/library/nope:0.0.1": failed to resolve reference "docker.io/library/nope:0.0.1": pull access denied, repository does not exist or may require authorization: server message: insufficient_scope: authorization failed
  Warning  Failed     23s (x2 over 38s)  kubelet            spec.containers{nope}: Error: ErrImagePull
  Normal   BackOff    10s (x2 over 38s)  kubelet            spec.containers{nope}: Back-off pulling image "nope:0.0.1"
  Warning  Failed     10s (x2 over 38s)  kubelet            spec.containers{nope}: Error: ImagePullBackOff
rafael@vm-hermes:~/devops-sprint$ cat > k8s/day07/broken/oom.yaml <<'YAML'
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
sleep 30; kubectl -n lab get pods -l app=oom-demo
kubectl -n lab describe pod -l app=oom-demo | grep -A3 'Last State'
deployment.apps/oom-demo created
NAME                        READY   STATUS      RESTARTS      AGE
oom-demo-656fbc998b-vprh6   0/1     OOMKilled   2 (29s ago)   30s
    Last State:     Terminated
      Reason:       OOMKilled
      Exit Code:    137
      Started:      Tue, 13 Oct 2026 20:27:42 +0300
rafael@vm-hermes:~/devops-sprint$
rafael@vm-hermes:~/devops-sprint$
rafael@vm-hermes:~/devops-sprint$
rafael@vm-hermes:~/devops-sprint$
rafael@vm-hermes:~/devops-sprint$ kubectl -n lab create deployment crash-demo --image=app:0.1.0 --dry-run=client -o yaml > k8s/day07/broken/crash.yaml
# правишь crash.yaml руками: добавить imagePullPolicy: Never и
# command: ["python", "-c", "import sys;print('стартую и падаю', flush=True);sys.exit(1)"]
kubectl apply -f k8s/day07/broken/crash.yaml
sleep 30; kubectl -n lab get pods -l app=crash-demo
kubectl -n lab logs -l app=crash-demo
kubectl -n lab describe pod -l app=crash-demo | grep -A4 'Last State'
deployment.apps/crash-demo created
^C
rafael@vm-hermes:~/devops-sprint$ nano k8s/day07/broken/crash.yaml
rafael@vm-hermes:~/devops-sprint$ kubectl -n lab create deployment crash-demo --image=app:0.1.0 --dry-run=client -o yaml > k8s/day07/broken/crash.yaml
rafael@vm-hermes:~/devops-sprint$ kubectl apply -f k8s/day07/broken/crash.yaml
sleep 30; kubectl -n lab get pods -l app=crash-demo
kubectl -n lab logs -l app=crash-demo
kubectl -n lab describe pod -l app=crash-demo | grep -A4 'Last State'
deployment.apps/crash-demo unchanged
^C
rafael@vm-hermes:~/devops-sprint$
rafael@vm-hermes:~/devops-sprint$
rafael@vm-hermes:~/devops-sprint$
rafael@vm-hermes:~/devops-sprint$ ls -al k8s/day07/broken/
total 20
drwxr-xr-x 2 rafael rafael 4096 Oct 13 20:30 .
drwxr-xr-x 3 rafael rafael 4096 Oct 13 20:23 ..
-rw-r--r-- 1 rafael rafael  365 Oct 13 20:24 bad-image.yaml
-rw-r--r-- 1 rafael rafael  367 Oct 13 20:30 crash.yaml
-rw-r--r-- 1 rafael rafael  485 Oct 13 20:27 oom.yaml
