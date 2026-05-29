"""add error_type and error_traceback to scraping_logs

Revision ID: 004
Revises: 003
Create Date: 2026-05-25
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("scraping_logs", sa.Column("error_type", sa.String(100), nullable=True))
    op.add_column("scraping_logs", sa.Column("error_traceback", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("scraping_logs", "error_traceback")
    op.drop_column("scraping_logs", "error_type")
