"""
Facebook page scraper.
Uses public page posts via HTTP requests (no official API).
Supports mbasic/m/web URLs, Playwright fallback, and direct post URLs.
Includes OCR for extracting prices from post images.
"""
import logging
import re
import io
import time
from datetime import datetime, timedelta
from typing import Optional, Any
from urllib.parse import urlparse, quote
from functools import lru_cache
from httpx import AsyncClient
from bs4 import BeautifulSoup
from PIL import Image
from rapidfuzz import fuzz, process as fuzz_process
from .base import BaseScraper
from .config import get_scraper_settings

logger = logging.getLogger(__name__)

# ── Module-level page cache (TTL 10 min) ─────────────────────────────────
_fb_page_cache: dict[int, dict] = {}
_FB_CACHE_TTL = 600

def _get_cached_fb_page(source_id: int) -> Optional[dict]:
    entry = _fb_page_cache.get(source_id)
    if entry and (time.time() - entry["timestamp"]) < _FB_CACHE_TTL:
        return entry
    return None

def _set_cached_fb_page(source_id: int, data: dict):
    data["timestamp"] = time.time()
    _fb_page_cache[source_id] = data

def _clear_cached_fb_page(source_id: int):
    _fb_page_cache.pop(source_id, None)

# ── Module-level shared Playwright browser ────────────────────────────────
_shared_pw = None
_shared_browser = None

async def _get_shared_browser():
    global _shared_pw, _shared_browser
    if _shared_browser is None:
        from playwright.async_api import async_playwright
        settings = get_scraper_settings()
        _shared_pw = await async_playwright().start()
        _shared_browser = await _shared_pw.chromium.launch(
            headless=settings.playwright_headless,
        )
        logger.info("Shared Playwright browser launched")
    return _shared_browser

async def _close_shared_browser():
    global _shared_pw, _shared_browser
    if _shared_browser:
        try:
            await _shared_browser.close()
        except Exception:
            pass
        _shared_browser = None
    if _shared_pw:
        try:
            await _shared_pw.stop()
        except Exception:
            pass
        _shared_pw = None
    logger.info("Shared Playwright browser closed")


async def _reset_shared_browser():
    """Forcefully reset shared browser (e.g. after TargetClosedError)."""
    await _close_shared_browser()
    logger.info("Shared Playwright browser reset for retry")

# ── Arabic numeral normalization ────────────────────────────────────────────
# Arabic (٠-٩) + Eastern Arabic (۰-۹)
_ARABIC_NUMERAL_MAP = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def _normalize_arabic_numerals(text: str) -> str:
    return text.translate(_ARABIC_NUMERAL_MAP)


def _normalize_price_text(text: str) -> str:
    text = _normalize_arabic_numerals(text)
    text = re.sub(r"[٫,]", ".", text)
    return text


# ── Flexible price regexes ──────────────────────────────────────────────────
# Match: 85, 85ج, 85 جنيه, 85 للطبق, 850 للكرتونة, 1650 طن, etc.
FB_PRICE_PATTERNS = [
    re.compile(r"(\d+[\.,]?\d*)\s*(جنيه|ج\.م|جم|EGP|le|ج\.م\.|ج)", re.IGNORECASE),
    re.compile(r"(\d+[\.,]?\d*)\s*(ج)\s*$", re.IGNORECASE),
    re.compile(r"سعر\s*(?:ال|الـ|)\s*(\d+[\.,]?\d*)", re.IGNORECASE),
    re.compile(r"(\d+[\.,]?\d*)\s*(?:ج|جنيه|جنية)", re.IGNORECASE),
    re.compile(r"(\d{2,}[\.,]?\d*)\s*(?:للطبق|لل|طبق|كرتونة|للألف|ألف|طن)", re.IGNORECASE),
    re.compile(r"(\d{2,3}(?:[\.,]\d{1,2})?)\s*$", re.IGNORECASE),
    re.compile(r"بسعر\s*(\d+[\.,]?\d*)", re.IGNORECASE),
    re.compile(r"(\d{2,})\s*(?:ج|جنيه|جنية|)", re.IGNORECASE),
]


def _extract_numbers(text: str) -> list[float]:
    text = _normalize_price_text(text)
    numbers = []
    for pat in FB_PRICE_PATTERNS:
        for match in pat.finditer(text):
            try:
                raw = match.group(1).replace(",", ".")
                val = float(raw)
                if 0.1 < val < 200_000:
                    numbers.append(val)
            except (ValueError, IndexError):
                continue
    return numbers


# ── Keyword lists ───────────────────────────────────────────────────────────
FB_TARGET_KEYWORDS = [
    "بيض مخصب", "بيض تفريخ", "هاتشد", "hatched", "hatching",
    "fertile", "fertilized", "كتاكيت", "كتكوت",
    "أمهات", "مفرخات", "مفرخة",
    "أعلاف", "علف", "ذرة", "صويا",
    "سعر", "أسعار", "جنيه", "السعر",
    "بورصة", "دواجن",
]

FB_REJECT_PHRASES = [
    "بيض مائدة", "كرتونة بيض", "طبق بيض",
    "بطاريات", "أبيض بطاريات",
    "فراخ بيضاء بالكيلو", "سعر كيلو الدواجن",
    "سعر كيلو الفراخ", "الفراخ البيضاء",
    "وصفات", "مطاعم", "استهلاك",
    "طبخ", "اكل", "أكل",
    "كريم", "زيت", "عطر",
    "أخبار الفن", "مشاهير", "رياضة",
]

LOGIN_INDICATORS = [
    "login.php", "checkpoint", "confirm_id",
    "ربما تكون", "ربما يكون", "تم حظر",
    "blocked", "suspicious", "این صفحه در دسترس نیست",
    "this page isn't available", "content isn't available",
    "you must log in", "سجل الدخول",
]

# ── Image URL filter patterns ──────────────────────────────────────────────
REJECT_IMAGE_PATTERNS = re.compile(
    r"(z-m-static|static\.xx\.fbcdn|rsrc\.php|hsts-pixel|emoji)", re.I
)
REJECT_IMAGE_SIZE = re.compile(r"/(?:126|144|288)x(?:126|144|288)/")

ACCEPT_IMAGE_PATTERNS = re.compile(
    r"(scontent|t39\.30808|p1080|s1080|dst-webp|_n\.jpg)", re.I
)


def _is_reject_image_url(url: str) -> bool:
    if not url:
        return True
    if REJECT_IMAGE_PATTERNS.search(url.lower()):
        return True
    if REJECT_IMAGE_SIZE.search(url):
        return True
    return False


def _is_accepted_post_image(url: str) -> bool:
    return bool(ACCEPT_IMAGE_PATTERNS.search(url))


BG_URL_RE = re.compile(r'url\(["\']?([^)"\']+)["\']?\)')


# ── OCR correction dictionary ──────────────────────────────────────────────
# Fixes common Arabic OCR misreadings. Longest keys first for clean matching.
OCR_CORRECTIONS = {
    "رييض": "بيض",
    "لبيض": "بيض",
    "نبيض": "بيض",
    "تفرية": "تفريخ",
    "تغزية": "تفريخ",
    "تغريخ": "تفريخ",
    "تفريغ": "تفريخ",
    "تفريح": "تفريخ",
    "مخصبب": "مخصب",
    "مخصصر": "مخصب",
    "مخصيب": "مخصب",
    "كتكؤن": "كتكوت",
    "كتاكؤت": "كتاكيت",
    "جتciسا": "جنيه",
    "جتيه": "جنيه",
    "نفريخ": "تفريخ",
    "ريض": "بيض",
    "ريص": "بيض",
    "سغر": "سعر",
}


def _apply_ocr_corrections(text: str) -> str:
    for wrong, correct in sorted(OCR_CORRECTIONS.items(), key=lambda x: -len(x[0])):
        if wrong in text:
            text = text.replace(wrong, correct)
    return text


# ── Fuzzy Arabic keyword dictionary ──────────────────────────────────────
OCR_FUZZY_KEYWORDS = {
    "بيض": "بيض",
    "مخصب": "مخصب",
    "تفريخ": "تفريخ",
    "أمهات": "أمهات",
    "امهات": "أمهات",
    "تسمين": "تسمين",
    "أبيض": "أبيض",
    "ابيض": "أبيض",
    "ساسو": "ساسو",
    "بلدي": "بلدي",
    "كتكوت": "كتكوت",
    "كتاكيت": "كتاكيت",
    "جنيه": "جنيه",
    "سعر": "سعر",
    "ذرة": "ذرة",
    "صويا": "صويا",
    "علف": "علف",
    "أعلاف": "أعلاف",
    "دواجن": "دواجن",
}

