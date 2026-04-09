"""Add items table

Revision ID: e568be01a144
Revises: 5a919dec6e83
Create Date: 2026-04-09 14:20:23.550959

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e568be01a144"
down_revision: str | Sequence[str] | None = "5a919dec6e83"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "items",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("owner_uid", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_uid"],
            ["users.uid"],
            name=op.f("fk_items_owner_uid_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_items")),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("items")
