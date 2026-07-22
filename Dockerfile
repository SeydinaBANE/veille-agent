FROM python:3.11-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD uv run python healthcheck.py

CMD ["sh", "-c", "uv run uvicorn ui.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
