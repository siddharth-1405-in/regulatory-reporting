"""drop manual override columns from element_governance

The Data Foundation no longer supports manual value overrides — report-ready
data elements are produced upstream (ingestion + rule engine) and only attested
through maker submission / checker sign-off. Drops override_value and
override_reason. Idempotent and safe on PostgreSQL and SQLite.

Revision ID: 0004_drop_element_override
Revises: 0003_target_state
Create Date: 2026-06-16
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_drop_element_override"
down_revision = "0003_target_state"
branch_labels = None
depends_on = None

_DROP_COLS = ["override_value", "override_reason"]


def upgrade() -> None:
    bind = op.get_bind()
    # Normalise legacy statuses that no longer exist in the lifecycle. 'edited'
    # and 'frozen' were intermediate override/freeze states; they collapse back
    # to 'draft' (ready for submission) now that values are never overridden.
    bind.execute(sa.text(
        "UPDATE element_governance SET status = 'draft' "
        "WHERE status IN ('edited', 'frozen')"))
    existing = {c["name"] for c in sa.inspect(bind).get_columns("element_governance")}
    with op.batch_alter_table("element_governance") as batch:
        for name in _DROP_COLS:
            if name in existing:
                batch.drop_column(name)


def downgrade() -> None:
    bind = op.get_bind()
    existing = {c["name"] for c in sa.inspect(bind).get_columns("element_governance")}
    with op.batch_alter_table("element_governance") as batch:
        if "override_value" not in existing:
            batch.add_column(sa.Column("override_value", sa.Numeric(24, 3), nullable=True))
        if "override_reason" not in existing:
            batch.add_column(sa.Column("override_reason", sa.Text(), server_default=""))
