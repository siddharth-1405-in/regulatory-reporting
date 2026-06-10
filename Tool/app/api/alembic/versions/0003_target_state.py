"""target-state: source systems, schedule sign-off, overrides, exception trail

Adds source_system and schedule_signoff tables and the new columns on
element_governance (override) and remediation_proposal (maker/checker trail).
Uses metadata.create_all for the new tables and ALTERs for the new columns
(works on PostgreSQL and SQLite).

Revision ID: 0003_target_state
Revises: 0002_element_governance
Create Date: 2026-06-09
"""
from alembic import op
import sqlalchemy as sa

import app.models  # noqa: F401  register models on Base
from app.core.db import Base

revision = "0003_target_state"
down_revision = "0002_element_governance"
branch_labels = None
depends_on = None

_NEW_TABLES = ["source_system", "schedule_signoff"]
_NEW_COLS = [
    ("element_governance", sa.Column("override_value", sa.Numeric(24, 3), nullable=True)),
    ("element_governance", sa.Column("override_reason", sa.Text(), server_default="")),
    ("remediation_proposal", sa.Column("maker_rationale", sa.Text(), server_default="")),
    ("remediation_proposal", sa.Column("checker_comment", sa.Text(), server_default="")),
]


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, tables=[Base.metadata.tables[t] for t in _NEW_TABLES])
    insp = sa.inspect(bind)
    for table, col in _NEW_COLS:
        existing = {c["name"] for c in insp.get_columns(table)}
        if col.name not in existing:
            op.add_column(table, col)


def downgrade() -> None:
    for table, col in reversed(_NEW_COLS):
        op.drop_column(table, col.name)
    Base.metadata.drop_all(bind=op.get_bind(), tables=[Base.metadata.tables[t] for t in _NEW_TABLES])
