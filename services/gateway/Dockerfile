# Build context = repo root (see infra/docker-compose.yml)
FROM python:3.12-slim

WORKDIR /app

COPY services/shared /app/shared
RUN pip install --no-cache-dir ./shared

COPY services/gateway /app/gateway
RUN pip install --no-cache-dir -r /app/gateway/requirements.txt

WORKDIR /app/gateway
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
