FROM python:3.12.11-slim AS builder
ENV PIP_NO_CACHE_DIR=1
WORKDIR /build
COPY requirements/ .
RUN pip wheel --wheel-dir=/wheels -r dev.txt
FROM python:3.12.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN groupadd -r app && useradd -r -g app app && mkdir -p /app/staticfiles /app/media /backups && chown -R app:app /app /backups
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*
WORKDIR /app
COPY --chown=app:app . .
USER root
RUN chmod +x /app/entrypoint.sh
USER app
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/')"
CMD ["gunicorn","config.wsgi:application","--bind","0.0.0.0:8000","--workers","3","--access-logfile","-"]
