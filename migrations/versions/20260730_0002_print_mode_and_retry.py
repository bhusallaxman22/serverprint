"""Add persistent print mode and retry fields."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260730_0002"
down_revision = "20260730_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "print_mode" not in user_columns:
        print_mode = sa.Enum("COLOR", "BW", name="print_mode")
        print_mode.create(bind, checkfirst=True)
        op.add_column(
            "users", sa.Column("print_mode", print_mode, nullable=False, server_default="BW")
        )
        op.alter_column("users", "print_mode", server_default=None)
    if "requires_approval" not in user_columns:
        op.add_column(
            "users",
            sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default=sa.true()),
        )
        op.alter_column("users", "requires_approval", server_default=None)

    job_columns = {column["name"] for column in inspector.get_columns("print_jobs")}
    if "retry_count" not in job_columns:
        op.add_column(
            "print_jobs", sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0")
        )
        op.alter_column("print_jobs", "retry_count", server_default=None)
    if "retried_at" not in job_columns:
        op.add_column(
            "print_jobs", sa.Column("retried_at", sa.DateTime(timezone=True), nullable=True)
        )
    if "retried_by_user_id" not in job_columns:
        op.add_column("print_jobs", sa.Column("retried_by_user_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_print_jobs_retried_by_user_id_users",
            "print_jobs",
            "users",
            ["retried_by_user_id"],
            ["id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    job_columns = {column["name"] for column in inspector.get_columns("print_jobs")}
    if "retried_by_user_id" in job_columns:
        op.drop_constraint(
            "fk_print_jobs_retried_by_user_id_users", "print_jobs", type_="foreignkey"
        )
        op.drop_column("print_jobs", "retried_by_user_id")
    if "retried_at" in job_columns:
        op.drop_column("print_jobs", "retried_at")
    if "retry_count" in job_columns:
        op.drop_column("print_jobs", "retry_count")

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "requires_approval" in user_columns:
        op.drop_column("users", "requires_approval")
    if "print_mode" in user_columns:
        op.drop_column("users", "print_mode")
