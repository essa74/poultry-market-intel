"""add debug counters to scraping_logs

Revision ID: 006
Revises: 005
Create Date: 2026-05-25
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("scraping_logs", sa.Column("valid_saved", sa.Integer(), server_default=sa.text("0")))
    op.add_column("scraping_logs", sa.Column("duplicates_skipped", sa.Integer(), server_default=sa.text("0")))
    op.add_column("scraping_logs", sa.Column("invalid_skipped", sa.Integer(), server_default=sa.text("0")))


def downgrade() -> None:
    op.drop_column("scraping_logs", "invalid_skipped")
    op.drop_column("scraping_logs", "duplicates_skipped")
    op.drop_column("scraping_logs", "valid_saved")
