"""Drift API routes — mounted under ``/api``.

Endpoints:
  GET  /api/health         — liveness
  GET  /api/drift          — current (unresolved) drift events (instant);
                             refreshes in the background
  GET  /api/drift/summary  — counts by risk and by type
  POST /api/drift/simulate — create a demo drift event
  POST /api/drift/restore  — clear simulated drift
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from api import services
from api.database import SessionLocal, get_db

router = APIRouter()


def _scan_in_background() -> None:
    """Run a reconciliation scan with its own session.

    Must NOT reuse the request's session — that is closed as soon as the
    response is sent, before this background task runs.
    """
    db = SessionLocal()
    try:
        services.scan_and_persist(db)
    finally:
        db.close()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/drift")
def get_drift(
    background_tasks: BackgroundTasks, db: Session = Depends(get_db)
) -> list[dict]:
    # Return the currently stored drift immediately so the UI never blocks on
    # AWS reconciliation (which can take several seconds)...
    results = [e.to_dict() for e in services.list_active(db)]
    # ...then refresh in the background so the next poll reflects live state.
    background_tasks.add_task(_scan_in_background)
    return results


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
