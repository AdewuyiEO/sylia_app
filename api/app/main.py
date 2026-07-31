"""Sylia API — modular monolith entrypoint (spec §1)."""
from fastapi import FastAPI

from .config import get_settings
from .db import engine
from .models import Base
from .domains.auth.router import router as auth_router
from .domains.identity.router import router as identity_router
from .domains.vision.router import router as vision_router
from .domains.closet.router import router as closet_router
from .domains.daily_look.router import router as daily_look_router
from .domains.coach.router import router as coach_router
from .domains.billing.router import router as billing_router

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")


@app.on_event("startup")
def _startup() -> None:
    # dev convenience: create tables if they don't exist. Prod uses Alembic migrations.
    if settings.env == "dev":
        Base.metadata.create_all(bind=engine)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "service": settings.app_name, "env": settings.env}


for r in (auth_router, identity_router, vision_router, closet_router,
          daily_look_router, coach_router, billing_router):
    app.include_router(r)
