"""add debug fields to scraping_logs and is_failed_sample to raw_extracted_prices

Revision ID: 003
Revises: 002
Create Date: 2026-05-25
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("scraping_logs", sa.Column("fetched_text", sa.Text(), nullable=True))
    op.add_column("scraping_logs", sa.Column("html_snapshot_path", sa.String(500), nullable=True))
    op.add_column("scraping_logs", sa.Column("raw_content_length", sa.Integer(), nullable=True))
    op.add_column("scraping_logs", sa.Column("selector_matches", sa.Integer(), nullable=True))
    op.add_column("raw_extracted_prices", sa.Column("is_failed_sample", sa.Boolean(), server_default=sa.text("false")))


def downgrade() -> None:
    op.drop_column("scraping_logs", "fetched_text")
    op.drop_column("scraping_logs", "html_snapshot_path")
    op.drop_column("scraping_logs", "raw_content_length")
    op.drop_column("scraping_logs", "selector_matches")
    op.drop_column("raw_extracted_prices", "is_failed_sample")
