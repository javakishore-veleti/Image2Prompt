from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from image2prompt_shared.base import utcnow
from image2prompt_shared.logging_config import configure_logging, get_logger
from image2prompt_shared.observability import (
    init_observability,
    instrument_fastapi,
    instrument_sqlalchemy,
)
from image2prompt_shared.request_context import RequestIdMiddleware
from image2prompt_shared.scheduler import PeriodicScheduler

from .api import (
    admin_users_controller,
    analytics_controller,
    auth_controller,
    csp_controller,
    customers_controller,
    maintenance_controller,
    providers_controller,
    subscriptions_controller,
)
from .config import settings
from .db import Base, db
from .seed import seed

configure_logging(service_name=settings.service_name, level=settings.log_level, as_json=settings.log_json)
init_observability(settings)
log = get_logger(__name__)

SERVICE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("starting %s (schema=%s)", settings.service_name, settings.db_schema)
    db.bootstrap(base=Base, settings=settings, service_dir=SERVICE_DIR, seed_fn=seed)
    instrument_sqlalchemy(db.engine)
    # Periodic housekeeping so a long-running task doesn't accumulate stale rows
    # between restarts. run_on_start=True keeps the original startup-prune behavior.
    scheduler = PeriodicScheduler(enabled=settings.scheduler_enabled)
    scheduler.add_job(
        name="prune-revoked-tokens",
        interval_seconds=settings.prune_interval_seconds,
        func=_prune_revoked_tokens,
        run_on_start=True,
    )
    scheduler.add_job(
        name="prune-csp-violations",
        interval_seconds=settings.prune_interval_seconds,
        func=_prune_csp_violations,
        run_on_start=True,
    )
    await scheduler.start()
    try:
        yield
    finally:
        await scheduler.stop()


def _prune_csp_violations() -> None:
    from datetime import timedelta

    from .dao.csp_violation_dao import CspViolationDao

    try:
        cutoff = utcnow() - timedelta(days=settings.csp_retention_days)
        with db.SessionLocal() as session:
            removed = CspViolationDao().prune_older_than(session, cutoff)
        if removed:
            log.info("pruned %d CSP violations older than %d days", removed, settings.csp_retention_days)
    except Exception as exc:  # never block startup on housekeeping
        log.warning("csp-violation prune skipped: %s", exc)


def _prune_revoked_tokens() -> None:
    import time

    from .dao.revoked_token_dao import RevokedTokenDao

    try:
        with db.SessionLocal() as session:
            removed = RevokedTokenDao().prune_expired(session, int(time.time()))
        if removed:
            log.info("pruned %d expired revoked tokens", removed)
    except Exception as exc:
        log.warning("revoked-token prune skipped: %s", exc)


app = FastAPI(title="Image2Prompt Admin Service", lifespan=lifespan)
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
app.include_router(providers_controller.router)
app.include_router(providers_controller.internal)
app.include_router(customers_controller.router)
app.include_router(analytics_controller.router)
app.include_router(admin_users_controller.router)
app.include_router(csp_controller.router)
app.include_router(csp_controller.internal)
app.include_router(maintenance_controller.router)
app.include_router(maintenance_controller.audit)
app.include_router(subscriptions_controller.router)
app.include_router(subscriptions_controller.internal)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "service": settings.service_name}
