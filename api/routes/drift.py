"""Drift API routes — mounted under ``/api``.

Endpoints:
  GET  /api/health         — liveness
  GET  /api/drift          — current (unresolved) drift events
  GET  /api/drift/summary  — counts by risk and by type
  POST /api/drift/simulate — create a demo drift event
  POST /api/drift/restore  — clear simulated drift
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api import services
from api.database import get_db

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/drift")
def get_drift(db: Session = Depends(get_db)) -> list[dict]:
    return [e.to_dict() for e in services.list_active(db)]


@router.get("/drift/summary")
def get_summary(db: Session = Depends(get_db)) -> dict:
    return services.summary(db)


@router.post("/drift/simulate")
def post_simulate(db: Session = Depends(get_db)) -> dict:
    event = services.simulate(db)
    return {"created": event.to_dict()}


@router.post("/drift/restore")
def post_restore(db: Session = Depends(get_db)) -> dict:
    cleared = services.restore(db)
    return {"resolved": cleared}
