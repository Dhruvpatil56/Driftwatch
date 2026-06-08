"""Detection + persistence service.

This is the bridge between the Sprint 1 engine and the Sprint 2 database. It
reuses the engine, parsers and providers *as-is* (no modification) and is shared
by both the API routes and the background scraper.

Responsibilities:
  * ``detect()``            — run the three-way reconciliation (live AWS, with an
                              offline demo fallback).
  * ``scan_and_persist()``  — sync detected drift into the ``drift_events`` table.
  * ``simulate()`` / ``restore()`` — create / clear a demo drift event.
  * ``summary()``           — aggregate counts for the dashboard cards + chart.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.config import settings
from api.models.db import DriftEvent
from engine.diff import reconcile
from engine.parser import parse_hcl, parse_tfstate
from models.drift import DriftResult
from providers.aws import AWSProvider, build_actual

REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = REPO_ROOT / "terraform-demo"
STATE_PATH = DEMO_DIR / "terraform.tfstate"
DEMO_ACTUAL_PATH = DEMO_DIR / "actual-state.demo.json"

RESOURCE_TYPES = ["aws_instance", "aws_s3_bucket", "aws_security_group"]

# Sentinel marking events created by POST /api/drift/simulate so restore can
# find them and scans never touch them.
SIM_ADDRESS = "aws_instance.simulated"

RISK_LEVELS = ["Critical", "High", "Medium", "Low"]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --- detection -------------------------------------------------------------
def _load_demo_actual() -> list:
    with open(DEMO_ACTUAL_PATH, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    out = []
    for resource_type in RESOURCE_TYPES:
        for raw in data.get(resource_type, []):
            out.append(build_actual(resource_type, raw))
    return out


def _get_actual() -> list:
    if settings.driftwatch_offline:
        return _load_demo_actual()
    try:
        return AWSProvider(region=settings.aws_region).list_resources(RESOURCE_TYPES)
    except Exception:
        # Any AWS failure (no creds, offline, throttling) falls back to demo.
        return _load_demo_actual()


def detect() -> list[DriftResult]:
    """Run the full three-way reconciliation and return scored drift."""
    desired = parse_hcl(str(DEMO_DIR))
    recorded = parse_tfstate(str(STATE_PATH))
    actual = _get_actual()
    return reconcile(desired, recorded, actual)


# --- persistence -----------------------------------------------------------
def _key(address: str, field: str, drift_type: str, desired: str, actual: str) -> tuple:
    return (address, field, drift_type, desired, actual)


def _event_key(e: DriftEvent) -> tuple:
    return _key(e.resource_address, e.field, e.drift_type, e.desired, e.actual)


def _result_key(r: DriftResult) -> tuple:
    return _key(r.resource_address, r.field, r.drift_type, r.desired, r.actual)


def scan_and_persist(db: Session) -> list[DriftEvent]:
    """Reconcile, then sync the result into ``drift_events``.

    New drift is inserted; drift that has disappeared is marked resolved.
    Simulated events are left untouched. Returns the active (unresolved) events.
    """
    results = detect()
    now = _utcnow()

    existing = list(
        db.execute(
            select(DriftEvent).where(
                DriftEvent.resolved_at.is_(None),
                DriftEvent.resource_address != SIM_ADDRESS,
            )
        ).scalars()
    )
    existing_by_key = {_event_key(e): e for e in existing}
    current_keys = set()

    for r in results:
        k = _result_key(r)
        current_keys.add(k)
        if k not in existing_by_key:
            db.add(
                DriftEvent(
                    resource_address=r.resource_address,
                    drift_type=r.drift_type,
                    field=r.field,
                    desired=r.desired,
                    recorded=r.recorded,
                    actual=r.actual,
                    cost_impact=r.cost_impact,
                    risk_impact=r.risk_impact,
                    governance_impact=r.governance_impact,
                    detected_at=now,
                )
            )

    # Anything previously open but no longer detected is now resolved.
    for e in existing:
        if _event_key(e) not in current_keys:
            e.resolved_at = now

    db.commit()
    return list_active(db)


def list_active(db: Session) -> list[DriftEvent]:
    return list(
        db.execute(
            select(DriftEvent)
            .where(DriftEvent.resolved_at.is_(None))
            .order_by(DriftEvent.detected_at.desc())
        ).scalars()
    )


# --- simulate / restore ----------------------------------------------------
def simulate(db: Session) -> DriftEvent:
    """Insert a demo drift event so the dashboard has something to show."""
    event = DriftEvent(
        resource_address=SIM_ADDRESS,
        drift_type="Infrastructure Drift",
        field="instance_type",
        desired="t3.micro",
        recorded="t3.micro",
        actual="m5.large",
        cost_impact="Unknown",
        risk_impact="High",
        governance_impact="Simulated drift (demo)",
        detected_at=_utcnow(),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def restore(db: Session) -> int:
    """Resolve all simulated drift events. Returns how many were cleared."""
    now = _utcnow()
    sims = list(
        db.execute(
            select(DriftEvent).where(
                DriftEvent.resource_address == SIM_ADDRESS,
                DriftEvent.resolved_at.is_(None),
            )
        ).scalars()
    )
    for e in sims:
        e.resolved_at = now
    db.commit()
    return len(sims)


# --- summary ---------------------------------------------------------------
def summary(db: Session) -> dict:
    events = list_active(db)
    by_risk = {level: 0 for level in RISK_LEVELS}
    by_type: dict[str, int] = {}
    for e in events:
        if e.risk_impact in by_risk:
            by_risk[e.risk_impact] += 1
        by_type[e.drift_type] = by_type.get(e.drift_type, 0) + 1
    return {"total": len(events), "by_risk": by_risk, "by_type": by_type}
