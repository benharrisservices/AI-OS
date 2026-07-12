FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml README.md ai_os_bootstrap.pth ./
COPY src ./src

RUN uv sync --extra api --no-dev

ENV AI_OS_DATA_DIR=/data
ENV PYTHONUNBUFFERED=1

EXPOSE 8741

CMD uv run uvicorn ai_os.api.app:app --host 0.0.0.0 --port ${PORT:-8741}
