"""
Specialized parser for Arabic chick/poultry price poster images.
Handles complex layouts with prices, product names, and modifiers.
"""
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

CHICK_KEYWORDS = [
    "كتاكيت", "سعر الكتكوت", "السلالات", "عمر يوم",
    "كتكوت", "أسعار الكتاكيت", "دجاج التسمين",
]

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

MODIFIERS = [
    "أرضو", "واصل", "تنفيذ", "استلام", "فرز", "عادي", "ممتاز",
]

MODIFIER_PATTERN = re.compile("|".join(re.escape(m) for m in MODIFIERS))

_EXTENDED_DIGIT_MAP = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def _normalize_all_digits(text: str) -> str:
    text = text.translate(_EXTENDED_DIGIT_MAP)
    text = text.replace("٫", ".").replace(",", ".")
    return text


def _is_chick_poster(text: str) -> bool:
    """Detect if the OCR text is from a chick price poster."""
    return any(kw in text for kw in CHICK_KEYWORDS)


def _extract_prices(text: str) -> list[float]:
    """Extract all price-like numbers from text."""
    normalized = _normalize_all_digits(text)
    numbers = re.findall(r"(\d+(?:\.\d+)?)", normalized)
    return [float(n) for n in numbers if 1 < float(n) < 10000]


def _find_breed(line: str) -> Optional[tuple[str, str, str]]:
    """Find a known breed in a line. Returns (matched_text, category, raw_line_suffix)."""
    for breed in SORTED_BREEDS:
        if breed in line:
            remaining = line.replace(breed, "", 1).strip()
            return breed, CHICK_BREED_MAP[breed], remaining
    return None


def _find_modifiers(line: str) -> list[str]:
    """Find all modifiers in a line."""
    return MODIFIER_PATTERN.findall(line)


def _find_price_in_region(full_text: str, breed_index: int, breed_len: int) -> Optional[float]:
    """Look for the nearest price number near the breed occurrence in the full text."""
    normalized = _normalize_all_digits(full_text)
    before = normalized[max(0, breed_index - 60):breed_index]
    after = normalized[breed_index + breed_len:breed_index + breed_len + 60]

    numbers_before = re.findall(r"(\d+(?:\.\d+)?)", before)
    numbers_after = re.findall(r"(\d+(?:\.\d+)?)", after)

    candidates = []
    for n in numbers_after:
        val = float(n)
        if 1 < val < 10000:
            candidates.append(val)
    for n in reversed(numbers_before):
        val = float(n)
        if 1 < val < 10000:
            candidates.append(val)

    return candidates[0] if candidates else None


def _clean_line(line: str) -> str:
    """Clean a line for parsing."""
    line = line.strip().strip(".:,;- ")
    return line


def parse_chick_poster_text(text: str) -> tuple[list[dict], list[str]]:
    """Parse OCR text from chick price poster images.

    Returns (parsed_items, rejected_lines) where each parsed_item has:
        product_type, category, raw_product_name, price, unit,
        confidence (high/medium/low), confidence_reason
    """
    if not _is_chick_poster(text):
        return [], [text]

    lines = text.split("\n")
    parsed: list[dict] = []
    rejected: list[str] = []
    found_breeds_in_full = set()
    prices = _extract_prices(text)
    full_normalized = _normalize_all_digits(text)

    # Strategy 1: line-by-line breed + price
    for line in lines:
        line = _clean_line(line)
        if not line:
            continue

        breed_match = _find_breed(line)
        if not breed_match:
            continue

        breed_text, category, remaining = breed_match
        found_breeds_in_full.add(breed_text)
        modifiers = _find_modifiers(remaining)

        # Find price in this line
        line_norm = _normalize_all_digits(remaining)
        line_prices = re.findall(r"(\d+(?:\.\d+)?)", line_norm)
        price = None
        for p in line_prices:
            val = float(p)
            if 1 < val < 10000:
                price = val
                break

        if price:
            raw_name = breed_text
            if modifiers:
                raw_name = f"{breed_text} {' '.join(modifiers)}"
            parsed.append({
                "product_type": "day_old_chicks",
                "category": category,
                "raw_product_name": raw_name,
                "price": price,
                "unit": "per_unit",
                "confidence": "high",
                "confidence_reason": f"exact product '{breed_text}' + nearby price {price}",
            })
        else:
            rejected.append(line)

    # Strategy 2: find breeds mentioned elsewhere and pair with nearest price
    for breed in SORTED_BREEDS:
        if breed in full_normalized and breed not in found_breeds_in_full:
            idx = full_normalized.index(breed)
            price = _find_price_in_region(full_normalized, idx, len(breed))
            if price:
                parsed.append({
                    "product_type": "day_old_chicks",
                    "category": CHICK_BREED_MAP[breed],
                    "raw_product_name": breed,
                    "price": price,
                    "unit": "per_unit",
                    "confidence": "medium",
                    "confidence_reason": f"known product '{breed}' + nearby price {price}",
                })
                found_breeds_in_full.add(breed)

    # Strategy 3: if breeds found but no prices, use any available price
    if parsed and not any(p["confidence"] in ("high", "medium") for p in parsed):
        if prices:
            avg_price = round(sum(prices) / len(prices), 1)
            for p in parsed:
                p["price"] = avg_price
                p["confidence"] = "low"
                p["confidence_reason"] = f"product found, estimated price {avg_price} from text"

    # Reject remaining non-breed lines
    for line in lines:
        line = _clean_line(line)
        if not line:
            continue
        if not _find_breed(line) and not any(kw in line for kw in CHICK_KEYWORDS + MODIFIERS + ["ج", "جنيه"]):
            if not re.match(r"^[\d\s.\-:,]+$", line):
                rejected.append(line)

    return parsed, rejected[:30]
