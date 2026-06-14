from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from image2prompt_shared.logging_config import configure_logging, get_logger
from image2prompt_shared.observability import (
    init_observability,
    instrument_fastapi,
    instrument_sqlalchemy,
)
from image2prompt_shared.request_context import RequestIdMiddleware

from .api import kb_controller
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
    instrument_sqlalchemy(db.engine)
    yield


app = FastAPI(title="Image2Prompt KB Service", lifespan=lifespan)
instrument_fastapi(app)
app.add_middleware(RequestIdMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(kb_controller.router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "service": settings.service_name}
