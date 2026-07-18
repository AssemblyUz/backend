# syntax=docker/dockerfile:1.7

ARG PYTHON_VERSION=3.14.6
ARG UV_VERSION=0.9.16
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM python:${PYTHON_VERSION}-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:$PATH" \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=0 \
    UV_LINK_MODE=copy

FROM base AS builder
COPY --from=uv /uv /uvx /usr/local/bin/

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

ENV SECRET_KEY=build-only-secret-key-for-collectstatic \
    DEBUG=False \
    ALLOWED_HOSTS=localhost \
    ADMIN_URL=admin/ \
    DATABASE_URL=sqlite:////tmp/assembly-build.sqlite3 \
    CORS_ALLOWED_ORIGINS=http://localhost \
    CSRF_TRUSTED_ORIGINS=http://localhost
COPY . .
RUN python manage.py collectstatic --noinput

FROM base AS runtime

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app /app

RUN useradd --create-home --uid 1000 app \
    && mkdir -p /app/media \
    && chown -R app:app /app
USER app

EXPOSE 8000

ENV WEB_CONCURRENCY=1 \
    GUNICORN_THREADS=2 \
    GUNICORN_TIMEOUT=30

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz/', timeout=3).read()"

CMD ["sh", "-c", "exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers ${WEB_CONCURRENCY} --threads ${GUNICORN_THREADS} --timeout ${GUNICORN_TIMEOUT} --access-logfile - --error-logfile -"]
