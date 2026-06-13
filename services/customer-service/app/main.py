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
from image2prompt_shared.scheduler import PeriodicScheduler

from .api import (
    auth_controller,
    connections_controller,
    internal_controller,
    payments_controller,
    profile_controller,
    projects_controller,
)
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
    scheduler = PeriodicScheduler(enabled=settings.scheduler_enabled)
    scheduler.add_job(
        name="prune-revoked-tokens",
        interval_seconds=settings.prune_interval_seconds,
        func=_prune_revoked_tokens,
        run_on_start=True,
    )
    await scheduler.start()
    try:
        yield
    finally:
        await scheduler.stop()


def _prune_revoked_tokens() -> None:
    import time

    from .dao.revoked_token_dao import RevokedTokenDao

    try:
        with db.SessionLocal() as session:
            removed = RevokedTokenDao().prune_expired(session, int(time.time()))
        if removed:
            log.info("pruned %d expired revoked tokens", removed)
    except Exception as exc:  # never block startup on housekeeping
        log.warning("revoked-token prune skipped: %s", exc)


app = FastAPI(title="Image2Prompt Customer Service", lifespan=lifespan)
instrument_fastapi(app)
app.add_middleware(RequestIdMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_controller.router)
app.include_router(profile_controller.router)
app.include_router(projects_controller.router)
app.include_router(payments_controller.router)
app.include_router(connections_controller.router)
app.include_router(internal_controller.router)
app.include_router(internal_controller.maintenance)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "service": settings.service_name}
