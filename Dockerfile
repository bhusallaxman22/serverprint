FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_MODULE=app.main:app \
    WEB_CONCURRENCY=2 \
    GUNICORN_BIND=0.0.0.0:8000 \
    GUNICORN_TIMEOUT=120 \
    GUNICORN_GRACEFUL_TIMEOUT=30 \
    GUNICORN_KEEPALIVE=5 \
    GUNICORN_MAX_REQUESTS=1000 \
    GUNICORN_MAX_REQUESTS_JITTER=100

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        cups-client \
        curl \
        file \
        libmagic1 \
        tini \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 printdrop \
    && useradd --system --uid 10001 --gid 10001 --home-dir /app --shell /usr/sbin/nologin printdrop \
    && mkdir -p /app /data/uploads /data/tmp \
    && chown -R printdrop:printdrop /app /data

COPY pyproject.toml /app/pyproject.toml
COPY README.md /app/README.md
COPY app /app/app
RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install .

USER printdrop

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import os,sys,urllib.request; u=f'http://127.0.0.1:{os.getenv(\"web_port\", \"8000\")}/healthz'; urllib.request.urlopen(u, timeout=3); sys.exit(0)"

ENTRYPOINT ["tini", "--"]
CMD ["sh", "-c", "exec gunicorn \"$APP_MODULE\" -k uvicorn.workers.UvicornWorker --bind \"$GUNICORN_BIND\" --workers \"$WEB_CONCURRENCY\" --timeout \"$GUNICORN_TIMEOUT\" --graceful-timeout \"$GUNICORN_GRACEFUL_TIMEOUT\" --keep-alive \"$GUNICORN_KEEPALIVE\" --max-requests \"$GUNICORN_MAX_REQUESTS\" --max-requests-jitter \"$GUNICORN_MAX_REQUESTS_JITTER\""]
