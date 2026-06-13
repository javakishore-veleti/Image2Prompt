from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from image2prompt_shared.logging_config import configure_logging, get_logger
from image2prompt_shared.observability import init_observability, instrument_fastapi

from .api import invoke_controller
from .config import settings

configure_logging(service_name=settings.service_name, level=settings.log_level, as_json=settings.log_json)
init_observability(settings)
log = get_logger(__name__)

app = FastAPI(title="Image2Prompt AI Adapters")
instrument_fastapi(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(invoke_controller.router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "service": settings.service_name}
