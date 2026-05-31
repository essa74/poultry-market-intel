import logging
import time
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

logger = logging.getLogger(__name__)
from sqlalchemy import select, func, delete
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel
from app.db.session import get_db
from app.models.scraping import (
    ScrapingSource, ScrapingLog, ScrapingJobStatus,
    RawExtractedPrice, ScrapingSourceType,
)
from app.schemas.scraping import (
    ScrapingSourceResponse, ScrapingLogResponse, RawPriceResponse,
    ScraperStatusResponse, ScrapingRunResponse,
)
from app.services.scrapers import run_scheduled_collection, scheduler, get_scraper
from app.api.deps import require_admin_token
from app.services.scrapers.registry import update_source_health
from app.schemas.scraping import ScrapingDebugResponse, DebugItem, CreateSourceRequest, UpdatePostUrlsRequest, FacebookDebugResponse, OcrPreviewItem, ParsedPriceLine, ExtractedRecordPreview
from app.models import PriceRecord, NewsArticle

router = APIRouter()


@router.get("/status", response_model=ScraperStatusResponse)
async def get_scraper_status(db: AsyncSession = Depends(get_db)):
    total = await db.execute(select(func.count(ScrapingSource.id)))
    active = await db.execute(
        select(func.count(ScrapingSource.id)).where(ScrapingSource.is_active == True)
    )
    healthy = await db.execute(
        select(func.count(ScrapingSource.id)).where(ScrapingSource.health_score >= 70)
    )
    failed = await db.execute(
        select(func.count(ScrapingSource.id)).where(ScrapingSource.consecutive_failures > 0)
    )

    today = date.today()
    logs_today = await db.execute(
        select(func.count(ScrapingLog.id)).where(
            func.date(ScrapingLog.started_at) == today
        )
    )
    collected_today = await db.execute(
        select(func.coalesce(func.sum(ScrapingLog.records_collected), 0)).where(
            func.date(ScrapingLog.started_at) == today
        )
    )

    # Latest success / failure across all sources
    success_at = await db.execute(
        select(func.max(ScrapingSource.last_success_at))
    )
    failure_at = await db.execute(
        select(func.max(ScrapingSource.last_failure_at))
    )

    # Aggregated log stats
    agg = await db.execute(
        select(
            func.coalesce(func.sum(ScrapingLog.valid_saved), 0),
            func.coalesce(func.sum(ScrapingLog.duplicates_skipped), 0),
            func.coalesce(func.sum(ScrapingLog.invalid_skipped), 0),
        )
    )
    valid_total, dup_total, invalid_total = agg.one()

    return ScraperStatusResponse(
        total_sources=total.scalar() or 0,
        active_sources=active.scalar() or 0,
        healthy_sources=healthy.scalar() or 0,
        failed_sources=failed.scalar() or 0,
        total_logs_today=logs_today.scalar() or 0,
        total_collected_today=collected_today.scalar() or 0,
        scheduler_running=scheduler.running,
        auto_discover_active=scheduler.running,
        auto_discover_interval_hours=3,
        latest_success_at=success_at.scalar(),
        latest_failure_at=failure_at.scalar(),
        total_valid_saved=valid_total or 0,
        total_duplicates_skipped=dup_total or 0,
        total_invalid_skipped=invalid_total or 0,
    )


@router.get("/sources", response_model=list[ScrapingSourceResponse])
async def list_sources(db: AsyncSession = Depends(get_db)):
    sources = (await db.execute(
        select(ScrapingSource).order_by(ScrapingSource.name)
    )).scalars().all()

    # Eagerly load latest log per source
    source_ids = [s.id for s in sources]
    if source_ids:
        latest_ids = (
            select(
                ScrapingLog.source_id,
                func.max(ScrapingLog.id).label("max_id"),
            )
            .where(ScrapingLog.source_id.in_(source_ids))
            .group_by(ScrapingLog.source_id)
            .subquery()
        )
        logs = (await db.execute(
            select(ScrapingLog).join(latest_ids, ScrapingLog.id == latest_ids.c.max_id)
        )).scalars().all()
        log_map = {log.source_id: log for log in logs}
    else:
        log_map = {}

    result = []
    for s in sources:
        resp = ScrapingSourceResponse.model_validate(s)
        resp.latest_log = ScrapingLogResponse.model_validate(log_map[s.id]) if s.id in log_map else None
        result.append(resp)
    return result


