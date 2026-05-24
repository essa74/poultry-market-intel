"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-24
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "price_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product_type", sa.String(50), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(10), server_default="EGP"),
        sa.Column("unit", sa.String(30), nullable=False),
        sa.Column("market", sa.String(100), nullable=True),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("recorded_date", sa.Date(), nullable=False),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_price_records_product_type"), "price_records", ["product_type"])
    op.create_index(op.f("ix_price_records_recorded_date"), "price_records", ["recorded_date"])

    op.create_table(
        "holiday_calendar",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("holiday_type", sa.String(50), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("date"),
    )

    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product_type", sa.String(50), nullable=False),
        sa.Column("predicted_price", sa.Float(), nullable=False),
        sa.Column("predicted_date", sa.Date(), nullable=False),
        sa.Column("confidence_lower", sa.Float(), nullable=True),
        sa.Column("confidence_upper", sa.Float(), nullable=True),
        sa.Column("model_version", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_predictions_product_type"), "predictions", ["product_type"])


def downgrade() -> None:
    op.drop_index(op.f("ix_predictions_product_type"), table_name="predictions")
    op.drop_table("predictions")
    op.drop_table("holiday_calendar")
    op.drop_index(op.f("ix_price_records_recorded_date"), table_name="price_records")
    op.drop_index(op.f("ix_price_records_product_type"), table_name="price_records")
    op.drop_table("price_records")
