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
    if settings.billing_sweep_enabled:
        scheduler.add_job(
            name="monthly-billing-sweep",
            interval_seconds=settings.billing_sweep_interval_seconds,
            func=_run_billing_sweep,
            run_on_start=False,
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


def _run_billing_sweep() -> None:
    """Invoice every active subscriber for the current month. Idempotent per
    (customer, month), so frequent sweeps still bill once. Fully fail-safe — one
    customer's failure never aborts the rest, and the job never raises."""
    from .di import _billing_client, get_payments_facade
    from .dtos.internal_dtos import ChargeSubscriptionReq

    facade = get_payments_facade()
    subs = _billing_client.list_active_subscriptions()
    if not subs:
        return
    billed = skipped = failed = 0
    for sub in subs:
        cid = sub.get("customer_id")
        if not cid:
            continue
        try:
            with db.SessionLocal() as session:
                resp = facade.charge_subscription(ChargeSubscriptionReq(db=session, customer_id=cid))
            if not resp.success:
                failed += 1
            elif resp.already_billed or resp.status in ("nothing_to_bill", "stripe_not_configured"):
                skipped += 1
            else:
                billed += 1
        except Exception as exc:  # isolate per-customer failures
            failed += 1
            log.warning("billing sweep failed for customer %s: %s", cid, exc)
    log.info("billing sweep: %d billed, %d skipped, %d failed", billed, skipped, failed)


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
