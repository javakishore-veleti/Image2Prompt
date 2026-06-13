from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from image2prompt_shared.logging_config import configure_logging, get_logger
from image2prompt_shared.observability import init_observability

from .api import prompts_controller, requests_controller
from .config import settings
from .db import Base, db

configure_logging(service_name=settings.service_name, level=settings.log_level, as_json=settings.log_json)
init_observability(settings)
log = get_logger(__name__)

SERVICE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("starting %s (schema=%s)", settings.service_name, settings.db_schema)
    db.bootstrap(base=Base, settings=settings, service_dir=SERVICE_DIR)
    yield


app = FastAPI(title="Image2Prompt Image Processing Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(requests_controller.router)
app.include_router(prompts_controller.router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "service": settings.service_name}