@router.patch("/sources/{source_id}/config")
async def update_source_config(source_id: int, body: CreateSourceRequest, db: AsyncSession = Depends(get_db), _=Depends(require_admin_token)):
    result = await db.execute(
        select(ScrapingSource).where(ScrapingSource.id == source_id)
    )
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    source.name = body.name
    source.url = body.url
    source.source_type = body.source_type

    logger.info("update_source_config: source=%s before config=%s", source_id, source.config)

    # Merge new config into existing config — never reset post_urls
    merged = dict(source.config or {})
    merged.update(body.config)
    source.config = merged
    flag_modified(source, "config")

    source.is_active = body.is_active
    await db.commit()
    await db.refresh(source)

    logger.info("update_source_config: source=%s after refresh config=%s", source_id, source.config)
    return ScrapingSourceResponse.model_validate(source)


@router.patch("/sources/{source_id}/toggle")
async def toggle_source(source_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_admin_token)):
    result = await db.execute(
        select(ScrapingSource).where(ScrapingSource.id == source_id)
    )
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    source.is_active = not source.is_active
    await db.commit()
    return {"id": source.id, "is_active": source.is_active}


@router.patch("/sources/{source_id}/post-urls")
async def update_source_post_urls(source_id: int, body: UpdatePostUrlsRequest, db: AsyncSession = Depends(get_db), _=Depends(require_admin_token)):
    result = await db.execute(
        select(ScrapingSource).where(ScrapingSource.id == source_id)
    )
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail={
            "en": "Source not found",
            "ar": "المصدر غير موجود",
        })

    logger.info("update_source_post_urls: source=%s before config=%s", source_id, source.config)

    # Force a NEW dict to ensure SQLAlchemy detects the change
    config = dict(source.config or {})
    config["post_urls"] = body.post_urls
    if body.auto_discover is not None:
        config["auto_discover"] = body.auto_discover
    if body.max_posts_scan is not None:
        config["max_posts_scan"] = body.max_posts_scan
    if body.max_price_posts is not None:
        config["max_price_posts"] = body.max_price_posts
    source.config = config
    flag_modified(source, "config")

    logger.info("update_source_post_urls: source=%s after assign config=%s", source_id, source.config)

    await db.commit()
    await db.refresh(source)

    logger.info("update_source_post_urls: source=%s after refresh config=%s", source_id, source.config)
    return {"message": "تم تحديث إعدادات المصدر", "config": source.config}


class DeleteSourceResponse(BaseModel):
    message: str
    deleted_logs: int
    deleted_raw_prices: int
    was_active: bool


@router.delete("/sources/{source_id}", response_model=DeleteSourceResponse)
async def delete_source(source_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_admin_token)):
    result = await db.execute(
        select(ScrapingSource).where(ScrapingSource.id == source_id)
    )
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail={
            "en": "Source not found",
            "ar": "المصدر غير موجود",
        })

    was_active = source.is_active

    log_result = await db.execute(
        select(func.count(ScrapingLog.id)).where(ScrapingLog.source_id == source_id)
    )
    deleted_logs = log_result.scalar() or 0

    raw_result = await db.execute(
        select(func.count(RawExtractedPrice.id)).where(RawExtractedPrice.source_id == source_id)
    )
    deleted_raw_prices = raw_result.scalar() or 0

    await db.execute(
        delete(RawExtractedPrice).where(RawExtractedPrice.source_id == source_id)
    )
    await db.execute(
        delete(ScrapingLog).where(ScrapingLog.source_id == source_id)
    )
    await db.delete(source)
    await db.commit()

    return DeleteSourceResponse(
        message="تم حذف المصدر وكل السجلات المرتبطة به بنجاح",
        deleted_logs=deleted_logs,
        deleted_raw_prices=deleted_raw_prices,
        was_active=was_active,
    )


