"""element governance table (data-layer maker-checker)

Adds the per-instance/per-element governance state used by the shared Data
Layer. Uses metadata.create_all so the table definition stays in lockstep with
the ORM model (single-pack MVP baseline pattern).

Revision ID: 0002_element_governance
Revises: 0001_initial
Create Date: 2026-06-09
"""
from alembic import op

import app.models  # noqa: F401  register models on Base
from app.core.db import Base

revision = "0002_element_governance"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), tables=[
        Base.metadata.tables["element_governance"],
    ])


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), tables=[
        Base.metadata.tables["element_governance"],
    ])
