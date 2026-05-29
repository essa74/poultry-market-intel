import logging
import re
from datetime import datetime, timedelta, date
from typing import Optional
from collections import Counter

import httpx
import feedparser
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func

from app.models import NewsArticle

logger = logging.getLogger(__name__)

MIN_RELEVANCE_SCORE = 75

REQUIRED_STRONG_KEYWORDS = [
    "كتاكيت", "كتكوت", "بيض مخصب", "بيض تفريخ",
    "أعلاف", "الذرة", "صويا", "فول الصويا",
    "بورصة الدواجن", "المفرخات", "شركات الدواجن",
    "الأمهات", "تكلفة الإنتاج",
]

HIGH_PRIORITY_KEYWORDS = [
    "كتاكيت", "كتكوت", "بيض مخصب", "بيض تفريخ",
    "أعلاف دواجن", "الذرة", "فول الصويا", "شركات الدواجن",
    "المفرخات", "الأمهات", "تكلفة الإنتاج",
    "قطاع الدواجن", "الاستيراد", "التصدير",
    "مزارع التسمين", "بورصة الدواجن", "أسعار الكتاكيت",
]

MEDIUM_PRIORITY_KEYWORDS = [
    "أسعار الأعلاف", "سعر العلف", "سعر الكتكوت",
    "التسمين", "تفريخ", "مزرعة دواجن", "إنتاج البيض",
    "الدواجن", "أسعار الدواجن", "اسعار الدواجن",
    "البورصة", "الإنتاج",
]

LOW_PRIORITY_KEYWORDS = [
    "دواجن", "فراخ", "سعر الفراخ", "سعر الدواجن",
    "كيلو الدواجن", "الفراخ البيضاء", "البيض اليوم",
    "أسعار البيض", "سعر البيض", "سعر كرتونة البيض",
    "اسعار البيض", "صوص", "وركي دواجن",
    "poultry", "broiler", "hatching eggs",
    "day old chick", "أسواق الماشية", "إنتاج بيض",
    "كرتونة البيض",
]

REJECT_PHRASES = [
    "حملات تموينية", "غير صالحة للاستهلاك", "ضبط",
    "فساد غذائي", "وصفات", "مطاعم", "استهلاك آدمي",
    "محقونة", "مضبوطات", "الطبخ", "طريقة عمل",
    "دجاج محمر", "فراخ مشوية", "منيو", "اكلات",
    "سندوتشات", "ركن الشيف", "شوربة",
    "سعر كيلو الدواجن", "الفراخ البيضاء بالكيلو",
    "سعر كيلو الفراخ", "كرتونة البيض",
    "البيض الاستهلاكي", "بيض المائدة",
]

CATEGORY_RULES = [
    (["كتاكيت", "كتكوت", "سعر الكتكوت", "أسعار الكتاكيت"], "أسعار الكتاكيت"),
    (["بيض مخصب", "بيض تفريخ", "بيض أمهات"], "بيض مخصب"),
    (["أعلاف", "الذرة", "صويا", "فول الصويا", "سعر العلف", "أسعار الأعلاف"], "أعلاف"),
    (["بورصة الدواجن", "البورصة", "الاستثمار", "مؤشرات", "الاقتصاد", "الدولار"], "بورصة ومؤشرات"),
    (["شركات الدواجن", "المفرخات", "الأمهات", "التسمين", "قطاع الدواجن",
      "الإنتاج", "تكلفة الإنتاج", "الاستيراد", "التصدير", "مزارع التسمين"], "شركات وإنتاج"),
]

SENTIMENT_POSITIVE = [
    "انخفاض الأعلاف", "انخفاض أسعار", "تراجع أسعار", "انخفاض سعر",
    "زيادة الإنتاج", "ارتفاع الإنتاج", "استقرار الأسعار",
    "استقرار سعر", "انخفاض الدولار", "تراجع الدولار",
    "زيادة الصادرات", "ارتفاع الصادرات", "دعم الحكومة",
    "افتتاح مزرعة", "توسعات", "استثمار جديد",
]

SENTIMENT_NEGATIVE = [
    "ارتفاع الأعلاف", "ارتفاع أسعار", "ارتفاع سعر", "زيادة الأسعار",
    "نقص الإنتاج", "انخفاض الإنتاج", "تراجع الإنتاج",
    "ارتفاع الدولار", "زيادة الدولار", "إغلاق مزارع",
    "نقص الكتاكيت", "نقص الأعلاف", "أزمة", "ازمة",
    "خسائر", "توقف", "نفوق", "مرض",
]

