"""
Smart region detection for complex poultry price poster images using OpenCV.
Detects high-contrast price cards/circles, crops regions, runs numeric OCR,
and matches nearby Arabic labels to known breeds.

OpenCV is optional. If unavailable, detect_regions returns an empty list.
"""
import io
import logging
from typing import Optional, Any

from PIL import Image

logger = logging.getLogger(__name__)

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    cv2 = None
    np = None
    CV2_AVAILABLE = False
    logger.info("OpenCV not available — region detection will be skipped")

CHICK_BREED_MAP: dict[str, str] = {
    "أبيض شركات": "white",
    "ملون جامبو": "sasso",
    "ساسو": "sasso",
    "روزي": "sasso",
    "بلدي": "baladi",
    "هجين": "local",
    "بط مولارد": "duck",
    "بط مسكوفي": "duck",
    "رومي": "turkey",
    "سمان": "quail",
    "السلالات": "white",
}

SORTED_BREEDS = sorted(CHICK_BREED_MAP.keys(), key=len, reverse=True)

MODIFIERS = ["أرضو", "واصل", "تنفيذ", "استلام", "فرز", "عادي", "ممتاز"]

_EXTENDED_DIGIT_MAP = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def _normalize_all_digits(text: str) -> str:
    text = text.translate(_EXTENDED_DIGIT_MAP)
    text = text.replace("٫", ".").replace(",", ".")
    return text


def _is_card_contour(contour: Any, img_area: int, scale: float) -> bool:
    """Check if a contour looks like a price card (circular or rectangular, not too small/large)."""
    x, y, w, h = cv2.boundingRect(contour)
    area = cv2.contourArea(contour)
    img_area_scaled = img_area * scale * scale

    min_area = img_area_scaled * 0.002
    max_area = img_area_scaled * 0.15

    if area < min_area or area > max_area:
        return False

    aspect = w / h if h > 0 else 0
    if aspect < 0.3 or aspect > 3.0:
        return False

    return True


def _find_nearby_text(
    img: Any,
    cx: int,
    cy: int,
    region_w: int,
    region_h: int,
    padding: int = 80,
) -> str:
    """Extract Arabic text from the area above/left/right of a detected price region."""
    import pytesseract

    h, w = img.shape[:2]
    x1 = max(0, cx - region_w - padding)
    y1 = max(0, cy - region_h - padding)
    x2 = min(w, cx + region_w * 2 + padding)
    y2 = min(h, cy + region_h + padding)

    label_roi = img[y1:y2, x1:x2]
    if label_roi.size == 0:
        return ""

    gray = cv2.cvtColor(label_roi, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    scaled = cv2.resize(thresh, None, fx=2, fy=2, interpolation=cv2.INTER_LANCZOS4)

    try:
        lang = "ara" if "ara" in pytesseract.get_languages() else "ara+eng"
        text = pytesseract.image_to_string(scaled, lang=lang, config="--psm 6 --oem 3")
        return text.strip()
    except Exception:
        return ""


def _match_breed_in_text(text: str) -> Optional[tuple[str, str]]:
    """Find the first known breed match in text. Returns (breed_text, category)."""
    for breed in SORTED_BREEDS:
        if breed in text:
            return breed, CHICK_BREED_MAP[breed]
    return None


def _extract_price_from_roi(roi: Any) -> Optional[float]:
    """Run numeric OCR on a cropped region to extract a price."""
    import pytesseract

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    scaled = cv2.resize(thresh, None, fx=3, fy=3, interpolation=cv2.INTER_LANCZOS4)

    config = "--psm 8 --oem 3 -c tessedit_char_whitelist=0123456789٠١٢٣٤٥٦٧٨٩.,٫"
    text = pytesseract.image_to_string(scaled, config=config)
    normalized = _normalize_all_digits(text.strip())
    import re
    numbers = re.findall(r"(\d+(?:\.\d+)?)", normalized)
    for n in numbers:
        val = float(n)
        if 1 < val < 10000:
            return val
    return None


async def detect_regions(image_bytes: bytes) -> list[dict]:
    """Detect price regions in a poster image and return candidate rows.

    Returns list of dicts with: product_type, category, raw_product_name,
    price, unit, confidence, confidence_reason, extraction_method.
    """
    if not CV2_AVAILABLE:
        logger.info("Region detection skipped: OpenCV not available")
        return []

    try:
        import pytesseract
    except ImportError:
        return []

    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return []
    except Exception as e:
        logger.warning(f"Region detection: failed to decode image: {e}")
        return []

    h, w = img.shape[:2]
    img_area = w * h
    scale = max(w, h) / 500  # normalize scaling

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 21, 4,
    )

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candidates = []
    seen_centers = set()

    for contour in contours:
        if not _is_card_contour(contour, img_area, scale):
            continue

        x, y, rw, rh = cv2.boundingRect(contour)
        cx, cy = x + rw // 2, y + rh // 2

        grid_key = (cx // 30, cy // 30)
        if grid_key in seen_centers:
            continue
        seen_centers.add(grid_key)

        margin = max(2, int(rw * 0.05))
        x1 = max(0, x - margin)
        y1 = max(0, y - margin)
        x2 = min(w, x + rw + margin)
        y2 = min(h, y + rh + margin)
        roi = img[y1:y2, x1:x2]
        if roi.size == 0:
            continue

        price = _extract_price_from_roi(roi)
        if price is None:
            continue

        nearby_text = _find_nearby_text(img, cx, cy, rw, rh)
        breed_match = _match_breed_in_text(nearby_text) if nearby_text else None

        if breed_match:
            breed_text, category = breed_match
            modifiers = [m for m in MODIFIERS if m in nearby_text]
            raw_name = breed_text
            if modifiers:
                raw_name = f"{breed_text} {' '.join(modifiers)}"
            candidates.append({
                "product_type": "day_old_chicks",
                "category": category,
                "raw_product_name": raw_name,
                "price": price,
                "unit": "per_unit",
                "confidence": "high",
                "confidence_reason": f"region detection: '{breed_text}' label near price {price}",
                "extraction_method": "region_detection",
            })
        else:
            candidates.append({
                "product_type": "day_old_chicks",
                "category": "white",
                "raw_product_name": f"سعر {price}",
                "price": price,
                "unit": "per_unit",
                "confidence": "low",
                "confidence_reason": f"region detection: price {price} found, no label nearby",
                "extraction_method": "region_detection",
            })

    if not candidates:
        logger.info("Region detection: no candidate price regions found")
        return []

    logger.info(f"Region detection: {len(candidates)} candidates found")
    return candidates
