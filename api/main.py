"""DriftWatch FastAPI application.

Mounts the drift router at ``/api``, enables CORS for the dashboard, exposes
Prometheus metrics at ``/metrics``, and runs an initial drift scan on startup so
the dashboard has data immediately.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from api import services
from api.config import settings
from api.database import Base, SessionLocal, engine
from api.routes import drift_router

logger = logging.getLogger("driftwatch.api")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Safety net so the table exists even before alembic runs (local/test).
    Base.metadata.create_all(bind=engine)
    # Populate the table with a first scan; failures must not block startup.
    db = SessionLocal()
    try:
        events = services.scan_and_persist(db)
        logger.info("startup scan complete: %d active drift event(s)", len(events))
    except Exception as exc:  # noqa: BLE001
        logger.warning("startup scan failed: %s", exc)
    finally:
        db.close()
    yield


app = FastAPI(title="DriftWatch API", version="2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(drift_router, prefix="/api")

# /metrics for Prometheus
Instrumentator().instrument(app).expose(app, endpoint="/metrics")


@app.get("/")
def root() -> dict:
    return {"service": "DriftWatch API", "docs": "/docs", "api": "/api"}
