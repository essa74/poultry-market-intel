"""add relevance_score and sentiment to news_articles

Revision ID: 010
Revises: 009
Create Date: 2026-05-26
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("news_articles", sa.Column("relevance_score", sa.Integer(), nullable=True))
    op.add_column("news_articles", sa.Column("sentiment", sa.String(20), nullable=True))
    op.execute("UPDATE news_articles SET relevance_score = 50")
    op.create_index("ix_news_articles_relevance_score", "news_articles", ["relevance_score"])
    op.create_index("ix_news_articles_sentiment", "news_articles", ["sentiment"])


def downgrade() -> None:
    op.drop_index("ix_news_articles_sentiment", table_name="news_articles")
    op.drop_index("ix_news_articles_relevance_score", table_name="news_articles")
    op.drop_column("news_articles", "sentiment")
    op.drop_column("news_articles", "relevance_score")
