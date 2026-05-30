"""Tests for price normalizer — poultry relevance and price extraction."""
import sys
sys.path.insert(0, ".")
from app.services.scrapers.price_normalizer import (
    is_poultry_relevant, contains_large_money, normalizer,
)


def test_large_money_5_million():
    t = '5 ملايين جنيه لتمكين المرأة البدوية بشمال سيناء'
    assert contains_large_money(t), "Should detect large money (ملايين)"
    assert not is_poultry_relevant(t), "Should reject: money without poultry terms"


def test_large_money_million_no_digits():
    t = 'مليون جنيه لدعم المشروعات الزراعية'
    assert contains_large_money(t), "Should detect million even without leading digits"
    assert not is_poultry_relevant(t)


def test_large_money_thousands():
    t = 'تم تخصيص 500 ألف جنيه للمشروع'
    assert contains_large_money(t)
    assert not is_poultry_relevant(t)


def test_poultry_relevant_chick_price():
    t = 'كتكوت أبيض عمر يوم 35 جنيه'
    assert is_poultry_relevant(t), "Should be poultry-relevant"
    result = normalizer.normalize(t)
    assert result.product_type == "day_old_chicks"
    assert result.price and 5 < result.price < 200
    assert result.category == "white"
    assert result.is_valid()


def test_poultry_relevant_fertilized_eggs():
    t = 'بيض مخصب ساسو 12 جنيه'
    assert is_poultry_relevant(t), "Should be poultry-relevant"
    result = normalizer.normalize(t)
    assert result.product_type == "fertilized_eggs"
    assert result.price and 1 < result.price < 50
    assert result.category == "sasso"
    assert result.is_valid()


def test_reject_large_money_from_normalizer():
    t = '5 ملايين جنيه لتمكين المرأة'
    result = normalizer.normalize(t)
    assert result.price is None, "Should not extract price from large money"


def test_reject_generic_agriculture_news():
    t = 'قال الفاروق انه تم تخصيص 5 ملايين جنيه لتحويل التجمعات الزراعية الي وحدات انتاجية'
    assert contains_large_money(t)
    assert not is_poultry_relevant(t)


def test_chick_normalizer_extracts():
    t = 'سعر كتكوت عمر يوم 25 جنيه للـ 1000'
    result = normalizer.normalize(t)
    assert result.product_type == "day_old_chicks"
    assert result.price and 5 < result.price < 200
    assert result.is_valid()


def test_egg_normalizer_rejects_table_eggs():
    """كرتونة بيض مائدة should be rejected as table eggs, not fertilized eggs."""
    t = 'كرتونة بيض مائدة 130 جنيه'
    result = normalizer.normalize(t)
    assert result.product_group is None, f"Expected None for table eggs, got {result.product_group}"
    assert not result.is_valid(), "Table eggs should not be valid"


def test_setro_white_chick_group_chicks():
    t = 'كتكوت ابيض تسمين 18.00'
    r = normalizer.normalize(t)
    assert r.product_group == "chicks", f"Expected chicks, got {r.product_group}"
    assert r.category == "white"
    assert r.price == 18.0
    assert r.unit == "per_unit"
    assert r.is_valid()


def test_setro_sasso_chick_group_chicks():
    t = 'كتكوت سترو ساسو بيور 08.00'
    r = normalizer.normalize(t)
    assert r.product_group == "chicks", f"Expected chicks, got {r.product_group}"
    assert r.category == "sasso"
    assert r.price == 8.0
    assert r.unit == "per_unit"
    assert r.is_valid()


def test_setro_baladi_chick_group_chicks():
    t = 'كتكوت بلدى 05.50'
    r = normalizer.normalize(t)
    assert r.product_group == "chicks", f"Expected chicks, got {r.product_group}"
    assert r.category == "baladi"
    assert r.price == 5.5
    assert r.unit == "per_unit"
    assert r.is_valid()


def test_setro_turkey_chick_not_day_old():
    t = 'كتكوت رومى 30.00'
    r = normalizer.normalize(t)
    assert r.product_group == "chicks"
    assert r.category == "turkey", f"Expected turkey, got {r.category}"
    assert r.price == 30.0
    assert r.is_valid()


def test_setro_table_eggs_rejected():
    """Table egg phrases should be rejected — not saved."""
    cases = [
        'بيض ابيض بطاريات 85.00',
        'بيض احمر ارضى 78.00',
        'بيض بلدى مائدة 100.00',
        'كراتين بيض مقاس 20ابيض 2460',
        'بيض أبيض بطاريات 85.00',
        'بيض أحمر 85.00',
    ]
    for t in cases:
        r = normalizer.normalize(t)
        assert r.product_group is None, f"'{t}' should be rejected (table egg), got product_group={r.product_group}"
        assert not r.is_valid(), f"'{t}' should not be valid"


def test_fertilized_egg_accepted():
    """Specific fertilized egg phrases should be accepted."""
    cases = [
        ('بيض مخصب ساسو 12 جنيه', 'fertilized_eggs', 'sasso'),
        ('بيض تفريخ أبيض 10 جنيه', 'fertilized_eggs', 'white'),
        ('بيض تسمين 15.00', 'fertilized_eggs', None),
    ]
    for t, expected_group, expected_cat in cases:
        r = normalizer.normalize(t)
        assert r.product_group == expected_group, f"'{t}' expected {expected_group}, got {r.product_group}"
        assert r.product_type == "fertilized_eggs", f"'{t}' expected fertilized_eggs type"
        if expected_cat:
            assert r.category == expected_cat, f"'{t}' expected category {expected_cat}, got {r.category}"
        assert r.is_valid(), f"'{t}' should be valid"


