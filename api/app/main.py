"""Sylia API — modular monolith entrypoint (spec §1)."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
from .domains.uploads.router import router as uploads_router
from .domains.journey.router import router as journey_router
from .domains.integrations.router import router as integrations_router
from .domains.account.router import router as account_router
from .domains.catalog.router import router as discover_router, partner as partner_router, admin as admin_router

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.2.0")

if settings.cors_origins:
    app.add_middleware(CORSMiddleware,
                       allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
                       allow_methods=["*"], allow_headers=["*"])

if settings.env == "prod" and settings.jwt_secret.startswith("dev-secret-change-me"):
    raise RuntimeError("Set JWT_SECRET before running in prod")


@app.on_event("startup")
def _startup() -> None:
    # dev convenience: create tables if they don't exist. Prod uses Alembic migrations.
    if settings.env == "dev":
        Base.metadata.create_all(bind=engine)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "service": settings.app_name, "env": settings.env}


for r in (auth_router, account_router, identity_router, vision_router, uploads_router,
          discover_router, closet_router, daily_look_router, coach_router, billing_router,
          integrations_router, journey_router, partner_router, admin_router):
    app.include_router(r)