SOURCE_PRIORITY = {
    "Google News — دواجن مصر": "high",
    "Google News — بورصة الدواجن": "high",
    "Google News — بيض مخصب وأعلاف": "high",
    "Google News — كتاكيت مصر": "high",
    "Google News — أعلاف دواجن": "high",
    "المال — دواجن": "high",
    "وزارة الزراعة — دواجن": "high",
    "اليوم السابع — دواجن": "medium",
    "مصراوي — دواجن": "medium",
}

SOURCE_PRIORITY_BONUS = {"high": 10, "medium": 5, "low": 0}


def clean_html(text: str) -> str:
    if not text:
        return ""
    soup = BeautifulSoup(text, "lxml")
    return soup.get_text(separator=" ", strip=True)


def compute_relevance(title: str, summary: str, source_name: str) -> int:
    text = f"{title} {summary}"

    has_strong = any(kw in text for kw in REQUIRED_STRONG_KEYWORDS)
    if not has_strong:
        return 0

    for rp in REJECT_PHRASES:
        if rp in text:
            return 0

    score = 0

    for kw in HIGH_PRIORITY_KEYWORDS:
        if kw in text:
            score += 30

    for kw in MEDIUM_PRIORITY_KEYWORDS:
        if kw in text:
            score += 20

    for kw in LOW_PRIORITY_KEYWORDS:
        if kw in text:
            score += 10

    bonus = SOURCE_PRIORITY_BONUS.get(SOURCE_PRIORITY.get(source_name, "low"), 0)
    if bonus:
        score += bonus

    return min(score, 100)


def classify_category(title: str, summary: str) -> str:
    text = f"{title} {summary}"
    for keywords, cat in CATEGORY_RULES:
        for kw in keywords:
            if kw in text:
                return cat
    return "أسعار"


def compute_sentiment(title: str, summary: str) -> str:
    text = f"{title} {summary}"
    pos_score = 0
    neg_score = 0
    for kw in SENTIMENT_POSITIVE:
        if kw in text:
            pos_score += 1
    for kw in SENTIMENT_NEGATIVE:
        if kw in text:
            neg_score += 1
    if pos_score > neg_score:
        return "إيجابي"
    elif neg_score > pos_score:
        return "سلبي"
    return "محايد"


class SourceDebugInfo:
    def __init__(self, source_name: str, url: str):
        self.source_name = source_name
        self.url = url
        self.status_code: Optional[int] = None
        self.html_length: int = 0
        self.candidates_found: int = 0
        self.accepted_count: int = 0
        self.rejected_count: int = 0
        self.rejection_reasons: list[dict] = []
        self.sample_titles: list[str] = []
        self.errors: list[str] = []

    def to_dict(self):
        return {
            "source_name": self.source_name,
            "url": self.url,
            "status_code": self.status_code,
            "html_length": self.html_length,
            "candidates_found": self.candidates_found,
            "accepted_count": self.accepted_count,
            "rejected_count": self.rejected_count,
            "rejection_reasons": self.rejection_reasons[:20],
            "sample_titles": self.sample_titles[:5],
            "errors": self.errors[:5],
        }


def extract_article_info(
    element: BeautifulSoup, source: dict, base_url: str
) -> Optional[dict]:
    link_el = element.select_one(source["link_selector"]) if source.get("link_selector") else element
    if not link_el:
        return None
    href = link_el.get("href", "")
    if not href:
        return None
    if href.startswith("/"):
        href = base_url.rstrip("/") + href
    elif not href.startswith("http"):
        href = base_url.rstrip("/") + "/" + href

    title_el = element.select_one(source["title_selector"]) if source.get("title_selector") else element
    title = title_el.get_text(strip=True) if title_el else ""
    if not title:
        return None

    summary_el = element.select_one(source["summary_selector"]) if source.get("summary_selector") else None
    summary = summary_el.get_text(strip=True) if summary_el else ""

    return {"title": title, "url": href, "summary": summary}


