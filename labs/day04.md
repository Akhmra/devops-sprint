rafael@vm-hermes:~/devops-sprint$ docker build -f Dockerfile --build-arg BASE=python:3.11-alpine -t devcheck:1.0.0-alpine .
Sending build context to Docker daemon  15.76MB
Step 1/11 : FROM python:3.11-slim AS builder
 ---> 541096ae9b05
Step 2/11 : WORKDIR /src
 ---> Using cache
 ---> 0b744ee6f3c0
Step 3/11 : COPY tools/ tools/
 ---> Using cache
 ---> e25b4b3c35b0
Step 4/11 : RUN python -m compileall -q tools/          # «цех»: подготовка (тут были бы зависимости)
 ---> Using cache
 ---> 290bc5f739ef
Step 5/11 : FROM python:3.11-slim AS runtime
 ---> 541096ae9b05
Step 6/11 : WORKDIR /app
 ---> Using cache
 ---> 9925186e5416
Step 7/11 : COPY --from=builder /src/tools/ tools/
 ---> Using cache
 ---> d694d88b0d27
Step 8/11 : RUN useradd --create-home --shell /usr/sbin/nologin appuser
 ---> Using cache
 ---> dfe74eed7fae
Step 9/11 : USER appuser
 ---> Using cache
 ---> 6fbb14f5e39c
Step 10/11 : HEALTHCHECK --interval=30s --timeout=5s --retries=3   CMD python tools/devcheck.py --json
 ---> Using cache
 ---> 657b3fb887cb
Step 11/11 : ENTRYPOINT ["python", "tools/devcheck.py"]
 ---> Using cache
 ---> ef03386e6b9e
[Warning] One or more build-args [BASE] were not consumed
Successfully built ef03386e6b9e
Successfully tagged devcheck:1.0.0-alpine
rafael@vm-hermes:~/devops-sprint$ docker tag devcheck:0.1.0 devcheck:1.0.0 && docker tag devcheck:0.1.0 devcheck:latest
docker images devcheck
REPOSITORY   TAG            IMAGE ID       CREATED       SIZE
devcheck     0.1.0          ef03386e6b9e   2 hours ago   125MB
devcheck     1.0.0          ef03386e6b9e   2 hours ago   125MB
devcheck     1.0.0-alpine   ef03386e6b9e   2 hours ago   125MB
devcheck     latest         ef03386e6b9e   2 hours ago   125MB
rafael@vm-hermes:~/devops-sprint$ nano Dockerfile
rafael@vm-hermes:~/devops-sprint$ docker build -f Dockerfile --build-arg BASE=python:3.11-alpine -t devcheck:1.0.0-alpine .
docker tag devcheck:0.1.0 devcheck:1.0.0 && docker tag devcheck:0.1.0 devcheck:latest
docker images devcheck
Sending build context to Docker daemon  15.76MB
Step 1/13 : ARG BASE=python:3.11-slim
Step 2/13 : FROM ${BASE} AS builder
3.11-alpine: Pulling from library/python
e2de96513ba9: Already exists
2c95de37c4a6: Pull complete
f1244e1e87fe: Pull complete
82ceee3231d4: Pull complete
Digest: sha256:d9368b3a5ac59afea7b5d4f2e2aea0941dbf9fdee9c369c5bec00b98244bc929
Status: Downloaded newer image for python:3.11-alpine
 ---> 607dc7448339
Step 3/13 : WORKDIR /src
 ---> Running in 5d3324a494b2
Removing intermediate container 5d3324a494b2
 ---> 70711a48fc77
Step 4/13 : COPY tools/ tools/
 ---> 043376060d2e
Step 5/13 : RUN python -m compileall -q tools/          # «цех»: подготовка (тут были бы зависимости)
 ---> Running in 81aa69288d4b
Removing intermediate container 81aa69288d4b
 ---> 77a902f6539d
Step 6/13 : ARG BASE=python:3.11-slim
 ---> Running in 7ff007dbf6e9
Removing intermediate container 7ff007dbf6e9
 ---> 5d7560028d85
builder stage name already used
REPOSITORY   TAG            IMAGE ID       CREATED       SIZE
devcheck     0.1.0          ef03386e6b9e   2 hours ago   125MB
devcheck     1.0.0          ef03386e6b9e   2 hours ago   125MB
devcheck     1.0.0-alpine   ef03386e6b9e   2 hours ago   125MB
devcheck     latest         ef03386e6b9e   2 hours ago   125MB
rafael@vm-hermes:~/devops-sprint$ docker images | grep localhost:5000
localhost:5000/devcheck   0.1.0          ef03386e6b9e   2 hours ago      125MB
rafael@vm-hermes:~/devops-sprint$ docker build -t devcheck:${{ github.sha }} .
-bash: devcheck:${{ github.sha }}: bad substitution
rafael@vm-hermes:~/devops-sprint$ sudo docker images | grep localhost:5000
localhost:5000/devcheck   0.1.0          ef03386e6b9e   2 hours ago      125MB


python:3.9-slim   → 122 МБ
python:3.9-alpine → 51.3 МБ
вывод: alpine дешевле на 70 МБ, но другой набор утилит → в базовом образе нет useradd,
сборка без правки падает; musl вместо glibc — та же тема, что с колёсами в дни 15–16.
