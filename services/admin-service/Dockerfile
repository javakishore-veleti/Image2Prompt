# CI/ECS build only — services run directly (venv) for local dev.
# Build context = repo root.
FROM python:3.12-slim
WORKDIR /app
COPY services/shared /app/shared
COPY libs/img2pmpt-caf-secret /app/caf
RUN pip install --no-cache-dir ./shared ./caf boto3
COPY services/admin-service /app/admin-service
RUN pip install --no-cache-dir -r /app/admin-service/requirements.txt
WORKDIR /app/admin-service
EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
