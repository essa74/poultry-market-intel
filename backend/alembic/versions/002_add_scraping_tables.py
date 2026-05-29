"""add scraping tables

Revision ID: 002
Revises: 001
Create Date: 2026-05-24
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scraping_sources",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column(
            "source_type",
            sa.Enum("website", "facebook", "telegram", name="scrapingsourcetype"),
            nullable=False,
        ),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("health_score", sa.Float(), server_default=sa.text("100.0")),
        sa.Column("consecutive_failures", sa.Integer(), server_default=sa.text("0")),
        sa.Column("last_success_at", sa.DateTime(), nullable=True),
        sa.Column("last_failure_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "scraping_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("scraping_sources.id"), nullable=False),
        sa.Column("job_id", sa.String(100), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "running", "success", "failed", "partial", name="scrapingjobstatus"),
            nullable=False,
        ),
        sa.Column("records_collected", sa.Integer(), server_default=sa.text("0")),
        sa.Column("records_skipped", sa.Integer(), server_default=sa.text("0")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scraping_logs_job_id"), "scraping_logs", ["job_id"])

    op.create_table(
        "raw_extracted_prices",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("scraping_sources.id"), nullable=False),
        sa.Column("log_id", sa.Integer(), sa.ForeignKey("scraping_logs.id"), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("product_type", sa.String(50), nullable=True),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(10), server_default="EGP"),
        sa.Column("unit", sa.String(30), nullable=True),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("recorded_date", sa.Date(), nullable=True),
        sa.Column("extraction_method", sa.String(50), server_default="regex"),
        sa.Column("confidence", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("is_normalized", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("is_duplicate", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("duplicate_of_id", sa.Integer(), nullable=True),
        sa.Column("matched_record_id", sa.Integer(), sa.ForeignKey("price_records.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("raw_extracted_prices")
    op.drop_index(op.f("ix_scraping_logs_job_id"), table_name="scraping_logs")
    op.drop_table("scraping_logs")
    op.drop_table("scraping_sources")
    op.execute("DROP TYPE IF EXISTS scrapingsourcetype")
    op.execute("DROP TYPE IF EXISTS scrapingjobstatus")