_FUZZY_THRESHOLD = 70


def _fuzzy_normalize_word(word: str) -> str:
    """Normalize a single Arabic word using fuzzy matching against the keyword dict."""
    word = word.strip()
    if not word or len(word) < 2:
        return word
    if word in OCR_FUZZY_KEYWORDS:
        return OCR_FUZZY_KEYWORDS[word]
    best = fuzz_process.extractOne(word, list(OCR_FUZZY_KEYWORDS.keys()),
                                    scorer=fuzz.ratio, score_cutoff=_FUZZY_THRESHOLD)
    if best:
        return OCR_FUZZY_KEYWORDS[best[0]]
    return word


def _fuzzy_arabic_cleanup(text: str) -> str:
    """Apply fuzzy matching to normalize OCR-mangled Arabic words."""
    words = text.split()
    cleaned = [_fuzzy_normalize_word(w) for w in words]
    return " ".join(cleaned)


# ── Image scoring ────────────────────────────────────────────────────────
SCORE_KEYWORDS = {
    "بيض": 50, "تفريخ": 50, "مخصب": 50, "كتكوت": 50, "كتاكيت": 50,
    "أمهات": 40, "تسمين": 40,
    "جنيه": 20, "جنية": 20, "سعر": 15, "أسعار": 15,
}
_SCORE_MINIMUM = 50


def _score_ocr_text(text: str) -> int:
    score = 0
    text_lower = text.lower()
    for kw, pts in SCORE_KEYWORDS.items():
        if kw in text_lower:
            score += pts
    # Bonus for recognizable price pattern
    if re.search(r"\b\d{2,3}\b", text):
        score += 30
    return score


# ── Structured OCR extraction ────────────────────────────────────────────
# Product-level keyword groups for nearest-keyword matching
PRODUCT_PATTERNS: list[tuple[str, str, str, str]] = [
    # (product_group, product_type, category_match, keywords)
    ("fertilized_eggs", "fertilized_eggs", "white",    "بيض أبيض"),
    ("fertilized_eggs", "fertilized_eggs", "white",    "بيض مخصب أبيض"),
    ("fertilized_eggs", "fertilized_eggs", "white",    "بيض تفريخ أبيض"),
    ("fertilized_eggs", "fertilized_eggs", "sasso",    "بيض ساسو"),
    ("fertilized_eggs", "fertilized_eggs", "baladi",   "بيض بلدي"),
    ("fertilized_eggs", "fertilized_eggs", "white",    "بيض تفريخ"),
    ("fertilized_eggs", "fertilized_eggs", "white",    "بيض مخصب"),
    ("fertilized_eggs", "fertilized_eggs", "white",    "بيض أمهات"),
    ("fertilized_eggs", "fertilized_eggs", "white",    "بيض تسمين"),
    ("chicks",          "day_old_chicks",   "white",    "كتاكيت أبيض"),
    ("chicks",          "day_old_chicks",   "sasso",    "كتاكيت ساسو"),
    ("chicks",          "day_old_chicks",   "baladi",   "كتاكيت بلدي"),
    ("chicks",          "day_old_chicks",   "white",    "كتكوت أبيض"),
    ("chicks",          "day_old_chicks",   "sasso",    "كتكوت ساسو"),
    ("chicks",          "day_old_chicks",   "baladi",   "كتكوت بلدي"),
    ("chicks",          "day_old_chicks",   "white",    "كتاكيت"),
    ("chicks",          "day_old_chicks",   "white",    "كتكوت"),
    ("feed",            "feed",             "feed_corn","ذرة"),
    ("feed",            "feed",             "feed_soy", "صويا"),
    ("feed",            "feed",             "other",    "علف"),
]

# Price extraction patterns for OCR text
OCR_PRICE_PATTERNS = [
    re.compile(r"(\d{2,3})\s*(?:جنيه|جنية|ج\.م|جم|EGP)", re.IGNORECASE),
    re.compile(r"(\d{2,3})\s*$"),
    re.compile(r"سعر\s*(\d{2,3})"),
    re.compile(r"(\d{2,3})\s*(?:ج|جنية|جنيه)"),
]


def _extract_ocr_price(text: str) -> Optional[float]:
    for pat in OCR_PRICE_PATTERNS:
        m = pat.search(text)
        if m:
            try:
                val = float(m.group(1))
                if 10 <= val <= 5000:
                    return val
            except ValueError:
                continue
    return None


def _extract_structured_ocr(text: str) -> Optional[dict[str, Any]]:
    """Parse cleaned OCR text into structured product info.
    
    Returns {product_group, product_type, category, price, unit} or None.
    """
    cleaned = _fuzzy_arabic_cleanup(text)
    text_lower = cleaned.lower()

    # Find which product pattern best matches
    best_match = None
    best_keyword = ""
    for group, ptype, cat, keywords in PRODUCT_PATTERNS:
        if keywords in cleaned or keywords in text_lower:
            best_match = (group, ptype, cat)
            best_keyword = keywords
            # Prefer more specific matches (longer keyword)
            if len(keywords) >= 10:
                break

    if not best_match:
        return None

    group, ptype, cat = best_match

    price = _extract_ocr_price(cleaned)
    if not price:
        return None

    # Determine unit
    unit_map = {
        "fertilized_eggs": "per_tray",
        "chicks": "per_unit",
        "feed": "per_ton",
    }
    unit = unit_map.get(group)

    return {
        "product_group": group,
        "product_type": ptype,
        "category": cat,
        "price": price,
        "unit": unit,
    }


# ── OCR cache (text, avg_confidence) ─────────────────────────────────────
_ocr_cache: dict[str, tuple[str, float]] = {}
_ocr_reader = None


def _get_ocr_reader():
    global _ocr_reader
    if _ocr_reader is None:
        try:
            import easyocr
            _ocr_reader = easyocr.Reader(["ar", "en"], gpu=False)
            logger.info("easyocr reader initialized (ar+en, CPU)")
        except Exception as e:
            logger.warning(f"easyocr not available: {e}")
            _ocr_reader = False
    return _ocr_reader if _ocr_reader is not False else None


