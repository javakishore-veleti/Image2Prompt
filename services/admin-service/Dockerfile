# Build context = repo root (see infra/docker-compose.yml)
FROM python:3.12-slim

WORKDIR /app

# Install the shared library first (good layer caching).
COPY services/shared /app/shared
RUN pip install --no-cache-dir ./shared

COPY services/admin-service /app/admin-service
RUN pip install --no-cache-dir -r /app/admin-service/requirements.txt

WORKDIR /app/admin-service
EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
