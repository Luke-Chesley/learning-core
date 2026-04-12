FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./
COPY learning_core ./learning_core

RUN uv sync --frozen --no-dev

# Cloud Run injects PORT at runtime. The local script defaults to 127.0.0.1:8000,
# so override host/port here while keeping the same console entrypoint.
CMD ["sh", "-c", "LEARNING_CORE_HOST=0.0.0.0 LEARNING_CORE_PORT=${PORT:-8080} uv run learning-core"]