async def scrape_rss_feed(source: dict, db: AsyncSession, debug: Optional[SourceDebugInfo] = None) -> int:
    url = source["url"]
    parsed_count = 0

    try:
        feed = feedparser.parse(url)
    except Exception as e:
        msg = f"RSS parse error: {e}"
        logger.warning(f"{source['name']}: {msg}")
        if debug:
            debug.errors.append(msg)
        return 0

    if debug:
        debug.status_code = 200
        entries = feed.entries if hasattr(feed, "entries") else []
        debug.candidates_found = len(entries)

    for entry in feed.entries:
        title = entry.get("title", "")
        link = entry.get("link", "")
        raw_summary = entry.get("summary", "") or entry.get("description", "") or ""
        summary = clean_html(raw_summary)
        published = entry.get("published_parsed") or entry.get("updated_parsed")

        if not title or not link:
            if debug:
                debug.rejected_count += 1
                debug.rejection_reasons.append({"title": str(title)[:50], "reason": "missing title or link"})
            continue

        pub_date = None
        if published:
            try:
                pub_date = datetime(*published[:6])
            except Exception:
                pub_date = datetime.utcnow()
        else:
            pub_date = datetime.utcnow()

        relevance = compute_relevance(title, summary, source["name"])
        if relevance < MIN_RELEVANCE_SCORE:
            if debug:
                debug.rejected_count += 1
                debug.rejection_reasons.append({"title": title[:80], "reason": f"low relevance ({relevance})"})
            continue

        existing = await db.execute(
            select(NewsArticle).where(NewsArticle.url == link)
        )
        if existing.first():
            if debug:
                debug.rejected_count += 1
                debug.rejection_reasons.append({"title": title[:80], "reason": "duplicate URL"})
            continue

        category = classify_category(title, summary)
        sentiment = compute_sentiment(title, summary)

        article = NewsArticle(
            title=title[:500],
            summary=summary[:500] if summary else None,
            url=link[:1000],
            source_name=source["name"],
            published_at=pub_date,
            category=category,
            keywords=", ".join(kw for kw in HIGH_PRIORITY_KEYWORDS + MEDIUM_PRIORITY_KEYWORDS if kw in f"{title} {summary}"),
            relevance_score=relevance,
            sentiment=sentiment,
        )
        db.add(article)
        parsed_count += 1
        if debug:
            debug.sample_titles.append(f"[{relevance}] {title[:60]}")

    if parsed_count:
        try:
            await db.commit()
        except Exception as e:
            logger.error(f"Commit failed for {source['name']}: {e}")
            await db.rollback()
            if debug:
                debug.errors.append(f"DB commit error: {e}")
            return 0
        logger.info(f"News: {parsed_count} new articles from {source['name']} (RSS)")

    if debug:
        debug.accepted_count = parsed_count

    return parsed_count


