"""Add items table

Revision ID: 56752a35789e
Revises: 219c69f50645
Create Date: 2026-02-28 01:10:08.448674

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "56752a35789e"
down_revision: str | Sequence[str] | None = "219c69f50645"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "item",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("owner_uid", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_uid"],
            ["users.uid"],
            name=op.f("fk_item_owner_uid_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_item")),
    )

    op.create_index(op.f("ix_item_id"), "item", ["id"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_item_id"), table_name="item")
    op.drop_table("item")
