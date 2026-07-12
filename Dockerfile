FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml README.md ai_os_bootstrap.pth ./
COPY src ./src

RUN uv sync --extra api --no-dev

ENV AI_OS_DATA_DIR=/data
ENV AI_OS_LOG_LEVEL=info
ENV PYTHONUNBUFFERED=1

EXPOSE 8741

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT:-8741}/api/v1/health" || exit 1

CMD ["sh", "-c", "exec uv run uvicorn ai_os.api.app:app --host 0.0.0.0 --port ${PORT:-8741} --log-level ${AI_OS_LOG_LEVEL:-info} --timeout-graceful-shutdown 30"]
