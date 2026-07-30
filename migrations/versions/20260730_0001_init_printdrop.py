"""Initial PrintDrop schema."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260730_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    user_role = sa.Enum("ADMIN", "USER", name="user_role")
    print_mode = sa.Enum("COLOR", "BW", name="print_mode")
    print_job_status = sa.Enum(
        "PENDING",
        "APPROVED",
        "QUEUED",
        "PRINTING",
        "COMPLETED",
        "FAILED",
        "REJECTED",
        "CANCELLED",
        name="print_job_status",
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("username_normalized", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("daily_page_quota", sa.Integer(), nullable=False),
        sa.Column("weekly_page_quota", sa.Integer(), nullable=False),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("print_mode", print_mode, nullable=False, server_default="BW"),
        sa.Column("must_change_password", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("username", name="uq_users_username"),
        sa.UniqueConstraint("username_normalized", name="uq_users_username_normalized"),
    )
    op.create_index("ix_users_username_normalized", "users", ["username_normalized"])

    op.create_table(
        "print_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("job_uuid", sa.String(length=36), nullable=False),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("extension", sa.String(length=10), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("copies", sa.Integer(), nullable=False),
        sa.Column("status", print_job_status, nullable=False),
        sa.Column("cups_job_id", sa.String(length=64), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("retried_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retried_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.UniqueConstraint("job_uuid", name="uq_print_jobs_job_uuid"),
    )
    op.create_index("ix_print_jobs_user_id", "print_jobs", ["user_id"])
    op.create_index("ix_print_jobs_status", "print_jobs", ["status"])
    op.create_index("ix_print_jobs_submitted_at", "print_jobs", ["submitted_at"])
    op.create_index("ix_print_jobs_cups_job_id", "print_jobs", ["cups_job_id"])
    op.create_index("ix_print_jobs_status_submitted_at", "print_jobs", ["status", "submitted_at"])
    op.create_index("ix_print_jobs_user_id_submitted_at", "print_jobs", ["user_id", "submitted_at"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("target_type", sa.String(length=80), nullable=False),
        sa.Column("target_id", sa.String(length=80), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_target", "audit_logs", ["target_type", "target_id"])
    op.create_index("ix_audit_logs_actor_created", "audit_logs", ["actor_user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_actor_created", table_name="audit_logs")
    op.drop_index("ix_audit_logs_target", table_name="audit_logs")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_print_jobs_user_id_submitted_at", table_name="print_jobs")
    op.drop_index("ix_print_jobs_status_submitted_at", table_name="print_jobs")
    op.drop_index("ix_print_jobs_cups_job_id", table_name="print_jobs")
    op.drop_index("ix_print_jobs_submitted_at", table_name="print_jobs")
    op.drop_index("ix_print_jobs_status", table_name="print_jobs")
    op.drop_index("ix_print_jobs_user_id", table_name="print_jobs")
    op.drop_table("print_jobs")

    op.drop_index("ix_users_username_normalized", table_name="users")
    op.drop_table("users")
