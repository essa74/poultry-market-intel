"""create news_articles table

Revision ID: 009
Revises: 008
Create Date: 2026-05-26
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "news_articles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("url", sa.String(1000), nullable=False),
        sa.Column("source_name", sa.String(200), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True, index=True),
        sa.Column("image_url", sa.String(1000), nullable=True),
        sa.Column("category", sa.String(100), nullable=True, index=True),
        sa.Column("keywords", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url"),
    )


def downgrade() -> None:
    op.drop_table("news_articles")
