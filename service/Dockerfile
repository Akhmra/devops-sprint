FROM python:3.11-slim
WORKDIR /app
COPY app.py .
ENV APP_PORT=8080
EXPOSE 8080
HEALTHCHECK CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8080/health')" || exit 1
CMD ["python", "app.py"]
