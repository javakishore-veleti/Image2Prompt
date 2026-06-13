# Build context = repo root (see infra/docker-compose.yml)
FROM python:3.12-slim

WORKDIR /app

COPY services/shared /app/shared
RUN pip install --no-cache-dir ./shared

COPY services/customer-service /app/customer-service
RUN pip install --no-cache-dir -r /app/customer-service/requirements.txt

WORKDIR /app/customer-service
EXPOSE 8002
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
