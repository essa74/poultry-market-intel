"""add raw_post_text to price_records

Revision ID: 011
Revises: 010
Create Date: 2026-05-28
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("price_records", sa.Column("raw_post_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("price_records", "raw_post_text")
