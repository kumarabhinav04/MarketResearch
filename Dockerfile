FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AIFACTORY_DB_PATH=/app/artifacts/aifactory.db \
    AIFACTORY_CONFIG_DIR=/app/config \
    AIFACTORY_REPORT_DIR=/app/artifacts/reports \
    AIFACTORY_RAW_SOURCE_DIR=/app/artifacts/raw-sources

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY config ./config
RUN pip install --no-cache-dir .

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/artifacts/reports /app/artifacts/raw-sources \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"

CMD ["uvicorn", "aifactory.api:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]