async def scrape_source(source: dict, db: AsyncSession, debug: Optional[SourceDebugInfo] = None) -> int:
    url = source["url"]
    parsed_count = 0

    if source.get("type") == "rss":
        return await scrape_rss_feed(source, db, debug)

    resp = None
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; NewsBot/1.0)"})
            resp.raise_for_status()
    except Exception as e:
        msg = f"HTTP fetch error: {e}"
        logger.warning(f"{source['name']}: {msg}")
        if debug:
            err_resp = getattr(e, "response", None)
            code = err_resp.status_code if err_resp is not None else None
            if code is None and resp is not None:
                code = resp.status_code
            debug.status_code = code or 0
            debug.errors.append(msg)
        return 0

    html_len = len(resp.text)
    logger.info(f"{source['name']}: HTTP {resp.status_code}, HTML length {html_len}")

    if debug:
        debug.status_code = resp.status_code
        debug.html_length = html_len

    try:
        soup = BeautifulSoup(resp.text, "lxml")
    except Exception as e:
        msg = f"HTML parse error: {e}"
        logger.warning(f"{source['name']}: {msg}")
        if debug:
            debug.errors.append(msg)
        return 0

    base_url = f"{resp.url.scheme}://{resp.url.host}"
    elements = soup.select(source["selector"]) if source.get("selector") else [soup]

    if debug:
        debug.candidates_found = len(elements)
    logger.info(f"{source['name']}: {len(elements)} candidate elements from selector '{source.get('selector')}'")

    for el in elements:
        info = extract_article_info(el, source, base_url)
        if not info:
            if debug:
                debug.rejected_count += 1
                debug.rejection_reasons.append({"el_preview": str(el)[:80], "reason": "extract failed"})
            continue

        relevance = compute_relevance(info["title"], info.get("summary", ""), source["name"])
        if relevance < MIN_RELEVANCE_SCORE:
            if debug:
                debug.rejected_count += 1
                debug.rejection_reasons.append({"title": info["title"][:80], "reason": f"low relevance ({relevance})"})
            continue

        existing = await db.execute(
            select(NewsArticle).where(NewsArticle.url == info["url"])
        )
        if existing.first():
            if debug:
                debug.rejected_count += 1
                debug.rejection_reasons.append({"title": info["title"][:80], "reason": "duplicate URL"})
            continue

        category = classify_category(info["title"], info.get("summary", ""))
        sentiment = compute_sentiment(info["title"], info.get("summary", ""))

        article = NewsArticle(
            title=info["title"][:500],
            summary=info.get("summary", "")[:500] if info.get("summary") else None,
            url=info["url"][:1000],
            source_name=source["name"],
            published_at=datetime.utcnow(),
            category=category,
            keywords=", ".join(kw for kw in HIGH_PRIORITY_KEYWORDS + MEDIUM_PRIORITY_KEYWORDS if kw in f"{info['title']} {info.get('summary', '')}"),
            relevance_score=relevance,
            sentiment=sentiment,
        )
        db.add(article)
        parsed_count += 1
        if debug:
            debug.sample_titles.append(f"[{relevance}] {info['title'][:60]}")

    if parsed_count:
        try:
            await db.commit()
        except Exception as e:
            logger.error(f"Commit failed for {source['name']}: {e}")
            await db.rollback()
            if debug:
                debug.errors.append(f"DB commit error: {e}")
            return 0
        logger.info(f"News: {parsed_count} new articles from {source['name']}")

    if debug:
        debug.accepted_count = parsed_count

    return parsed_count


NEWS_SOURCES = [
    {
        "name": "Google News — دواجن مصر",
        "url": "https://news.google.com/rss/search?q=%D8%A8%D9%88%D8%B1%D8%B5%D8%A9+%D8%A7%D9%84%D8%AF%D9%88%D8%A7%D8%AC%D9%86+%D9%85%D8%B5%D8%B1&hl=ar&gl=EG&ceid=EG:ar",
        "type": "rss",
    },
    {
        "name": "Google News — بورصة الدواجن",
        "url": "https://news.google.com/rss/search?q=%D8%A8%D9%88%D8%B1%D8%B5%D8%A9+%D8%A7%D9%84%D8%AF%D9%88%D8%A7%D8%AC%D9%86&hl=ar&gl=EG&ceid=EG:ar",
        "type": "rss",
    },
    {
        "name": "Google News — بيض مخصب وأعلاف",
        "url": "https://news.google.com/rss/search?q=%D8%A8%D9%8A%D8%B6+%D9%85%D8%AE%D8%B5%D8%A8+%D8%A3%D8%B9%D9%84%D8%A7%D9%81+%D8%AF%D9%88%D8%A7%D8%AC%D9%86&hl=ar&gl=EG&ceid=EG:ar",
        "type": "rss",
    },
    {
        "name": "Google News — كتاكيت مصر",
        "url": "https://news.google.com/rss/search?q=%D8%A3%D8%B3%D8%B9%D8%A7%D8%B1+%D8%A7%D9%84%D9%83%D8%AA%D8%A7%D9%83%D9%8A%D8%AA+%D9%85%D8%B5%D8%B1&hl=ar&gl=EG&ceid=EG:ar",
        "type": "rss",
    },
    {
        "name": "Google News — أعلاف دواجن",
        "url": "https://news.google.com/rss/search?q=%D8%A3%D8%B9%D9%84%D8%A7%D9%81+%D8%AF%D9%88%D8%A7%D8%AC%D9%86+%D9%85%D8%B5%D8%B1&hl=ar&gl=EG&ceid=EG:ar",
        "type": "rss",
    },
    {
        "name": "المال — دواجن",
        "url": "https://almalnews.com/?s=%D8%AF%D9%88%D8%A7%D8%AC%D9%86",
        "selector": "article, .post, .item, .news-item, .search-result, .entry",
        "link_selector": "a",
        "title_selector": "h2, h3, .entry-title, .title",
        "summary_selector": ".summary, .excerpt, p, .entry-content",
    },
    {
        "name": "وزارة الزراعة — دواجن",
        "url": "https://www.agr-egypt.gov.eg/ar/Search?q=%D8%AF%D9%88%D8%A7%D8%AC%D9%86",
        "selector": "article, .item, .news-item, .search-result, .result-item, .post",
        "link_selector": "a",
        "title_selector": "h2, h3, .title, .headline",
        "summary_selector": ".summary, .description, p, .text",
    },
    {
        "name": "اليوم السابع — دواجن",
        "url": "https://www.youm7.com/Search?q=%D8%AF%D9%88%D8%A7%D8%AC%D9%86",
        "selector": ".item, .news-item, article, .search-item, .blog-item, li.item, .original-item",
        "link_selector": "a",
        "title_selector": "h2, h3, .title, .headline, a",
        "summary_selector": ".summary, .description, p, .body, .text",
    },
    {
        "name": "مصراوي — دواجن",
        "url": "https://www.masrawy.com/search?q=%D8%AF%D9%88%D8%A7%D8%AC%D9%86",
        "selector": "article, .news-item, .item, .post, .search-item, .result-item",
        "link_selector": "a",
        "title_selector": "h2, h3, .title, .headline",
        "summary_selector": ".summary, .description, p, .text",
    },
]