def _split_image_regions(image_bytes: bytes, n: int = 3) -> list[bytes]:
    """Split a tall image into n vertical regions, return list of JPEG bytes."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        w, h = img.size
        if h <= w:
            return [image_bytes]
        region_h = h // n
        regions = []
        for i in range(n):
            top = i * region_h
            bottom = top + region_h if i < n - 1 else h
            region = img.crop((0, top, w, bottom))
            buf = io.BytesIO()
            region.save(buf, format="JPEG", quality=85)
            regions.append(buf.getvalue())
        return regions
    except Exception:
        return [image_bytes]


def _ocr_image_url(url: str, max_size_px: int = 400) -> tuple[str, float]:
    """Return (corrected_text, avg_confidence) or ("", 0.0)."""
    if url in _ocr_cache:
        cached = _ocr_cache[url]
        if isinstance(cached, str):
            return (cached, 0.0)
        return cached
    reader = _get_ocr_reader()
    if not reader:
        return ("", 0.0)
    try:
        import httpx as sync_httpx
        resp = sync_httpx.get(url, timeout=15.0, follow_redirects=True,
                              headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            _ocr_cache[url] = ("", 0.0)
            return ("", 0.0)
        image_bytes = resp.content
        if len(image_bytes) < 100:
            _ocr_cache[url] = ("", 0.0)
            return ("", 0.0)

        # Check dimensions, reject small/profile images
        try:
            img = Image.open(io.BytesIO(image_bytes))
            w, h = img.size
            if w < max_size_px or h < max_size_px:
                _ocr_cache[url] = ("", 0.0)
                return ("", 0.0)
            # Reject square images < 800px (likely avatar)
            if w == h and w < 800:
                _ocr_cache[url] = ("", 0.0)
                return ("", 0.0)
        except Exception:
            pass

        # Split tall images into regions
        regions = _split_image_regions(image_bytes, 3)

        all_words: list[str] = []
        all_confidences: list[float] = []

        for region_bytes in regions:
            try:
                results = reader.readtext(region_bytes)
                for _bbox, text, conf in results:
                    conf = float(conf)
                    if conf >= 0.35:
                        all_words.append(text)
                        all_confidences.append(conf)
            except Exception:
                continue

        if not all_words:
            _ocr_cache[url] = ("", 0.0)
            return ("", 0.0)

        text = " ".join(all_words)
        text = _normalize_price_text(text)
        avg_conf = sum(all_confidences) / len(all_confidences)

        _ocr_cache[url] = (text, avg_conf)
        logger.info(f"OCR {url[:60]}... conf={avg_conf:.2f}: {text[:100]}")
        return (text, avg_conf)
    except Exception as e:
        logger.debug(f"OCR failed for {url[:60]}: {e}")
        _ocr_cache[url] = ("", 0.0)
        return ("", 0.0)


# ── Pure functions ──────────────────────────────────────────────────────────
def _is_poultry_price_post(text: str) -> bool:
    for phrase in FB_REJECT_PHRASES:
        if phrase in text:
            return False
    has_target = any(kw in text for kw in FB_TARGET_KEYWORDS)
    has_number = bool(re.search(r"\d+", text))
    return has_target and has_number


def _extract_page_id(url: str) -> str:
    parsed = urlparse(url.rstrip("/"))
    path = parsed.path
    for prefix in ("/pages/", "/pg/"):
        if path.startswith(prefix):
            path = path[len(prefix):]
    if path.startswith("/"):
        path = path[1:]
    path = path.split("/")[0].split("?")[0]
    return path


def _build_attempt_urls(page_id: str) -> list[str]:
    encoded = quote(page_id, safe="")
    return [
        f"https://mbasic.facebook.com/{encoded}",
        f"https://m.facebook.com/{encoded}",
        f"https://web.facebook.com/{encoded}",
    ]


def _build_direct_post_url(post_url: str) -> str:
    parsed = urlparse(post_url.rstrip("/"))
    path = parsed.path
    return f"https://mbasic.facebook.com{path}"


def _is_image_only_post(soup: BeautifulSoup, text_len: int) -> bool:
    images = soup.find_all("img")
    has_image = any(
        img.get("src") and "emoji" not in (img.get("src") or "").lower()
        for img in images
    )
    return has_image and text_len < 50


def _extract_post_texts(soup: BeautifulSoup, debug: dict) -> list[str]:
    texts = []
    selectors = [
        "div[role=article]", "div.story_body_container",
        "div.mbl", "div[id*=feed]", "div[id*=story]",
        "div[class*=post]", "div[class*=userContent]",
        "div[data-testid*=post]", "div[class*=message]",
        "p", "span[class*=fcg]", "div[class*=story_body]",
        "div[class*=fbUserContent]", "section",
    ]
    seen = set()
    for sel in selectors:
        matched = soup.select(sel)
        for el in matched:
            text = el.get_text(separator=" ", strip=True)
            if text and len(text) > 15 and text not in seen:
                seen.add(text)
                texts.append(text)
    if not texts:
        for tag in ("div", "p", "span", "li", "section"):
            for el in soup.find_all(tag):
                text = el.get_text(separator=" ", strip=True)
                if len(text) > 20 and text not in seen:
                    seen.add(text)
                    texts.append(text)
    debug["posts_found"] = len(texts)
    return texts


def _extract_post_images(soup: BeautifulSoup) -> list[str]:
    urls = set()
    for img in soup.find_all("img"):
        src = img.get("src") or ""
        if not src or not src.startswith("http"):
            continue
        if _is_reject_image_url(src):
            continue
        if _is_accepted_post_image(src):
            urls.add(src)
    return list(urls)


def _detect_product_type(text: str) -> Optional[dict]:
    text_lower = text.lower()
    result = {}
    if any(kw in text for kw in ["بيض مخصب", "بيض تفريخ", "hatching", "fertile", "بيض أمهات", "بيض تسمين"]):
        result["product_group"] = "fertilized_eggs"
        result["product_type"] = "fertilized_eggs"
    elif any(kw in text for kw in ["كتاكيت", "كتكوت"]):
        result["product_group"] = "chicks"
        result["product_type"] = "day_old_chicks"
    elif any(kw in text for kw in ["ذرة", "صويا", "علف", "أعلاف"]):
        result["product_group"] = "feed"
        result["product_type"] = "feed"
    else:
        return None
    if result["product_group"] == "fertilized_eggs":
        if any(kw in text for kw in ["أبيض", "ابيض"]):
            result["category"] = "white"
        elif any(kw in text for kw in ["ساسو"]):
            result["category"] = "sasso"
        elif any(kw in text for kw in ["بلدي", "بلدى"]):
            result["category"] = "baladi"
        else:
            result["category"] = "white"
    elif result["product_group"] == "chicks":
        if any(kw in text for kw in ["أبيض", "ابيض"]):
            result["category"] = "white"
        elif any(kw in text for kw in ["ساسو"]):
            result["category"] = "sasso"
        elif any(kw in text for kw in ["بلدي", "بلدى"]):
            result["category"] = "baladi"
        else:
            result["category"] = "white"
    elif result["product_group"] == "feed":
        if any(kw in text for kw in ["ذرة"]):
            result["category"] = "feed_corn"
        elif any(kw in text for kw in ["صويا"]):
            result["category"] = "feed_soy"
        else:
            result["category"] = "other"
    numbers = _extract_numbers(text)
    if numbers:
        result["price"] = numbers[0]
    from .price_normalizer import normalizer
    nr = normalizer.normalize(text)
    if nr and nr.is_valid():
        result["price"] = nr.price if not result.get("price") else result["price"]
        result["unit"] = nr.unit
        result["region"] = nr.region
        result["recorded_date"] = nr.recorded_date
    return result if result.get("price") else None


# ── Arabic price-line parser for multi-line Facebook text posts ─────────────
# Extended digit normalization: Arabic (٠-٩) + Eastern Arabic (۰-۹)
_EXTENDED_DIGIT_MAP = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def _normalize_all_digits(text: str) -> str:
    """Normalize Arabic and Eastern Arabic digits to ASCII, fix decimal separators."""
    text = text.translate(_EXTENDED_DIGIT_MAP)
    text = text.replace("٫", ".").replace(",", ".")
    return text


# ONLY two regexes used in _parse_single_price_line (applied AFTER normalization)
PRICE_RANGE_RE = re.compile(
    r"(?:من\s*)?(\d+(?:\.\d+)?)\s*(?:الى|ل|-|to)\s*(\d+(?:\.\d+)?)\s*ج?"
)
PRICE_SINGLE_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*ج"
)

# Category keywords with priority: ostrich > quail > duck > turkey > sasso > baladi > local > white
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "ostrich": ["نعام"],
    "quail":   ["سمان"],
    "duck":    ["بط"],
    "turkey":  ["رومى", "رومي"],
    "sasso":   ["ساسو"],
    "baladi":  ["بلدي", "بلدى"],
    "local":   ["فيومي", "فيومى", "جميزه", "جميزة", "جمبري", "جمبرى"],
    "white":   ["أبيض", "ابيض", "شركات", "قطعان", "أمهات"],
}

# Fertilized egg acceptance keywords
_FERTILIZED_KEYWORDS = [
    "تفريخ", "مخصب", "ساسو", "بلدي", "بلدى",
    "بط", "سمان", "نعام", "رومى", "رومي",
    "فيومى", "فيومي", "جميزه", "جميزة",
]

# Rejection keywords (table eggs / consumer)
_REJECT_KEYWORDS = ["مائدة", "كرتونة", "استهلاكي", "طبق بيض مائدة"]


def _normalize_price_units(text: str) -> str:
    """Normalize currency symbols: جنيه/جنية/ج. → ج"""
    text = re.sub(r"(?:جنيه|جنية|ج\.م|ج\.)", "ج", text)
    # Collapse spaces around ج
    text = re.sub(r"\s*ج\s*", " ج ", text)
    return text


def _collapse_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _parse_single_price_line(line: str) -> Optional[dict]:
    """Parse a single Arabic price line like:
      بيض تفريخ ابيض من 10 ل12 ج
      بيض تفريخ ساسو شيفر 8 ج
      بيض مخصب ابيض شركات ١٥ج.
      بيض مخصب بلدى هجين 4.5ج

    Returns {raw_line, normalized_line, product_group, product_type,
             category, price, min_price, max_price, unit, raw_price_range, confidence}
    or None if it can't be parsed.
    """
    line = line.strip()
    if not line:
        return None

    logger.warning("PARSE INPUT LINE: %s", line)

    # ── 1. Normalize the line FIRST ────────────────────────────────────────
    normalized = _normalize_all_digits(line)
    normalized = _normalize_price_units(normalized)
    normalized = normalized.replace("إلى", "الى")
    normalized = _collapse_spaces(normalized)
    # Strip trailing punctuation (keep decimal dots and digits)
    normalized = normalized.strip(" .,:;!؟?،\n\r\t")
    normalized = re.sub(r"\s*[،,]\s*", " ", normalized)

    # ── 2. Reject table egg / consumer keywords ────────────────────────────
    if any(kw in line for kw in _REJECT_KEYWORDS):
        logger.warning("PARSE FAILED: %s", line)
        return None

    # ── 3. Must contain بيض ────────────────────────────────────────────────
    if "بيض" not in line:
        logger.warning("PARSE FAILED: %s", line)
        return None

    # ── 4. Must contain a fertilized egg keyword ───────────────────────────
    if not any(kw in line for kw in _FERTILIZED_KEYWORDS):
        logger.warning("PARSE FAILED: %s", line)
        return None

    # ── 5. Extract price using ONLY two regexes ────────────────────────────
    price = None
    min_price = None
    max_price = None
    raw_range = None

    range_m = PRICE_RANGE_RE.search(normalized)
    single_m = PRICE_SINGLE_RE.search(normalized)

    if range_m:
        min_price = float(range_m.group(1))
        max_price = float(range_m.group(2))
        price = round((min_price + max_price) / 2, 1)
        raw_range = f"{min_price:.0f}-{max_price:.0f}"
    elif single_m:
        price = float(single_m.group(1))

    # ── 5b. Brute-force fallback: if line has بيض + number + ج ─────────────
    if price is None and "بيض" in line:
        fallback_m = re.search(r"(\d+(?:\.\d+)?)\s*ج", normalized)
        if fallback_m:
            price = float(fallback_m.group(1))
            logger.warning("FALLBACK PRICE: %s -> price=%s via brute-force", line, price)

    if price is None:
        logger.warning("PARSE FAILED: %s", line)
        return None

    if price <= 0 or price > 10000:
        logger.warning("PARSE FAILED: %s", line)
        return None

    # ── 6. Determine category (priority order) ─────────────────────────────
    category = "white"
    for cat_name, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in line for kw in keywords):
            category = cat_name
            break

    # ── 7. Build result dict ───────────────────────────────────────────────
    result = {
        "raw_line": line,
        "normalized_line": normalized,
        "product_group": "fertilized_eggs",
        "product_type": "fertilized_eggs",
        "category": category,
        "price": price,
        "min_price": min_price,
        "max_price": max_price,
        "unit": "per_unit",
        "raw_price_range": raw_range,
        "confidence": 0.9,
    }

    logger.warning("PARSED RESULT: %s", result)
    return result


def _parse_arabic_price_lines(text: str) -> tuple[list[dict], list[str]]:
    """
    Parse multi-line Arabic Facebook price post text.
    Every line is passed to _parse_single_price_line (no pre-filter).
    Returns (parsed_lines, rejected_lines).
    """
    lines = text.split("\n")
    parsed: list[dict] = []
    rejected: list[str] = []

    for i, line in enumerate(lines):
        line = line.strip()
        logger.warning("PARSE LINE %d: repr=%r", i, line)
        if not line:
            logger.warning("PARSE LINE %d: empty, skipped", i)
            continue

        result = _parse_single_price_line(line)
        if result:
            parsed.append(result)
        else:
            rejected.append(line)

    logger.warning(
        "PARSE RESULT: total_lines=%d parsed=%d rejected=%d",
        len(lines), len(parsed), len(rejected),
    )
    return parsed, rejected


# ── Facebook post date extraction ─────────────────────────────────────────
_ARABIC_MONTHS = {
    "يناير": 1, "فبراير": 2, "مارس": 3, "أبريل": 4, "إبريل": 4,
    "مايو": 5, "يونيو": 6, "يوليو": 7, "أغسطس": 8, "سبتمبر": 9,
    "أكتوبر": 10, "نوفمبر": 11, "ديسمبر": 12,
}


def _extract_post_date(text: str) -> Optional[str]:
    """Try to extract a post date from Facebook Arabic post text.
    Returns 'YYYY-MM-DD' string or None (caller should use today).
    """
    today = datetime.utcnow().date()
    # اليوم
    if "اليوم" in text:
        return today.isoformat()
    # أمس
    if "أمس" in text:
        return (today - timedelta(days=1)).isoformat()
    # Arabic date: الثلاثاء، ٢٦ مايو ٢٠٢٦
    m = re.search(r"(\d{1,2})\s*(يناير|فبراير|مارس|أبريل|إبريل|مايو|يونيو|يوليو|أغسطس|سبتمبر|أكتوبر|نوفمبر|ديسمبر)\s*(\d{4})", text)
    if m:
        day = int(m.group(1))
        month = _ARABIC_MONTHS.get(m.group(2), 1)
        year = int(m.group(3))
        return f"{year:04d}-{month:02d}-{day:02d}"
    # Short Arabic date without year: ٢٦ مايو -> assume this year
    m = re.search(r"(\d{1,2})\s*(يناير|فبراير|مارس|أبريل|إبريل|مايو|يونيو|يوليو|أغسطس|سبتمبر|أكتوبر|نوفمبر|ديسمبر)", text)
    if m:
        day = int(m.group(1))
        month = _ARABIC_MONTHS.get(m.group(2), 1)
        return f"{today.year:04d}-{month:02d}-{day:02d}"
    # Numeric date: 5/5/2026 or 5-5-2026
    m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", text)
    if m:
        return f"{int(m.group(3)):04d}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    # Numeric with 2-digit year: 5/5/26
    m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2})$", text)
    if m:
        year = 2000 + int(m.group(3))
        return f"{year:04d}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    return None


# ── Scraper class ───────────────────────────────────────────────────────────
class FacebookPageScraper(BaseScraper):
    async def fetch_raw_data(
        self,
        run_ocr: bool = False,
        max_posts: int = 15,
        max_images: int = 3,
        max_scrolls: int = 2,
        max_see_more_clicks: int = 5,
    ) -> list:
        logger.warning("### NEW FETCH_RAW_DATA ACTIVE ###")
        logger.warning("FacebookScraper module path: %s", __file__)
        items: list = []
        ocr_items: list[str] = []
        config = self.source.config or {}
        page_id = config.get("page_id", "") or _extract_page_id(self.source.url or "")
        limit = config.get("posts_limit", max_posts)
        post_urls = config.get("post_urls", [])

        self._ocr_enabled = run_ocr
        self._max_images = max_images

        if not page_id and not post_urls:
            logger.warning(f"No page_id or post_urls for Facebook source {self.source.id}")
            return items

        self.debug_info["page_id"] = page_id
        self.debug_info["attempted_urls"] = []
        self.debug_info["fetched_lengths"] = {}
        self.debug_info["posts_found"] = 0
        self.debug_info["accepted_posts"] = 0
        self.debug_info["rejected_posts"] = 0
        self.debug_info["rejected_reasons"] = []
        self.debug_info["sample_post_texts"] = []
        self.debug_info["image_only_detected"] = False
        self.debug_info["facebook_blocked"] = False
        self.debug_info["strategy_used"] = None
        self.debug_info["ocr_text_preview"] = []
        self.debug_info["normalized_ocr_text"] = []
        self.debug_info["image_urls_found"] = []
        self.debug_info["extracted_numbers"] = []
        self.debug_info["normalized_numbers"] = []
        self.debug_info["ocr_items_created"] = 0
        self.debug_info["ocr_confidence_avg"] = 0.0
        self.debug_info["accepted_ocr_lines"] = 0
        self.debug_info["rejected_ocr_lines"] = 0
        self.debug_info["structured_matches"] = []
        self.debug_info["normalized_products"] = []
        self.debug_info["all_images_count"] = 0
        self.debug_info["rejected_image_urls_sample"] = []
        self.debug_info["accepted_post_images"] = []
        self.debug_info["image_filter_reasons"] = []
        self.debug_info["per_post_debug"] = []
        self.debug_info["posts_used"] = len(post_urls)
        self.debug_info["used_structured_only"] = False
        self.debug_info["structured_items_count"] = 0
        self.debug_info["parsed_price_lines_count"] = 0
        self._collected_accepted_images: list[str] = []
        self._collected_text_items: list[str] = []
        auto_discover = config.get("auto_discover", True)
        max_posts_scan = config.get("max_posts_scan", 10)
        max_price_posts = config.get("max_price_posts", 3)

        # ── Strategy A (primary): Auto-discover latest price posts ──────────
        if page_id and auto_discover:
            self.debug_info["auto_discover_used"] = True
            logger.info("Strategy A: auto-discovering latest price posts from page feed")
            auto_items = await self._discover_latest_posts_from_page(
                page_id,
                max_posts_scan=max_posts_scan,
                max_price_posts=max_price_posts,
            )
            if auto_items:
                logger.warning(
                    f"### AUTO-DISCOVER RETURNED {len(auto_items)} STRUCTURED ITEMS ###"
                )
                self.debug_info["used_structured_only"] = True
                self.debug_info["structured_items_count"] = len(auto_items)
                self.debug_info["parsed_price_lines_count"] = len(auto_items)
                self.debug_info["accepted_posts"] = len(auto_items)
                return auto_items[:limit]
            else:
                logger.info("Auto-discover found no price posts, trying post_urls fallback")

        # ── Strategy B (fallback): Direct post URLs ─────────────────────────
        if post_urls:
            logger.info("Strategy B: trying direct post URLs")
            direct_items, ocr_items = await self._fetch_direct_posts(post_urls, limit)
            items = direct_items

            structured_items = [item for item in items if isinstance(item, dict)]
            if structured_items:
                logger.warning(f"### STRUCTURED RETURN ACTIVE: {len(structured_items)} ###")
                self.debug_info["used_structured_only"] = True
                self.debug_info["structured_items_count"] = len(structured_items)
                self.debug_info["parsed_price_lines_count"] = len(structured_items)
                self.debug_info["accepted_posts"] = len(structured_items)
                return structured_items[:limit]

        # ── Strategy C (fallback): mbasic HTML parser ───────────────────────
        if page_id and not items:
            logger.info("Strategy C: trying mbasic HTML parser")
            items = await self._fetch_mbasic(page_id, limit)

        # ── Strategy D (fallback): Playwright page feed ─────────────────────
        if page_id and not items:
            logger.info("Strategy D: trying Playwright page feed")
            items_playwright, ocr_items_pw = await self._fetch_playwright(
                page_id, limit, max_scrolls, max_see_more_clicks
            )
            items = items_playwright
            ocr_items.extend(ocr_items_pw)

        # Merge OCR-derived items into output
        all_items = items[:]
        for ocr_item in ocr_items:
            if ocr_item not in all_items:
                all_items.append(ocr_item)

        # ── Hard final fallback: scan all string items for parseable Arabic price lines ──
        if not any(isinstance(item, dict) for item in all_items):
            for item in all_items:
                if isinstance(item, str):
                    parsed, _ = _parse_arabic_price_lines(item)
                    if parsed:
                        structured = []
                        for pl in parsed:
                            structured.append({
                                "raw_text": pl["raw_line"],
                                "normalized_line": pl["normalized_line"],
                                "product_type": pl["product_type"],
                                "category": pl["category"],
                                "price": pl["price"],
                                "min_price": pl.get("min_price"),
                                "max_price": pl.get("max_price"),
                                "unit": pl.get("unit", "per_unit"),
                                "product_group": "fertilized_eggs",
                                "raw_price_range": pl.get("raw_price_range"),
                                "confidence": pl.get("confidence", 0.85),
                                "source_type": "final_fallback_parsed",
                            })
                        logger.warning(
                            f"### FINAL FALLBACK PARSED {len(structured)} items from raw string ###"
                        )
                        self.debug_info["used_structured_only"] = True
                        self.debug_info["structured_items_count"] = len(structured)
                        self.debug_info["parsed_price_lines_count"] = len(structured)
                        return structured[:limit]

        self.debug_info["accepted_posts"] = len(all_items)
        self.debug_info["sample_post_texts"] = [
            (t.get("raw_text", "")[:300] if isinstance(t, dict) else str(t)[:300])
            for t in all_items[:3]
        ]

        # Cache successful page result
        if all_items or self.raw_content:
            _set_cached_fb_page(self.source_id, {
                "posts": all_items[:limit],
                "accepted_post_images": self.debug_info.get("accepted_post_images", []),
                "raw_text_preview": (self.raw_content[:500] if self.raw_content else None),
                "sample_post_texts": self.debug_info.get("sample_post_texts", []),
            })

        logger.info(
            f"Facebook: {len(all_items)} accepted (text={len(items)}, ocr={len(ocr_items)}), "
            f"strategy={self.debug_info.get('strategy_used')}, "
            f"blocked={self.debug_info.get('facebook_blocked')}"
        )
        return all_items[:limit]

    # ── mbasic strategy ──────────────────────────────────────────────────
    async def _fetch_mbasic(self, page_id: str, limit: int) -> list:
        items = []
        urls = _build_attempt_urls(page_id)
        self.debug_info["strategy_used"] = "mbasic_httpx"
        self.debug_info["attempted_urls"] = urls

        for url in urls[:1]:
            try:
                async with AsyncClient(
                    timeout=get_scraper_settings().request_timeout,
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/125.0.0.0 Safari/537.36"
                        ),
                        "Accept-Language": "ar-EG,ar;q=0.9,en;q=0.8",
                    },
                    follow_redirects=True,
                ) as client:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    self.debug_info["fetched_lengths"][url] = len(resp.text)
                    logger.info(f"Fetched {url}: {len(resp.text)} bytes")

                    soup = BeautifulSoup(resp.text, "lxml")
                    page_text = soup.get_text(separator=" ", strip=True).lower()

                    if any(ind in page_text or ind in resp.text.lower() for ind in LOGIN_INDICATORS):
                        self.debug_info["facebook_blocked"] = True
                        self.debug_info["facebook_block_reason"] = f"login_wall_on_{url}"
                        logger.warning(f"Facebook {page_id}: login wall on {url}")
                        continue

                    self.raw_content = resp.text
                    texts = _extract_post_texts(soup, self.debug_info)
                    image_urls = _extract_post_images(soup)
                    self.debug_info["image_urls_found"].extend(image_urls)

                    for text in texts:
                        # Try structured parsing first
                        parsed_lines, _ = _parse_arabic_price_lines(text)
                        if parsed_lines:
                            for pl in parsed_lines:
                                item = {
                                    "raw_text": pl["raw_line"],
                                    "normalized_line": pl["normalized_line"],
                                    "product_type": pl["product_type"],
                                    "category": pl["category"],
                                    "price": pl["price"],
                                    "min_price": pl.get("min_price"),
                                    "max_price": pl.get("max_price"),
                                    "unit": pl.get("unit", "per_unit"),
                                    "product_group": "fertilized_eggs",
                                    "raw_price_range": pl.get("raw_price_range"),
                                    "confidence": pl.get("confidence", 0.85),
                                    "source_type": "mbasic_structured",
                                }
                                if item["raw_text"] not in [x.get("raw_text", "") for x in items if isinstance(x, dict)]:
                                    items.append(item)
                            continue

                        if _is_image_only_post(soup, len(text)):
                            self.debug_info["image_only_detected"] = True
                            if self._ocr_enabled and image_urls:
                                ocr_texts = self._ocr_images(image_urls)
                                for ocr_t in ocr_texts:
                                    items.append(f"[OCR] {ocr_t}")
                            continue
                        if _is_poultry_price_post(text):
                            if text not in items:
                                items.append(text[:2000])
                        else:
                            self.debug_info["rejected_posts"] += 1

                    self.debug_info["rejected_reasons"] = self._get_rejection_samples(texts)
                    break

            except Exception as e:
                logger.warning(f"Facebook fetch failed for {url}: {e}")
                self.debug_info.setdefault("fetch_errors", []).append(str(e))
                continue

        return items[:limit]

    # ── Playwright strategy (with expansion + image extraction) ──────────
    async def _fetch_playwright(
        self, page_id: str, limit: int,
        max_scrolls: int = 2, max_see_more_clicks: int = 5,
    ) -> tuple[list, list[str]]:
        text_items = []
        ocr_items = []
        self.debug_info["strategy_used"] = "playwright"
        urls = _build_attempt_urls(page_id)
        self.debug_info["playwright_urls"] = urls

        try:
            from playwright.async_api import async_playwright

            browser = await _get_shared_browser()
            page = await browser.new_page(
                viewport={"width": 375, "height": 812},
                user_agent=(
                    "Mozilla/5.0 (Linux; Android 10; K) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Mobile Safari/537.36"
                ),
            )

            try:
                for url in urls:
                    try:
                        await page.goto(url, timeout=20000, wait_until="domcontentloaded")
                        try:
                            await page.wait_for_selector("body", timeout=8000)
                        except Exception:
                            logger.warning(f"body wait timeout on {url}, proceeding anyway")
                        await page.wait_for_timeout(2000)

                        page_text = await page.inner_text("body")
                        page_text_lower = page_text.lower()
                        if any(ind in page_text_lower for ind in LOGIN_INDICATORS):
                            self.debug_info["facebook_blocked"] = True
                            self.debug_info["facebook_block_reason"] = f"login_wall_on_{url}"
                            logger.warning(f"Facebook {page_id}: login wall on {url} via playwright")
                            continue

                        # Click "See more" / "عرض المزيد" links
                        expanded = await self._click_see_more(page, max_clicks=max_see_more_clicks)
                        self.debug_info["see_more_clicked"] = expanded

                        # Scroll
                        blocked = False
                        for _ in range(max_scrolls):
                            await page.evaluate("window.scrollBy(0, 800)")
                            await page.wait_for_timeout(1500)
                            page_text_lower = (await page.inner_text("body")).lower()
                            if any(ind in page_text_lower for ind in LOGIN_INDICATORS):
                                self.debug_info["facebook_blocked"] = True
                                blocked = True
                                break
                        if blocked:
                            continue

                        # Collect images from rendered DOM via Playwright
                        img_data = await self._extract_playwright_images(page)
                        self.debug_info["all_images_count"] = img_data["all_count"]
                        self.debug_info["rejected_image_urls_sample"] = img_data["rejected_samples"]
                        self.debug_info["image_filter_reasons"] = img_data["filter_reasons"]
                        accepted_images = img_data["accepted"]
                        self.debug_info["accepted_post_images"] = accepted_images
                        self.debug_info["image_urls_found"].extend(accepted_images)

                        # Store for optional OCR-after-collection
                        self._collected_accepted_images = accepted_images

                        # Collect text from rendered page
                        html = await page.content()
                        if not self.raw_content:
                            self.raw_content = html
                        soup = BeautifulSoup(html, "lxml")
                        texts = _extract_post_texts(soup, self.debug_info)

                        # Extract text items
                        for text in texts:
                            # Try structured parsing first
                            parsed_lines, _ = _parse_arabic_price_lines(text)
                            if parsed_lines:
                                for pl in parsed_lines:
                                    item = {
                                        "raw_text": pl["raw_line"],
                                        "normalized_line": pl["normalized_line"],
                                        "product_type": pl["product_type"],
                                        "category": pl["category"],
                                        "price": pl["price"],
                                        "min_price": pl.get("min_price"),
                                        "max_price": pl.get("max_price"),
                                        "unit": pl.get("unit", "per_unit"),
                                        "product_group": "fertilized_eggs",
                                        "raw_price_range": pl.get("raw_price_range"),
                                        "confidence": pl.get("confidence", 0.85),
                                        "source_type": "playwright_page_feed_structured",
                                    }
                                    if item["raw_text"] not in [x.get("raw_text", "") for x in text_items if isinstance(x, dict)]:
                                        text_items.append(item)
                                continue
                            if _is_poultry_price_post(text):
                                if text not in text_items:
                                    text_items.append(text[:2000])
                            else:
                                self.debug_info["rejected_posts"] += 1
                        self._collected_text_items = text_items.copy()

                        # OCR only on accepted post images (if enabled)
                        if self._ocr_enabled and accepted_images:
                            ocr_texts = self._ocr_images(accepted_images)
                            for ocr_t in ocr_texts:
                                is_dup = any(kw in " ".join(text_items) for kw in ocr_t.split()[:5])
                                if not is_dup:
                                    ocr_items.append(f"[OCR] {ocr_t}")

                        if text_items or ocr_items:
                            break

                    except Exception as e:
                        logger.warning(f"Playwright fetch failed for {url}: {e}")
                        continue

            finally:
                await page.close()

        except Exception as e:
            logger.warning(f"Playwright not available: {e}")
            self.debug_info["playwright_error"] = str(e)

        return text_items[:limit], ocr_items[:limit]

    # ── Auto-discover price posts from Facebook page feed ────────────────
    async def _discover_latest_posts_from_page(
        self, page_id: str,
        max_posts_scan: int = 10,
        max_price_posts: int = 3,
    ) -> list[dict]:
        """
        Open Facebook page, scroll to load recent posts, and try to parse
        price lines from each post text block.
        Returns structured dict items (or empty list).
        """
        structured_items: list[dict] = []
        self.debug_info["strategy_used"] = "auto_discover"
        urls = _build_attempt_urls(page_id)
        self.debug_info["auto_discover_urls"] = urls
        post_debug_list = []
        price_post_count = 0

        browser = None
        try:
            browser = await _get_shared_browser()
        except Exception:
            await _reset_shared_browser()
            browser = await _get_shared_browser()

        page = await browser.new_page(
            viewport={"width": 375, "height": 812},
            user_agent=(
                "Mozilla/5.0 (Linux; Android 10; K) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Mobile Safari/537.36"
            ),
        )
        try:
            for url in urls:
                if structured_items:
                    break
                try:
                    await page.goto(url, timeout=20000, wait_until="domcontentloaded")
                    try:
                        await page.wait_for_selector("body", timeout=8000)
                    except Exception:
                        pass
                    await page.wait_for_timeout(3000)

                    body_text = await page.inner_text("body")
                    if any(ind in body_text.lower() for ind in LOGIN_INDICATORS):
                        self.debug_info["facebook_blocked"] = True
                        self.debug_info["facebook_block_reason"] = f"login_wall_on_{url}"
                        logger.warning(f"Auto-discover: login wall on {url}")
                        continue

                    # Scroll to load posts
                    for _ in range(max_posts_scan):
                        await page.evaluate("window.scrollBy(0, 600)")
                        await page.wait_for_timeout(1500)

                    # Expand "See more" buttons
                    try:
                        await self._click_see_more(page, max_clicks=5)
                    except Exception:
                        pass

                    await page.wait_for_timeout(1000)

                    # Extract all post-like elements from the DOM
                    post_entries = await page.evaluate("""
                        () => {
                            const results = [];
                            const posts = document.querySelectorAll(
                                '[role="article"], ' +
                                '[data-testid*="post"], ' +
                                '[class*="userContent"], ' +
                                '[class*="story_body"], ' +
                                'div[class*="fbUserContent"]'
                            );
                            const seen = new Set();
                            posts.forEach(el => {
                                const text = (el.innerText || '').trim();
                                if (text.length > 30 && !seen.has(text)) {
                                    seen.add(text);
                                    // Find permalink
                                    const link = el.querySelector('a[href*="/posts/"], a[href*="/photo/"]');
                                    results.push({
                                        text: text,
                                        permalink: link ? link.href : '',
                                        html: el.innerHTML.substring(0, 100),
                                    });
                                }
                            });
                            return results;
                        }
                    """)
                    post_entries = post_entries or []

                    logger.info(
                        f"Auto-discover: found {len(post_entries)} post elements on {url}"
                    )

                    for entry in post_entries[:max_posts_scan]:
                        if price_post_count >= max_price_posts:
                            break

                        post_text = entry.get("text", "")
                        post_url = entry.get("permalink", "")

                        if not post_text or len(post_text) < 50:
                            continue

                        detected_date = _extract_post_date(post_text)
                        parsed_lines, rejected_lines = _parse_arabic_price_lines(post_text)

                        post_debug = {
                            "index": len(post_debug_list),
                            "url": post_url,
                            "text_length": len(post_text),
                            "parsed_count": len(parsed_lines),
                            "rejected_count": len(rejected_lines),
                            "detected_date": detected_date,
                            "is_price_post": len(parsed_lines) > 0,
                        }
                        post_debug_list.append(post_debug)

                        if parsed_lines and price_post_count < max_price_posts:
                            price_post_count += 1
                            logger.info(
                                f"Auto-discover: price post #{price_post_count} "
                                f"({len(parsed_lines)} lines) detected_date={detected_date}"
                            )
                            for pl in parsed_lines:
                                item = {
                                    "raw_text": pl["raw_line"],
                                    "normalized_line": pl["normalized_line"],
                                    "product_type": pl["product_type"],
                                    "category": pl["category"],
                                    "price": pl["price"],
                                    "min_price": pl.get("min_price"),
                                    "max_price": pl.get("max_price"),
                                    "unit": pl.get("unit", "per_unit"),
                                    "product_group": "fertilized_eggs",
                                    "raw_price_range": pl.get("raw_price_range"),
                                    "confidence": pl.get("confidence", 0.85),
                                    "source_type": "auto_discover",
                                    "post_url": post_url,
                                    "detected_date": detected_date,
                                }
                                if item["raw_text"] not in [x.get("raw_text", "") for x in structured_items]:
                                    structured_items.append(item)

                    if price_post_count > 0:
                        logger.info(
                            f"Auto-discover: stopping after {price_post_count} price posts "
                            f"({len(structured_items)} structured lines)"
                        )

                except Exception as e:
                    logger.warning(f"Auto-discover failed for {url}: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Auto-discover Playwright error: {e}")
        finally:
            try:
                await page.close()
            except Exception:
                pass

        self.debug_info["auto_discover_post_debug"] = post_debug_list
        self.debug_info["discovered_posts_count"] = len(post_entries) if 'post_entries' in dir() else 0
        self.debug_info["discovered_price_posts_count"] = price_post_count
        self.debug_info["parsed_price_lines_count"] = len(structured_items)

        if structured_items:
            self.debug_info["used_structured_only"] = True
            self.debug_info["structured_items_count"] = len(structured_items)
            self.debug_info["accepted_posts"] = len(structured_items)

        logger.info(
            f"Auto-discover result: {len(structured_items)} structured items "
            f"from {price_post_count} price posts"
        )
        return structured_items

    async def _extract_playwright_images(self, page) -> dict:
        result = {"accepted": [], "rejected": [], "all_count": 0,
                   "rejected_samples": [], "filter_reasons": []}
        try:
            raw_items = await page.evaluate("""
                () => {
                    const items = [];
                    document.querySelectorAll('img').forEach(el => {
                        const w = el.naturalWidth || 0;
                        const h = el.naturalHeight || 0;
                        items.push({
                            src: el.src || '',
                            currentSrc: el.currentSrc || '',
                            w: w, h: h,
                            dataset: el.dataset?.imgperflogname || '',
                            parentHref: (el.closest('a')?.href) || '',
                            role: el.getAttribute('role') || '',
                        });
                    });
                    document.querySelectorAll('[role="img"]').forEach(el => {
                        const bg = window.getComputedStyle(el).backgroundImage;
                        if (bg && bg !== 'none') {
                            const m = bg.match(/url\\(["\\']?([^)"\\']+)["\\']?\\)/);
                            if (m) items.push({ src: m[1], currentSrc: '', w: 0, h: 0, dataset: '', parentHref: '', role: 'img' });
                        }
                    });
                    document.querySelectorAll('[style*="background"]').forEach(el => {
                        const bg = el.style.backgroundImage || el.style.background || '';
                        const m = bg.match(/url\\(["\\']?([^)"\\']+)["\\']?\\)/);
                        if (m) items.push({ src: m[1], currentSrc: '', w: 0, h: 0, dataset: '', parentHref: '', role: 'img' });
                    });
                    return items;
                }
            """)
        except Exception as e:
            logger.debug("Playwright image extraction failed: %s", e)
            return result

        accepted = []
        rejected = []
        rejected_samples = []
        filter_reasons = []

        def is_profile_image(w: int, h: int) -> bool:
            if w == 0 or h == 0:
                return False
            if w < 400 or h < 400:
                return True
            if w == h and w < 800:
                return True
            return False

        for item in raw_items:
            url = item.get("src") or ""
            w, h = item.get("w", 0), item.get("h", 0)

            if not url or not url.startswith("http"):
                continue

            if _is_reject_image_url(url) or is_profile_image(w, h):
                rejected.append(url)
                if len(rejected_samples) < 5:
                    rejected_samples.append(url)
                if is_profile_image(w, h):
                    filter_reasons.append(f"صورة شخصية {w}x{h}: {url[:60]}")
                else:
                    reason = "حجم مصغر" if REJECT_IMAGE_SIZE.search(url) else "عنصر واجهة"
                    filter_reasons.append(f"{reason}: {url[:80]}")
                continue

            if _is_accepted_post_image(url):
                accepted.append(url)
            else:
                rejected.append(url)
                if len(rejected_samples) < 5:
                    rejected_samples.append(url)
                filter_reasons.append(f"ليست صورة منشور: {url[:80]}")

        return {
            "accepted": accepted,
            "rejected": rejected,
            "all_count": len(accepted) + len(rejected),
            "rejected_samples": rejected_samples[:5],
            "filter_reasons": filter_reasons[:10],
        }

    async def _click_see_more(self, page, max_clicks: int = 5) -> int:
        count = 0
        try:
            for _ in range(5):
                clicked = await page.evaluate("""
                    () => {
                        const texts = ['عرض المزيد', 'See more', 'المزيد'];
                        let c = 0;
                        document.querySelectorAll('a, span, div, button, span[dir="auto"], div[role="button"]').forEach(el => {
                            const t = (el.textContent || '').trim();
                            if (texts.includes(t)) {
                                el.click();
                                c++;
                            }
                        });
                        return c;
                    }
                """)
                clicked = int(clicked or 0)
                if clicked == 0:
                    break
                count += clicked
                await page.wait_for_timeout(800)
                if count >= max_clicks:
                    break
        except Exception:
            pass
        return count

    def _ocr_images(self, image_urls: list[str]) -> list[str]:
        results: list[str] = []
        seen = set()
        max_imgs = getattr(self, "_max_images", 2)
        created = 0
        total_conf = 0.0
        accepted_lines = 0
        rejected_lines = 0
        structured_matches: list[dict] = []
        normalized_products: list[dict] = []

        for url in image_urls[:max_imgs]:
            if url in seen:
                continue
            seen.add(url)

            raw_text, avg_conf = _ocr_image_url(url)
            if not raw_text or len(raw_text.strip()) <= 5:
                rejected_lines += 1
                continue

            # Score the image content
            score = _score_ocr_text(raw_text)
            if score < _SCORE_MINIMUM:
                rejected_lines += 1
                continue

            accepted_lines += 1
            total_conf += avg_conf

            normalized = _normalize_price_text(raw_text)
            corrected = _apply_ocr_corrections(normalized)
            fuzzy_cleaned = _fuzzy_arabic_cleanup(corrected)

            self.debug_info["ocr_text_preview"].append(corrected[:150])
            self.debug_info["normalized_ocr_text"].append(fuzzy_cleaned[:300])
            self.debug_info["extracted_numbers"].extend(_extract_numbers(corrected))

            # Structured extraction
            structured = _extract_structured_ocr(fuzzy_cleaned)
            parsed = _detect_product_type(corrected)

            if structured:
                structured_matches.append({
                    "url": url,
                    "text": fuzzy_cleaned[:200],
                    "product_group": structured["product_group"],
                    "product_type": structured["product_type"],
                    "category": structured["category"],
                    "price": structured["price"],
                    "unit": structured["unit"],
                })
                normalized_products.append({
                    "product_type": structured["product_type"],
                    "category": structured["category"],
                    "price": structured["price"],
                    "unit": structured["unit"],
                    "product_group": structured["product_group"],
                })
                results.append(fuzzy_cleaned)
                created += 1
            elif parsed and parsed.get("price"):
                # Fallback to legacy detection
                results.append(corrected)
                created += 1
                structured_matches.append({
                    "url": url,
                    "text": corrected[:200],
                    "product_group": parsed.get("product_group", "unknown"),
                    "product_type": parsed.get("product_type", "unknown"),
                    "category": parsed.get("category", "unknown"),
                    "price": parsed.get("price"),
                    "unit": parsed.get("unit"),
                })

        avg = total_conf / max(accepted_lines, 1)
        self.debug_info["ocr_items_created"] += created
        self.debug_info["ocr_text_preview"] = self.debug_info["ocr_text_preview"][:max_imgs]
        self.debug_info["ocr_confidence_avg"] = round(float(avg), 3)
        self.debug_info["accepted_ocr_lines"] = accepted_lines
        self.debug_info["rejected_ocr_lines"] = rejected_lines
        self.debug_info["structured_matches"] = structured_matches
        self.debug_info["normalized_products"] = normalized_products
        return results

    # ── Direct post URLs strategy (primary) ──────────────────────────────
    async def _fetch_direct_posts(
        self, post_urls: list[str], limit: int,
    ) -> tuple[list, list[str]]:
        text_items: list = []
        ocr_items: list[str] = []
        self.debug_info["strategy_used"] = "direct_posts"
        self.debug_info["per_post_debug"] = []
        self.debug_info["direct_post_text"] = None
        self.debug_info["parsed_price_lines"] = []
        self.debug_info["rejected_lines"] = []
        self.debug_info["extracted_records_preview"] = []
        text_items_seen: set[str] = set()

        logger.warning("### DIRECT POSTS PARSER ACTIVE ###")
        logger.info(f"Direct posts: opening {len(post_urls[:limit])} URLs for source {self.source.id}")
        browser = None
        try:
            browser = await _get_shared_browser()
        except Exception:
            logger.warning("Playwright browser error, resetting and retrying")
            await _reset_shared_browser()
            browser = await _get_shared_browser()

        page = await browser.new_page(
            viewport={"width": 375, "height": 812},
            user_agent=(
                "Mozilla/5.0 (Linux; Android 10; K) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Mobile Safari/537.36"
            ),
        )
        try:
            for post_url in post_urls[:limit]:
                post_debug = {
                    "url": post_url, "text_length": 0,
                    "images_found": [], "ocr_text_preview": [],
                    "extracted_numbers": [], "status": "pending",
                    "parsed_count": 0, "rejected_count": 0,
                    "full_post_text": None,
                }
                try:
                    await page.goto(post_url, timeout=20000, wait_until="domcontentloaded")
                    try:
                        await page.wait_for_selector("body", timeout=8000)
                    except Exception:
                        pass
                    await page.wait_for_timeout(2000)

                    body_text = await page.inner_text("body")
                    post_debug["text_length"] = len(body_text)

                    if any(ind in body_text.lower() for ind in LOGIN_INDICATORS):
                        post_debug["status"] = "blocked"
                        self.debug_info.setdefault("facebook_blocked", True)
                        self.debug_info["facebook_block_reason"] = f"login_wall_on_{post_url}"
                        self.debug_info["per_post_debug"].append(post_debug)
                        continue

                    # Click all "See more" / "عرض المزيد" links aggressively
                    see_more_count = await self._click_see_more(page, max_clicks=10)
                    post_debug["see_more_clicked"] = see_more_count

                    # ── Extract full post text from article container ──
                    post_text = await page.evaluate("""
                        () => {
                            const article = document.querySelector('[role="article"]');
                            if (article && article.innerText.trim().length > 50)
                                return article.innerText;
                            const msg = document.querySelector(
                                '[data-testid="post_message"], [class*="userContent"], '
                                '[class*="story_body"], div[class*="fbUserContent"]'
                            );
                            if (msg && msg.innerText.trim().length > 50)
                                return msg.innerText;
                            return document.body.innerText;
                        }
                    """)
                    post_text = str(post_text or "")
                    post_debug["full_post_text"] = post_text[:2000]

                    # ── Parse price lines ─────────────────────────────
                    all_parsed: list[dict] = []
                    all_rejected: list[str] = []

                    if post_text and len(post_text.strip()) > 50:
                        parsed_lines, rejected_lines = _parse_arabic_price_lines(post_text)
                        all_parsed = parsed_lines
                        all_rejected = rejected_lines
                        logger.info(
                            f"Post {post_url}: parsed {len(all_parsed)} structured lines, "
                            f"{len(all_rejected)} rejected"
                        )

                        # Create ONE structured dict per parsed line
                        for pl in parsed_lines:
                            item = {
                                "raw_text": pl["raw_line"],
                                "normalized_line": pl["normalized_line"],
                                "product_type": pl["product_type"],
                                "category": pl["category"],
                                "price": pl["price"],
                                "min_price": pl.get("min_price"),
                                "max_price": pl.get("max_price"),
                                "unit": pl.get("unit", "per_unit"),
                                "product_group": "fertilized_eggs",
                                "raw_price_range": pl.get("raw_price_range"),
                                "confidence": pl.get("confidence", 0.85),
                                "source_type": "facebook_post_text",
                            }
                            logger.info(
                                f"Parsed structured line: {pl['raw_line'][:80]} -> "
                                f"{pl['product_type']}/{pl['category']} @ {pl['price']}"
                            )
                            dedup_key = pl.get("normalized_line", pl["raw_line"])
                            if dedup_key not in text_items_seen:
                                text_items_seen.add(dedup_key)
                                text_items.append(item)

                    # Extract images for debug info only (not for saving)
                    img_data = await self._extract_playwright_images(page)
                    accepted_images = img_data["accepted"]
                    self.debug_info["all_images_count"] += img_data["all_count"]
                    self.debug_info["rejected_image_urls_sample"].extend(img_data["rejected_samples"])
                    self.debug_info["image_filter_reasons"].extend(img_data["filter_reasons"])
                    self.debug_info["accepted_post_images"].extend(accepted_images)
                    self.debug_info["image_urls_found"].extend(accepted_images)
                    self._collected_accepted_images.extend(accepted_images)
                    post_debug["images_found"] = accepted_images

                    # Fallback: always try HTML parsing when evaluate text didn't produce results
                    if not all_parsed:
                        logger.info(f"Post {post_url}: Playwright article text empty, trying HTML fallback")
                        html = await page.content()
                        if not self.raw_content:
                            self.raw_content = html
                        soup = BeautifulSoup(html, "lxml")
                        fallback_texts = _extract_post_texts(soup, self.debug_info)
                        for fb_text in fallback_texts:
                            fb_parsed, fb_rejected = _parse_arabic_price_lines(fb_text)
                            for pl in fb_parsed:
                                item = {
                                    "raw_text": pl["raw_line"],
                                    "normalized_line": pl["normalized_line"],
                                    "product_type": pl["product_type"],
                                    "category": pl["category"],
                                    "price": pl["price"],
                                    "min_price": pl.get("min_price"),
                                    "max_price": pl.get("max_price"),
                                    "unit": pl.get("unit", "per_unit"),
                                    "product_group": "fertilized_eggs",
                                    "raw_price_range": pl.get("raw_price_range"),
                                    "confidence": pl.get("confidence", 0.85),
                                    "source_type": "facebook_post_text_fallback",
                                }
                                logger.info(f"Fallback parsed line: {pl['raw_line'][:80]} -> {pl['product_type']}/{pl['category']} @ {pl['price']}")
                                dedup_key = pl.get("normalized_line", pl["raw_line"])
                                if dedup_key not in text_items_seen:
                                    text_items_seen.add(dedup_key)
                                    text_items.append(item)
                                    all_parsed.append(pl)
                            if not fb_parsed:
                                logger.info(f"Fallback text had no parsable lines: {fb_text[:100]}")

                    # Store debug info
                    post_debug["parsed_count"] = len(all_parsed)
                    post_debug["rejected_count"] = len(all_rejected)
                    self.debug_info["direct_post_text"] = post_text[:5000]
                    self.debug_info["parsed_price_lines"].extend(all_parsed)
                    self.debug_info["rejected_lines"].extend(all_rejected)
                    self.debug_info["extracted_records_preview"].extend([
                        {
                            "product_type": p["product_type"],
                            "category": p["category"],
                            "price": p["price"],
                            "unit": p["unit"],
                            "product_group": p["product_group"],
                            "raw_text": p["raw_line"],
                            "confidence": p["confidence"],
                        }
                        for p in all_parsed
                    ])

                    post_debug["status"] = "success"
                except Exception as e:
                    post_debug["status"] = f"error: {str(e)[:100]}"
                self.debug_info["per_post_debug"].append(post_debug)
        except Exception as e:
            logger.warning(f"Direct posts playwright failed: {e}")
        finally:
            try:
                await page.close()
            except Exception:
                pass

        # HARD GUARD: return ONLY structured dicts if any parsed lines were found
        structured_only = [it for it in text_items if isinstance(it, dict)]
        if structured_only:
            logger.warning(
                f"### STRUCTURED RETURN ACTIVE: {len(structured_only)} ###"
            )
            logger.info(
                f"HARD RETURN structured items only: {len(structured_only)}"
            )
            return structured_only, []

        # Only if NO structured items at all, MAY use old text fallback
        # (this path should rarely trigger when post URLs are configured correctly)
        if text_items:
            logger.warning(
                f"No structured items from {len(post_urls)} post URLs; "
                f"falling back to {len(text_items)} raw text items"
            )
        max_items = min(limit, 20)
        return text_items[:max_items], ocr_items[:max_items]

    def _get_rejection_samples(self, texts: list[str]) -> list[str]:
        reasons = []
        for t in texts[:10]:
            if any(phrase in t for phrase in FB_REJECT_PHRASES):
                match = next(p for p in FB_REJECT_PHRASES if p in t)
                reasons.append(f"rejected by phrase '{match}': {t[:150]}")
        for t in texts[:10]:
            if not any(kw in t for kw in FB_TARGET_KEYWORDS):
                reasons.append(f"no target keywords: {t[:150]}")
                break
        if not reasons:
            for t in texts[:5]:
                reasons.append(f"no number found: {t[:150]}")
                break
        return reasons[:10]
