"""
Test chick poster parser for OCR-extracted text.
"""
import pytest
from app.services.chick_poster_parser import parse_chick_poster_text, _is_chick_poster, _normalize_all_digits


def test_detect_chick_poster():
    assert _is_chick_poster("سعر الكتكوت اليوم") is True
    assert _is_chick_poster("كتاكيت عمر يوم") is True
    assert _is_chick_poster("السلالات") is True
    assert _is_chick_poster("بيض مخصب ابيض 15") is False


def test_chick_poster_simple_lines():
    text = """كتاكيت عمر يوم
أبيض شركات 25
ساسو 22
بلدي 18"""
    items, rejected = parse_chick_poster_text(text)
    assert len(items) == 3
    white = [i for i in items if i["category"] == "white"]
    sasso = [i for i in items if i["category"] == "sasso"]
    baladi = [i for i in items if i["category"] == "baladi"]
    assert len(white) >= 1
    assert len(sasso) >= 1
    assert len(baladi) >= 1
    assert all(i["product_type"] == "day_old_chicks" for i in items)
    assert all(i["unit"] == "per_unit" for i in items)


def test_chick_poster_with_modifiers():
    text = """كتاكيت
أبيض شركات واصل 25
ملون جامبو أرضو 23
ساسو تنفيذ 20"""
    items, rejected = parse_chick_poster_text(text)
    assert len(items) == 3
    raw_names = [i["raw_product_name"] for i in items]
    assert any("واصل" in r for r in raw_names)
    assert any("أرضو" in r for r in raw_names)
    assert any("تنفيذ" in r for r in raw_names)


def test_chick_poster_without_header():
    """Should still detect chick poster and parse when chick keyword is present."""
    text = """كتاكيت
أبيض شركات 25
ملون جامبو 23
بلدي 18"""
    items, rejected = parse_chick_poster_text(text)
    assert len(items) == 3


def test_chick_poster_no_prices():
    """Text with breeds but no prices should return empty."""
    text = """كتاكيت
أبيض شركات
ملون جامبو
بلدي"""
    items, rejected = parse_chick_poster_text(text)
    assert len(items) == 0


def test_egg_text_not_confused_as_chick():
    """Fertilized egg text should NOT be parsed as chick poster."""
    text = """بيض مخصب ابيض شركات 15
بيض مخصب ساسو 11"""
    items, rejected = parse_chick_poster_text(text)
    assert len(items) == 0


def test_normalize_arabic_digits():
    assert _normalize_all_digits("١٥") == "15"
    assert _normalize_all_digits("١٢.٥") == "12.5"
    assert _normalize_all_digits("۰۱۲۳") == "0123"
    assert _normalize_all_digits("سعر ٥٠ ج") == "سعر 50 ج"


def test_all_breeds_parsed():
    text = """كتاكيت
أبيض شركات 25
ملون جامبو 24
ساسو 23
روزي 22
بلدي 18
هجين 17"""
    items, rejected = parse_chick_poster_text(text)
    assert len(items) >= 6
    categories = {i["category"] for i in items}
    assert "white" in categories
    assert "sasso" in categories
    assert "baladi" in categories
    assert "local" in categories


def test_confidence_high_for_exact_match():
    text = """كتاكيت
أبيض شركات 25"""
    items, rejected = parse_chick_poster_text(text)
    assert len(items) == 1
    assert items[0]["confidence"] == "high"
    assert items[0]["price"] == 25.0


def test_non_chick_text_returns_empty():
    """Non-chick text should return all lines as rejected."""
    text = "هذا النص لا يحتوي على أسعار"
    items, rejected = parse_chick_poster_text(text)
    assert len(items) == 0
    assert len(rejected) == 1


def test_mixed_line_parsing():
    """Complex poster line with multiple prices per breed."""
    text = """كتاكيت
أبيض شركات واصل 25 أرضو 23
ملون جامبو تنفيذ 27"""
    items, rejected = parse_chick_poster_text(text)
    assert len(items) >= 1
