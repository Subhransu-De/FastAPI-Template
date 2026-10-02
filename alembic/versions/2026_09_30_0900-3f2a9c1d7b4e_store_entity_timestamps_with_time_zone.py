"""Store entity timestamps with time zone

Revision ID: 3f2a9c1d7b4e
Revises: 97f7686bdccd
Create Date: 2026-09-30 09:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "3f2a9c1d7b4e"
down_revision: str | Sequence[str] | None = "97f7686bdccd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TIMESTAMP_COLUMNS = ("created_at", "updated_at")


def upgrade() -> None:
    for column in _TIMESTAMP_COLUMNS:
        op.alter_column(
            "entities",
            column,
            type_=sa.DateTime(timezone=True),
            existing_type=sa.DateTime(),
            existing_nullable=False,
            existing_server_default=sa.text("now()"),
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )


def downgrade() -> None:
    for column in _TIMESTAMP_COLUMNS:
        op.alter_column(
            "entities",
            column,
            type_=sa.DateTime(),
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
            existing_server_default=sa.text("now()"),
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )
