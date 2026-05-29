"""add raw_product_name and product_group columns

Revision ID: 007
Revises: 006
Create Date: 2026-05-25
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import ProgrammingError


revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    cols = {c["name"] for c in inspector.get_columns(table)}
    return column in cols


def upgrade() -> None:
    if not _column_exists("price_records", "raw_product_name"):
        op.add_column("price_records", sa.Column("raw_product_name", sa.String(500), nullable=True))
    if not _column_exists("price_records", "product_group"):
        op.add_column("price_records", sa.Column("product_group", sa.String(30), nullable=True))
    if not _column_exists("raw_extracted_prices", "product_group"):
        op.add_column("raw_extracted_prices", sa.Column("product_group", sa.String(30), nullable=True))


def downgrade() -> None:
    if _column_exists("raw_extracted_prices", "product_group"):
        op.drop_column("raw_extracted_prices", "product_group")
    if _column_exists("price_records", "product_group"):
        op.drop_column("price_records", "product_group")
    if _column_exists("price_records", "raw_product_name"):
        op.drop_column("price_records", "raw_product_name")
