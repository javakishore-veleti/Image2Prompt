# CI/ECS build only — services run directly (venv) for local dev.
# Build context = repo root.
FROM python:3.12-slim
WORKDIR /app
COPY services/shared /app/shared
COPY libs/img2pmpt-caf-secret /app/caf
COPY libs/img2pmpt-caf-routers /app/caf-routers
RUN pip install --no-cache-dir ./shared ./caf "./caf-routers[openrouter,litellm]" boto3
COPY services/ai-adapters /app/ai-adapters
RUN pip install --no-cache-dir -r /app/ai-adapters/requirements.txt
WORKDIR /app/ai-adapters
EXPOSE 8003
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
