"""Extend official-account publication attempts for real sends."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009_official_account_real_send"
down_revision = "0008_official_account_provider_boundary"
branch_labels = None
depends_on = None

old_provider_mode_enum = sa.Enum(
    "disabled",
    "dry_run",
    name="officialaccountprovidermode",
    native_enum=False,
)
new_provider_mode_enum = sa.Enum(
    "disabled",
    "dry_run",
    "real",
    name="officialaccountprovidermode",
    native_enum=False,
)
old_attempt_status_enum = sa.Enum(
    "started",
    "previewed",
    "failed",
    name="digestpublicationattemptstatus",
    native_enum=False,
)
new_attempt_status_enum = sa.Enum(
    "started",
    "previewed",
    "sent",
    "failed",
    name="digestpublicationattemptstatus",
    native_enum=False,
)


def upgrade() -> None:
    with op.batch_alter_table("digest_publication_attempts", recreate="always") as batch_op:
        batch_op.alter_column(
            "provider_mode",
            existing_type=old_provider_mode_enum,
            type_=new_provider_mode_enum,
            existing_nullable=False,
        )
        batch_op.alter_column(
            "status",
            existing_type=old_attempt_status_enum,
            type_=new_attempt_status_enum,
            existing_nullable=False,
        )
        batch_op.add_column(sa.Column("external_message_id", sa.String(length=255), nullable=True))
        batch_op.add_column(
            sa.Column("provider_response_code", sa.String(length=100), nullable=True)
        )
        batch_op.add_column(sa.Column("provider_response_message", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("digest_publication_attempts", recreate="always") as batch_op:
        batch_op.alter_column(
            "provider_mode",
            existing_type=new_provider_mode_enum,
            type_=old_provider_mode_enum,
            existing_nullable=False,
        )
        batch_op.alter_column(
            "status",
            existing_type=new_attempt_status_enum,
            type_=old_attempt_status_enum,
            existing_nullable=False,
        )
        batch_op.drop_column("provider_response_message")
        batch_op.drop_column("provider_response_code")
        batch_op.drop_column("external_message_id")
