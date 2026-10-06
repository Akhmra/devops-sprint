# devcheck в образе: две стадии, непривилегированный пользователь, проверка здоровья.
ARG BASE=python:3.11-slim
FROM ${BASE} AS builder
#FROM python:3.11-slim AS builder
WORKDIR /src
COPY tools/ tools/
RUN python -m compileall -q tools/          # «цех»: подготовка (тут были бы зависимости)


ARG BASE=python:3.11-slim
FROM ${BASE} AS builder
#FROM python:3.11-slim AS runtime
WORKDIR /app
COPY --from=builder /src/tools/ tools/
RUN useradd --create-home --shell /usr/sbin/nologin appuser
USER appuser
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python tools/devcheck.py --json
ENTRYPOINT ["python", "tools/devcheck.py"]