def test_chick_accepted():
    """Chick prices should be accepted."""
    t = 'كتكوت أبيض 18 جنيه'
    r = normalizer.normalize(t)
    assert r.product_group == "chicks", f"Expected chicks, got {r.product_group}"
    assert r.product_type == "day_old_chicks"
    assert r.category == "white"
    assert r.price == 18.0
    assert r.is_valid()


def test_setro_white_in_chick_not_confused_with_egg():
    """Regression: 'ابيض' contains 'بيض' as substring but should not match egg group."""
    t = 'كتكوت ابيض تسمين 18.00'
    r = normalizer.normalize(t)
    assert r.product_group == "chicks", f"Should be chicks, not eggs. Got {r.product_group}"
    assert r.category == "white"
    assert r.price == 18.0


def test_setro_no_date_returns_today():
    t = 'كتكوت بلدى 05.50'
    r = normalizer.normalize(t)
    assert r.recorded_date is not None


def test_fertilized_egg_85():
    """بيض تفريخ 85 جنيه => fertilized_eggs accepted."""
    t = 'بيض تفريخ 85 جنيه'
    assert is_poultry_relevant(t), "Should be poultry-relevant"
    r = normalizer.normalize(t)
    assert r.product_group == "fertilized_eggs", f"Expected fertilized_eggs, got {r.product_group}"
    assert r.product_type == "fertilized_eggs"
    assert r.price == 85.0
    assert r.is_valid()


def test_fertilized_egg_white_90():
    """بيض مخصب أبيض 90 جنيه => fertilized_eggs accepted."""
    t = 'بيض مخصب أبيض 90 جنيه'
    assert is_poultry_relevant(t), "Should be poultry-relevant"
    r = normalizer.normalize(t)
    assert r.product_group == "fertilized_eggs", f"Expected fertilized_eggs, got {r.product_group}"
    assert r.product_type == "fertilized_eggs"
    assert r.category == "white"
    assert r.price == 90.0
    assert r.is_valid()


def test_table_egg_carton_rejected():
    """كرتونة بيض 150 جنيه => rejected (table egg)."""
    t = 'كرتونة بيض 150 جنيه'
    r = normalizer.normalize(t)
    assert r.product_group is None, f"Expected None (table egg), got {r.product_group}"
    assert not r.is_valid()


def test_consumer_broiler_price_rejected():
    """سعر كيلو الفراخ البيضاء 75 => rejected by facebook/news filter (not normalizer alone)."""
    from app.services.scrapers.facebook_scraper import _is_poultry_price_post
    assert not _is_poultry_price_post('سعر كيلو الفراخ البيضاء 75'), "Facebook filter should reject"
    assert not _is_poultry_price_post('كرتونة بيض 150 جنيه'), "Facebook filter should reject table eggs"


def test_facebook_poultry_keywords():
    """Test Facebook scraper keyword filtering logic."""
    from app.services.scrapers.facebook_scraper import _is_poultry_price_post
    assert _is_poultry_price_post('بيض تفريخ 85 جنيه'), "Fertilized egg post should match"
    assert _is_poultry_price_post('كتاكيت أبيض 35 جنيه'), "Chick post should match"
    assert _is_poultry_price_post('سعر البيض المخصب اليوم 95'), "Fertilized egg with price should match"
    assert not _is_poultry_price_post('كرتونة بيض 150 جنيه'), "Table egg carton should be rejected"
    assert not _is_poultry_price_post('سعر كيلو الفراخ البيضاء 75'), "Consumer broiler should be rejected"
    assert not _is_poultry_price_post('وصفة دجاج بالفرن'), "Recipe should be rejected"
    assert not _is_poultry_price_post('أخبار المشاهير اليوم'), "Celebrity news should not match"


def test_facebook_url_extraction():
    """Test _extract_page_id handles various Facebook URL formats."""
    from app.services.scrapers.facebook_scraper import _extract_page_id, _build_attempt_urls
    assert _extract_page_id("https://web.facebook.com/expoeggegypt/") == "expoeggegypt"
    assert _extract_page_id("https://web.facebook.com/HATCHED.EGG.EGYPT/?locale=ar_AR") == "HATCHED.EGG.EGYPT"
    assert _extract_page_id("https://mbasic.facebook.com/expoeggegypt") == "expoeggegypt"
    assert _extract_page_id("https://www.facebook.com/pages/SomePage/") == "SomePage"
    urls = _build_attempt_urls("expoeggegypt")
    assert "mbasic.facebook.com" in urls[0]
    assert "m.facebook.com" in urls[1]
    assert "web.facebook.com" in urls[2]


def test_manual_price_model():
    """Test ManualPriceEntry validation."""
    from app.api.endpoints.prices import ManualPriceEntry
    entry = ManualPriceEntry(
        product_type="fertilized_eggs",
        category="white",
        price=95.0,
        unit="per_unit",
        source_name="مصدر اختباري",
        raw_note="سعر اختباري",
    )
    assert entry.product_type == "fertilized_eggs"
    assert entry.category == "white"
    assert entry.price == 95.0
    assert entry.unit == "per_unit"
    assert entry.source_name == "مصدر اختباري"
    assert entry.raw_note == "سعر اختباري"
    assert entry.recorded_date is None  # defaults to None, backend will use today


if __name__ == "__main__":
    for name, fn in sorted((n, v) for n, v in globals().items() if n.startswith("test_")):
        try:
            fn()
            print(f"  PASS  {name}")
        except AssertionError as e:
            print(f"  FAIL  {name}: {e}")
        except Exception as e:
            print(f"  ERROR {name}: {e}")
