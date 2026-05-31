import logging
import traceback as tb
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from app.db.session import get_db
from app.models import NewsArticle
from app.services.news_scraper import (
    refresh_all_news, refresh_all_news_debug, get_market_indicators,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class NewsArticleResponse(BaseModel):
    id: int
    title: str
    summary: Optional[str] = None
    url: str
    source_name: str
    published_at: Optional[datetime] = None
    image_url: Optional[str] = None
    category: Optional[str] = None
    keywords: Optional[str] = None
    relevance_score: Optional[int] = None
    sentiment: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NewsRefreshResponse(BaseModel):
    message: str
    new_articles: int
    source: str = "news_scraper"


class DebugSourceInfo(BaseModel):
    source_name: str
    url: str
    status_code: Optional[int] = None
    html_length: int = 0
    candidates_found: int = 0
    accepted_count: int = 0
    rejected_count: int = 0
    rejection_reasons: list[dict] = []
    sample_titles: list[str] = []
    errors: list[str] = []


class NewsDebugResponse(BaseModel):
    total_new_articles: int
    sources: list[DebugSourceInfo]


class MarketIndicatorsResponse(BaseModel):
    today_count: int
    dominant_category: Optional[str] = None
    market_sentiment: str = "محايد"
    category_distribution: dict[str, int] = {}
    sentiment_distribution: dict[str, int] = {}


@router.get("/", response_model=list[NewsArticleResponse])
async def list_news(
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    category: Optional[str] = Query(None),
    min_score: int = Query(75, ge=0, le=100),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(NewsArticle).where(
        NewsArticle.relevance_score >= min_score,
    ).order_by(
        NewsArticle.published_at.desc().nullslast(),
        NewsArticle.relevance_score.desc(),
        NewsArticle.created_at.desc(),
    )
    if category:
        stmt = stmt.where(NewsArticle.category == category)
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/latest", response_model=list[NewsArticleResponse])
async def latest_news(
    limit: int = Query(5, le=20),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(NewsArticle)
        .where(NewsArticle.relevance_score >= 75)
        .order_by(NewsArticle.published_at.desc().nullslast(), NewsArticle.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.post("/refresh")
async def refresh_news(
    db: AsyncSession = Depends(get_db),
):
    try:
        count = await refresh_all_news(db)
        return NewsRefreshResponse(
            message=f"تم تحديث الأخبار: {count} مقال جديد",
            new_articles=count,
        )
    except Exception as e:
        tb_str = "".join(tb.format_exception(type(e), e, e.__traceback__))
        logger.error(f"News refresh failed: {e}\n{tb_str}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "traceback": tb_str,
            },
        )


@router.get("/debug", response_model=NewsDebugResponse)
async def debug_news(
    db: AsyncSession = Depends(get_db),
):
    total, sources = await refresh_all_news_debug(db)
    return NewsDebugResponse(total_new_articles=total, sources=sources)


@router.get("/indicators", response_model=MarketIndicatorsResponse)
async def market_indicators(
    db: AsyncSession = Depends(get_db),
):
    return await get_market_indicators(db)
