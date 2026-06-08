"""create drift_events table

Revision ID: 0001
Revises:
Create Date: 2026-06-08
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "drift_events",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("resource_address", sa.Text(), nullable=False),
        sa.Column("drift_type", sa.Text(), nullable=False),
        sa.Column("field", sa.Text(), nullable=True),
        sa.Column("desired", sa.Text(), nullable=True),
        sa.Column("recorded", sa.Text(), nullable=True),
        sa.Column("actual", sa.Text(), nullable=True),
        sa.Column("cost_impact", sa.Text(), nullable=True),
        sa.Column("risk_impact", sa.Text(), nullable=True),
        sa.Column("governance_impact", sa.Text(), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_drift_events_resolved_at", "drift_events", ["resolved_at"])


def downgrade() -> None:
    op.drop_index("ix_drift_events_resolved_at", table_name="drift_events")
    op.drop_table("drift_events")