@router.post("/sources", response_model=ScrapingSourceResponse, status_code=201)
async def create_source(body: CreateSourceRequest, db: AsyncSession = Depends(get_db), _=Depends(require_admin_token)):
    existing = await db.execute(
        select(ScrapingSource).where(func.lower(ScrapingSource.url) == body.url.lower())
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail={
            "en": "A source with this URL already exists",
            "ar": "يوجد مصدر بهذا الرابط بالفعل",
        })
    source = ScrapingSource(
        name=body.name,
        source_type=body.source_type,
        url=body.url,
        config=body.config,
        is_active=body.is_active,
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return ScrapingSourceResponse.model_validate(source)


@router.get("/logs", response_model=list[ScrapingLogResponse])
async def list_logs(
    source_id: Optional[int] = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ScrapingLog)
    if source_id:
        stmt = stmt.where(ScrapingLog.source_id == source_id)
    stmt = stmt.order_by(ScrapingLog.started_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/raw-prices", response_model=list[RawPriceResponse])
async def list_raw_prices(
    limit: int = Query(50, le=200),
    source_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(RawExtractedPrice)
    if source_id:
        stmt = stmt.where(RawExtractedPrice.source_id == source_id)
    stmt = stmt.order_by(RawExtractedPrice.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


class ResetDataResponse(BaseModel):
    message: str
    deleted_prices: int
    deleted_raw: int
    deleted_logs: int
    deleted_news: int


@router.post("/reset", response_model=ResetDataResponse)
async def reset_all_data(db: AsyncSession = Depends(get_db), _=Depends(require_admin_token)):
    try:
        raw_result = await db.execute(delete(RawExtractedPrice))
        raw_count = raw_result.rowcount or 0

        log_result = await db.execute(delete(ScrapingLog))
        log_count = log_result.rowcount or 0

        price_result = await db.execute(delete(PriceRecord))
        prices_count = price_result.rowcount or 0

        news_result = await db.execute(delete(NewsArticle))
        news_count = news_result.rowcount or 0

        await db.commit()

        return ResetDataResponse(
            message="تمت إعادة تهيئة البيانات بنجاح",
            deleted_prices=prices_count,
            deleted_raw=raw_count,
            deleted_logs=log_count,
            deleted_news=news_count,
        )
    except Exception as e:
        await db.rollback()
        logger.exception("Reset failed")
        raise HTTPException(status_code=500, detail={
            "ar": f"فشلت إعادة تهيئة البيانات: {str(e)}",
            "en": f"Data reset failed: {str(e)}",
        })


@router.post("/run", response_model=ScrapingRunResponse)
async def trigger_collection(_=Depends(require_admin_token)):
    try:
        await run_scheduled_collection("manual")
        return ScrapingRunResponse(
            message="Collection completed successfully",
            status="success",
        )
    except Exception as e:
        return ScrapingRunResponse(
            message=str(e)[:200],
            status="failed",
        )


@router.post("/sources/{source_id}/run", response_model=ScrapingDebugResponse)
async def run_source(source_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_admin_token)):
    source = (await db.execute(
        select(ScrapingSource).where(ScrapingSource.id == source_id)
    )).scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    scraper = get_scraper(source, db)
    if not scraper:
        raise HTTPException(status_code=400, detail=f"No scraper for source type: {source.source_type}")

    await scraper.run()
    source = await update_source_health(source_id, db) or source

    log_result = await db.execute(
        select(ScrapingLog)
        .where(ScrapingLog.source_id == source_id)
        .order_by(ScrapingLog.started_at.desc(), ScrapingLog.id.desc())
        .limit(1)
    )
    latest_log = log_result.scalar_one_or_none()

    raw_result = await db.execute(
        select(RawExtractedPrice)
        .where(RawExtractedPrice.source_id == source_id)
        .order_by(RawExtractedPrice.created_at.desc())
        .limit(50)
    )
    raw_prices = raw_result.scalars().all()

    items = [
        DebugItem(
            raw_text=(rp.raw_text or "")[:500],
            product_type=rp.product_type,
            category=rp.category,
            price=rp.price,
            region=rp.region,
            confidence=rp.confidence,
            extraction_method=rp.extraction_method,
            is_duplicate=rp.is_duplicate,
            is_failed_sample=rp.is_failed_sample,
        )
        for rp in raw_prices
    ]

    return ScrapingDebugResponse(
        source=ScrapingSourceResponse.model_validate(source),
        latest_log=ScrapingLogResponse.model_validate(latest_log) if latest_log else None,
        raw_text_preview=(latest_log.fetched_text[:500] if latest_log and latest_log.fetched_text else None),
        total_items_fetched=len(items),
        items=items,
        used_structured_only=scraper.debug_info.get("used_structured_only", False),
        structured_items_count=scraper.debug_info.get("structured_items_count", 0),
        parsed_price_lines_count=scraper.debug_info.get("parsed_price_lines_count", 0),
    )


@router.get("/sources/{source_id}/facebook-debug", response_model=FacebookDebugResponse)
async def facebook_debug(
    source_id: int,
    ocr: bool = Query(False, description="Run OCR on post images"),
    max_posts: int = Query(15, ge=1, le=50, description="Max posts to scan"),
    max_images: int = Query(0, ge=0, le=10, description="Max images for OCR"),
    timeout_seconds: int = Query(0, ge=0, le=180, description="Timeout in seconds (0=auto)"),
    use_posts: bool = Query(True, description="Only use direct post URLs, skip page feed"),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin_token),
):
    from app.services.scrapers.facebook_scraper import (
        FacebookPageScraper as FBScraper,
        _get_cached_fb_page, _set_cached_fb_page,
    )
    import asyncio

    total_start = time.monotonic()

    source = (await db.execute(
        select(ScrapingSource).where(ScrapingSource.id == source_id)
    )).scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    if source.source_type != ScrapingSourceType.FACEBOOK:
        raise HTTPException(status_code=400, detail="Source is not a Facebook source")

    effective_timeout = timeout_seconds if timeout_seconds > 0 else (120 if ocr else 60)
    effective_max_images = max_images if max_images > 0 else (2 if ocr else 0)

    # If use_posts is true and source has no post_urls, warn
    config = source.config or {}
    post_urls = config.get("post_urls", [])
    if use_posts and not post_urls:
        logger.warning("use_posts=true but source %s has no post_urls", source_id)

    scraper = FBScraper(source, db)

    timeout_hit = False
    ocr_error = None
    ocr_available = False
    partial = False
    page_load_seconds = 0.0
    ocr_seconds = 0.0

    # ── Phase 1: Collect page (no OCR) ───────────────────────────────────
    page_start = time.monotonic()
    try:
        items = await asyncio.wait_for(
            scraper.fetch_raw_data(
                run_ocr=False,
                max_posts=max_posts,
                max_images=0,
            ),
            timeout=effective_timeout,
        )
        page_load_seconds = time.monotonic() - page_start
    except asyncio.TimeoutError:
        page_load_seconds = time.monotonic() - page_start
        logger.warning("Facebook debug timeout for source %s (%.1fs)", source_id, page_load_seconds)
        items = []
        partial = True
        timeout_hit = True
    except Exception as exc:
        page_load_seconds = time.monotonic() - page_start
        logger.exception("Facebook debug unexpected error for source %s", source_id)
        items = []
        partial = True
        ocr_error = str(exc)[:300]

    # ── Cache fallback on timeout ─────────────────────────────────────────
    cached = None
    admin_warning = None
    if timeout_hit and not items:
        cached = _get_cached_fb_page(source_id)
        if cached:
            items = cached.get("posts", [])
            partial = True
            admin_warning = "تم استخدام آخر نتيجة ناجحة بسبب بطء فيسبوك"

    # ── Phase 2: OCR on already-collected images (if requested) ───────────
    if ocr and not timeout_hit and scraper._collected_accepted_images:
        ocr_start = time.monotonic()
        try:
            if max_images > 0:
                scraper._max_images = max_images
            ocr_texts = await asyncio.to_thread(scraper._ocr_images, scraper._collected_accepted_images)
            for ocr_t in ocr_texts:
                is_dup = any(kw in " ".join(items) for kw in ocr_t.split()[:5])
                if not is_dup:
                    items.append(f"[OCR] {ocr_t}")
            ocr_seconds = time.monotonic() - ocr_start
        except Exception as exc:
            ocr_seconds = time.monotonic() - ocr_start
            ocr_error = str(exc)[:300]

    # ── Phase 3: Check OCR availability ───────────────────────────────────
    try:
        import easyocr
        ocr_available = True
    except ImportError:
        ocr_available = False

    total_seconds = time.monotonic() - total_start

    accepted = scraper.debug_info.get("accepted_post_images", [])
    if cached:
        accepted = cached.get("accepted_post_images", [])
    if ocr and not accepted and not timeout_hit and not cached:
        admin_warning = "لم يتم العثور على صور منشورات قابلة للقراءة — تم تجاهل صور الواجهة الثابتة"

    return FacebookDebugResponse(
        source=ScrapingSourceResponse.model_validate(source),
        strategy_used=scraper.debug_info.get("strategy_used"),
        page_id=scraper.debug_info.get("page_id"),
        attempted_urls=scraper.debug_info.get("attempted_urls", []),
        fetched_lengths=scraper.debug_info.get("fetched_lengths", {}),
        posts_found=scraper.debug_info.get("posts_found", 0),
        accepted_posts=len(items) if not cached else len(cached.get("posts", [])),
        rejected_posts=scraper.debug_info.get("rejected_posts", 0),
        rejected_reasons=scraper.debug_info.get("rejected_reasons", []),
        sample_post_texts=(cached.get("sample_post_texts", []) if cached
                           else scraper.debug_info.get("sample_post_texts", [])),
        facebook_blocked=scraper.debug_info.get("facebook_blocked", False),
        facebook_block_reason=scraper.debug_info.get("facebook_block_reason"),
        image_only_detected=scraper.debug_info.get("image_only_detected", False),
        fetch_errors=scraper.debug_info.get("fetch_errors", []),
        playwright_urls=scraper.debug_info.get("playwright_urls", []),
        playwright_error=scraper.debug_info.get("playwright_error"),
        ocr_text_preview=scraper.debug_info.get("ocr_text_preview", []),
        normalized_ocr_text=scraper.debug_info.get("normalized_ocr_text", []),
        image_urls_found=scraper.debug_info.get("image_urls_found", []),
        extracted_numbers=scraper.debug_info.get("extracted_numbers", []),
        see_more_clicked=scraper.debug_info.get("see_more_clicked", 0),
        ocr_items_created=scraper.debug_info.get("ocr_items_created", 0),
        ocr_error=ocr_error,
        ocr_available=ocr_available,
        all_images_count=scraper.debug_info.get("all_images_count", 0),
        rejected_image_urls_sample=scraper.debug_info.get("rejected_image_urls_sample", []),
        accepted_post_images=accepted,
        image_filter_reasons=scraper.debug_info.get("image_filter_reasons", []),
        per_post_debug=scraper.debug_info.get("per_post_debug", []),
        posts_used=scraper.debug_info.get("posts_used", 0),
        ocr_confidence_avg=scraper.debug_info.get("ocr_confidence_avg", 0.0),
        accepted_ocr_lines=scraper.debug_info.get("accepted_ocr_lines", 0),
        rejected_ocr_lines=scraper.debug_info.get("rejected_ocr_lines", 0),
        structured_matches=scraper.debug_info.get("structured_matches", []),
        normalized_products=scraper.debug_info.get("normalized_products", []),
        direct_post_text=scraper.debug_info.get("direct_post_text"),
        parsed_price_lines=[ParsedPriceLine(**p) for p in scraper.debug_info.get("parsed_price_lines", [])],
        rejected_lines=scraper.debug_info.get("rejected_lines", []),
        extracted_records_preview=[ExtractedRecordPreview(**r) for r in scraper.debug_info.get("extracted_records_preview", [])],
        admin_warning=admin_warning,
        cached=bool(cached),
        page_load_seconds=round(page_load_seconds, 2) if page_load_seconds else None,
        image_collect_seconds=None,
        ocr_seconds=round(ocr_seconds, 2) if ocr_seconds else None,
        total_seconds=round(total_seconds, 2),
        partial=partial,
        timeout=timeout_hit,
        message="انتهت مهلة الفحص قبل اكتمال القراءة" if timeout_hit else None,
        raw_text_preview=(cached.get("raw_text_preview") if cached
                          else (scraper.raw_content[:500] if scraper.raw_content else None)),
        used_structured_only=scraper.debug_info.get("used_structured_only", False),
        structured_items_count=scraper.debug_info.get("structured_items_count", 0),
        parsed_price_lines_count=scraper.debug_info.get("parsed_price_lines_count", 0),
    )


@router.get("/sources/{source_id}/ocr-preview", response_model=list[OcrPreviewItem])
async def ocr_preview(
    source_id: int,
    max_images: int = Query(5, ge=1, le=20, description="Max images to preview"),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin_token),
):
    source = (await db.execute(
        select(ScrapingSource).where(ScrapingSource.id == source_id)
    )).scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    if source.source_type != ScrapingSourceType.FACEBOOK:
        raise HTTPException(status_code=400, detail="Source is not a Facebook source")

    from app.services.scrapers.facebook_scraper import (
        FacebookPageScraper as FBScraper,
        _ocr_image_url, _score_ocr_text, _fuzzy_arabic_cleanup,
        _apply_ocr_corrections, _normalize_price_text, _extract_structured_ocr,
        _SCORE_MINIMUM,
    )

    config = source.config or {}
    post_urls = config.get("post_urls", [])
    scraper = FBScraper(source, db)
    items = await scraper.fetch_raw_data(run_ocr=False, max_posts=max_images)

    image_urls = scraper.debug_info.get("accepted_post_images", [])
    if not image_urls:
        return []

    previews = []
    for img_url in image_urls[:max_images]:
        raw_text, conf = _ocr_image_url(img_url)
        cleaned = ""
        structured = None
        score = 0
        accepted = False

        if raw_text and len(raw_text.strip()) > 5:
            score = _score_ocr_text(raw_text)
            normalized = _normalize_price_text(raw_text)
            corrected = _apply_ocr_corrections(normalized)
            fuzzy = _fuzzy_arabic_cleanup(corrected)
            cleaned = fuzzy[:300]
            structured = _extract_structured_ocr(fuzzy)
            accepted = score >= _SCORE_MINIMUM and structured is not None

        previews.append(OcrPreviewItem(
            image_url=img_url,
            raw_ocr=raw_text[:200],
            cleaned_ocr=cleaned,
            extracted_product=f"{structured['product_type']}/{structured['category']}" if structured else None,
            extracted_price=structured["price"] if structured else None,
            confidence=round(float(conf), 3),
            score=score,
            accepted=accepted,
        ))

    return previews


@router.get("/debug/{source_id}", response_model=ScrapingDebugResponse)
async def debug_source(source_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_admin_token)):
    source_result = await db.execute(
        select(ScrapingSource).where(ScrapingSource.id == source_id)
    )
    source = source_result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    log_result = await db.execute(
        select(ScrapingLog)
        .where(ScrapingLog.source_id == source_id)
        .order_by(ScrapingLog.started_at.desc(), ScrapingLog.id.desc())
        .limit(1)
    )
    latest_log = log_result.scalar_one_or_none()

    raw_result = await db.execute(
        select(RawExtractedPrice)
        .where(RawExtractedPrice.source_id == source_id)
        .order_by(RawExtractedPrice.created_at.desc())
        .limit(50)
    )
    raw_prices = raw_result.scalars().all()

    items = [
        DebugItem(
            raw_text=(rp.raw_text or "")[:500],
            product_type=rp.product_type,
            category=rp.category,
            price=rp.price,
            region=rp.region,
            confidence=rp.confidence,
            extraction_method=rp.extraction_method,
            is_duplicate=rp.is_duplicate,
            is_failed_sample=rp.is_failed_sample,
        )
        for rp in raw_prices
    ]

    return ScrapingDebugResponse(
        source=ScrapingSourceResponse.model_validate(source),
        latest_log=ScrapingLogResponse.model_validate(latest_log) if latest_log else None,
        raw_text_preview=(latest_log.fetched_text[:500] if latest_log and latest_log.fetched_text else None),
        total_items_fetched=len(items),
        items=items,
    )


class TestFacebookParserRequest(BaseModel):
    text: str


class TestFacebookParserResponse(BaseModel):
    parsed_count: int
    parsed: list[dict]
    rejected: list[str]
    input_text: str
    input_length: int
    lines_count: int
    parser_module_path: str


@router.post("/test-facebook-parser", response_model=TestFacebookParserResponse)
async def test_facebook_parser(body: TestFacebookParserRequest, _=Depends(require_admin_token)):
    """Temporary debug endpoint to test _parse_arabic_price_lines directly."""
    import app.services.scrapers.facebook_scraper as fbmod

    parsed, rejected = fbmod._parse_arabic_price_lines(body.text)
    return TestFacebookParserResponse(
        parsed_count=len(parsed),
        parsed=parsed,
        rejected=rejected,
        input_text=body.text,
        input_length=len(body.text),
        lines_count=len(body.text.split("\n")),
        parser_module_path=fbmod.__file__,
    )
