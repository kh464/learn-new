FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1

WORKDIR /build

COPY pyproject.toml README.md /build/
COPY app /build/app

RUN python -m pip install --upgrade pip build && \
    python -m build --wheel


FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1

WORKDIR /app

RUN useradd --create-home --shell /usr/sbin/nologin --uid 10001 appuser && \
    mkdir -p /app/.learn && \
    chown -R 10001:10001 /app

COPY --from=builder /build/dist/*.whl /tmp/learn_new.whl
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini
COPY config /app/config

RUN python -m pip install --upgrade pip && \
    python -m pip install /tmp/learn_new.whl && \
    rm -f /tmp/learn_new.whl

USER 10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=5 \
  CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health/ready').status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
