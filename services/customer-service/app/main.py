from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from image2prompt_shared.base import Base

from .config import settings
from .deps import db
from .routers import auth, internal, payments, profile, projects


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.create_all(Base)
    yield


app = FastAPI(title="Image2Prompt Customer Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(projects.router)
app.include_router(payments.router)
app.include_router(internal.router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "service": "customer-service"}
