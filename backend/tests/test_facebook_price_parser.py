import sys; sys.path.insert(0, '.')
import pytest
from app.services.scrapers.facebook_scraper import (
    _parse_single_price_line,
    _parse_arabic_price_lines,
)


LINE_TESTS = [
    # (input_line, expected_price, expected_category)
    ("بيض تفريخ ابيض من 10 ل12 ج", 11.0, "white"),
    ("بيض تفريخ ساسو شيفر 8 ج", 8.0, "sasso"),
    ("بيض مخصب ابيض شركات ١٥ج.", 15.0, "white"),
    ("بيض مخصب بلدى هجين 4.5ج", 4.5, "baladi"),
    ("بيض تفريخ بط مولارد 17 ج", 17.0, "duck"),
    ("بيض تفريخ سمان 3 ج", 3.0, "quail"),
    ("بيض تفريخ نعام 800 ج", 800.0, "ostrich"),
    ("بيض تفريخ رومى ابيض 60 ج", 60.0, "turkey"),
]


@pytest.mark.parametrize("line,exp_price,exp_cat", LINE_TESTS)
def test_parse_single_price_line(line, exp_price, exp_cat):
    result = _parse_single_price_line(line)
    assert result is not None, f"Failed to parse: {line}"
    assert result["price"] == exp_price, (
        f"Line: {line} expected price={exp_price}, got {result['price']}"
    )
    assert result["category"] == exp_cat, (
        f"Line: {line} expected category={exp_cat}, got {result['category']}"
    )
    assert result["product_type"] == "fertilized_eggs"
    assert result["product_group"] == "fertilized_eggs"
    assert result["unit"] == "per_unit"
    assert result["confidence"] == 0.9
    print(f"  OK: {line} -> {result['product_type']}/{result['category']} @ {result['price']}")


FULL_POST_TEXT = (
    "بيض تفريخ ابيض من 10 ل12 ج\n"
    "بيض تفريخ ساسو شيفر 8 ج\n"
    "بيض مخصب ابيض شركات ١٥ج.\n"
    "بيض مخصب بلدى هجين 4.5ج\n"
    "بيض تفريخ بط مولارد 17 ج\n"
    "بيض تفريخ سمان 3 ج\n"
    "بيض تفريخ نعام 800 ج\n"
    "بيض تفريخ رومى ابيض 60 ج"
)


def test_parse_arabic_price_lines_full_post():
    parsed, rejected = _parse_arabic_price_lines(FULL_POST_TEXT)
    assert len(parsed) == 8, f"Expected 8 parsed, got {len(parsed)}"
    assert len(rejected) == 0, f"Expected 0 rejected, got {len(rejected)}"

    expected_prices = [11.0, 8.0, 15.0, 4.5, 17.0, 3.0, 800.0, 60.0]
    expected_categories = [
        "white", "sasso", "white", "baladi",
        "duck", "quail", "ostrich", "turkey",
    ]
    for i, p in enumerate(parsed):
        assert p["price"] == expected_prices[i], (
            f"Item {i}: expected price {expected_prices[i]}, got {p['price']}"
        )
        assert p["category"] == expected_categories[i], (
            f"Item {i}: expected category {expected_categories[i]}, got {p['category']}"
        )
        assert p["product_type"] == "fertilized_eggs"
        assert p["unit"] == "per_unit"
        assert p["raw_line"] == FULL_POST_TEXT.split("\n")[i]

    print(f"  OK: All 8 lines parsed correctly with no rejections")


def test_no_raw_line_contains_newline():
    parsed, _ = _parse_arabic_price_lines(FULL_POST_TEXT)
    for i, p in enumerate(parsed):
        assert "\n" not in p["raw_line"], (
            f"Item {i}: raw_line contains newline"
        )
        assert len(p["raw_line"]) < 500, (
            f"Item {i}: raw_line length {len(p['raw_line'])} >= 500"
        )
    print(f"  OK: All 8 raw_lines are single lines under 500 chars")


def test_rejects_table_eggs():
    assert _parse_single_price_line("بيض مائدة 100 ج") is None
    assert _parse_single_price_line("طبق بيض مائدة 85 ج") is None
    assert _parse_single_price_line("كرتونة بيض 150 ج") is None
    print(f"  OK: Table egg lines correctly rejected")


def test_normalizes_arabic_and_eastern_digits():
    result = _parse_single_price_line("بيض تفريخ ساسو ٨ ج")
    assert result is not None
    assert result["price"] == 8.0

    result = _parse_single_price_line("بيض تفريخ نعام ۸۰۰ ج")
    assert result is not None
    assert result["price"] == 800.0

    print(f"  OK: Arabic and Eastern digit normalization works")


def test_normalizes_currency_units():
    result = _parse_single_price_line("بيض تفريخ ساسو 8 جنيه")
    assert result is not None
    assert result["price"] == 8.0

    result = _parse_single_price_line("بيض تفريخ بط 17 ج.م")
    assert result is not None
    assert result["price"] == 17.0

    print(f"  OK: Currency unit normalization works")


def test_handles_removed_decimal_dot_issue():
    """4.5ج must NOT lose its decimal point during normalization."""
    result = _parse_single_price_line("بيض مخصب بلدى هجين 4.5ج")
    assert result is not None
    assert result["price"] == 4.5
    print(f"  OK: Decimal point preserved correctly")


def test_no_false_positive_rejections():
    """These valid lines must all parse successfully."""
    lines = [
        "بيض تفريخ ابيض من 10 ل12 ج",
        "بيض تفريخ ساسو شيفر 8 ج",
        "بيض مخصب ابيض شركات ١٥ج.",
        "بيض مخصب بلدى هجين 4.5ج",
        "بيض تفريخ بط مولارد 17 ج",
        "بيض تفريخ سمان 3 ج",
        "بيض تفريخ نعام 800 ج",
        "بيض تفريخ رومى ابيض 60 ج",
    ]
    for line in lines:
        assert _parse_single_price_line(line) is not None, f"False rejection: {line}"
    print(f"  OK: No false positive rejections")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