async def cleanup_low_relevance(db: AsyncSession) -> int:
    result = await db.execute(
        delete(NewsArticle).where(NewsArticle.relevance_score < MIN_RELEVANCE_SCORE)
    )
    await db.commit()
    deleted = result.rowcount if result.rowcount is not None else 0
    if deleted:
        logger.info(f"Cleaned up {deleted} low-relevance news articles (< {MIN_RELEVANCE_SCORE})")
    return deleted


async def refresh_all_news(db: AsyncSession) -> int:
    await cleanup_low_relevance(db)
    total = 0
    for source in NEWS_SOURCES:
        count = await scrape_source(source, db)
        total += count
    logger.info(f"News refresh complete: {total} new articles total")
    return total


async def refresh_all_news_debug(db: AsyncSession) -> tuple[int, list[dict]]:
    cleaned = await cleanup_low_relevance(db)
    total = 0
    debug_results = []
    for source in NEWS_SOURCES:
        debug = SourceDebugInfo(source["name"], source["url"])
        count = await scrape_source(source, db, debug)
        total += count
        debug_results.append(debug.to_dict())
    logger.info(f"News refresh complete: {total} new articles (cleaned {cleaned} old)")
    return total, debug_results


async def get_market_indicators(db: AsyncSession) -> dict:
    today = date.today()
    today_start = datetime(today.year, today.month, today.day)
    tomorrow_start = today_start + timedelta(days=1)

    today_count_q = select(func.count(NewsArticle.id)).where(
        NewsArticle.created_at >= today_start,
        NewsArticle.created_at < tomorrow_start,
        NewsArticle.relevance_score >= MIN_RELEVANCE_SCORE,
    )
    today_count = (await db.execute(today_count_q)).scalar() or 0

    category_q = select(NewsArticle.category, func.count(NewsArticle.id).label("cnt")).where(
        NewsArticle.relevance_score >= MIN_RELEVANCE_SCORE,
    ).group_by(NewsArticle.category).order_by(func.count(NewsArticle.id).desc())
    cat_rows = (await db.execute(category_q)).all()
    dominant_category = cat_rows[0][0] if cat_rows else None

    sentiment_q = select(NewsArticle.sentiment, func.count(NewsArticle.id).label("cnt")).where(
        NewsArticle.relevance_score >= MIN_RELEVANCE_SCORE,
    ).group_by(NewsArticle.sentiment).order_by(func.count(NewsArticle.id).desc())
    sent_rows = (await db.execute(sentiment_q)).all()
    dominant_sentiment = sent_rows[0][0] if sent_rows else "محايد"

    return {
        "today_count": today_count,
        "dominant_category": dominant_category,
        "market_sentiment": dominant_sentiment,
        "category_distribution": {row[0]: row[1] for row in cat_rows},
        "sentiment_distribution": {row[0]: row[1] for row in sent_rows},
    }
