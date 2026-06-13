# Build context = repo root (see infra/docker-compose.yml)
FROM python:3.12-slim

WORKDIR /app

COPY services/shared /app/shared
RUN pip install --no-cache-dir ./shared

COPY services/ai-adapters /app/ai-adapters
RUN pip install --no-cache-dir -r /app/ai-adapters/requirements.txt

WORKDIR /app/ai-adapters
EXPOSE 8003
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
