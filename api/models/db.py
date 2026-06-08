"""The ``drift_events`` table — the persisted record of detected drift.

The ``Uuid`` column type is dialect-aware: native UUID on Postgres, CHAR on
SQLite (used by the offline test suite).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DriftEvent(Base):
    __tablename__ = "drift_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource_address: Mapped[str] = mapped_column(Text, nullable=False)
    drift_type: Mapped[str] = mapped_column(Text, nullable=False)
    field: Mapped[str | None] = mapped_column(Text)
    desired: Mapped[str | None] = mapped_column(Text)
    recorded: Mapped[str | None] = mapped_column(Text)
    actual: Mapped[str | None] = mapped_column(Text)
    cost_impact: Mapped[str | None] = mapped_column(Text)
    risk_impact: Mapped[str | None] = mapped_column(Text)
    governance_impact: Mapped[str | None] = mapped_column(Text)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "resource_address": self.resource_address,
            "drift_type": self.drift_type,
            "field": self.field,
            "desired": self.desired,
            "recorded": self.recorded,
            "actual": self.actual,
            "cost_impact": self.cost_impact,
            "risk_impact": self.risk_impact,
            "governance_impact": self.governance_impact,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }
