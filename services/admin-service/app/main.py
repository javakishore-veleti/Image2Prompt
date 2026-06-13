from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from image2prompt_shared.base import Base

from .config import settings
from .deps import db
from .routers import auth, customers, providers
from .seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.create_all(Base)
    with db.SessionLocal() as session:
        seed(session)
    yield


app = FastAPI(title="Image2Prompt Admin Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(providers.router)
app.include_router(providers.internal)
app.include_router(customers.router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "service": "admin-service"}
