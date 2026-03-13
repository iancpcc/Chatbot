"""Initial schema

Revision ID: 20260312_01
Revises:
Create Date: 2026-03-12 21:30:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260312_01"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "services",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id", "tenant_id"),
    )
    op.create_index("ix_services_tenant_id", "services", ["tenant_id"], unique=False)

    op.create_table(
        "resources",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id", "tenant_id"),
    )
    op.create_index("ix_resources_tenant_id", "resources", ["tenant_id"], unique=False)

    op.create_table(
        "bookings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=120), nullable=False),
        sa.Column("service_id", sa.String(length=36), nullable=False),
        sa.Column("resource_id", sa.String(length=36), nullable=False),
        sa.Column("customer_name", sa.String(length=255), nullable=False),
        sa.Column("customer_contact", sa.String(length=255), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bookings_tenant_id", "bookings", ["tenant_id"], unique=False)
    op.create_index("ix_bookings_service_id", "bookings", ["service_id"], unique=False)
    op.create_index("ix_bookings_resource_id", "bookings", ["resource_id"], unique=False)
    op.create_index("ix_bookings_status", "bookings", ["status"], unique=False)

    op.create_table(
        "conversations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=120), nullable=False),
        sa.Column("user_id", sa.String(length=120), nullable=False),
        sa.Column("channel", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("state", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_conversations_tenant_id",
        "conversations",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_conversations_user_id",
        "conversations",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_conversations_channel",
        "conversations",
        ["channel"],
        unique=False,
    )
    op.create_index(
        "ix_conversations_status",
        "conversations",
        ["status"],
        unique=False,
    )
    op.create_index("ix_conversations_type", "conversations", ["type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_conversations_type", table_name="conversations")
    op.drop_index("ix_conversations_status", table_name="conversations")
    op.drop_index("ix_conversations_channel", table_name="conversations")
    op.drop_index("ix_conversations_user_id", table_name="conversations")
    op.drop_index("ix_conversations_tenant_id", table_name="conversations")
    op.drop_table("conversations")

    op.drop_index("ix_bookings_status", table_name="bookings")
    op.drop_index("ix_bookings_resource_id", table_name="bookings")
    op.drop_index("ix_bookings_service_id", table_name="bookings")
    op.drop_index("ix_bookings_tenant_id", table_name="bookings")
    op.drop_table("bookings")

    op.drop_index("ix_resources_tenant_id", table_name="resources")
    op.drop_table("resources")

    op.drop_index("ix_services_tenant_id", table_name="services")
    op.drop_table("services")
