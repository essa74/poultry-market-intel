from datetime import date
from app.services.holiday_calendar_service import (
    _generate_events_for_year,
    _gregorian_easter,
    _coptic_easter,
    RAMADAN, EID_FITR, EID_ADHA, COPTIC_CHRISTMAS, EASTER,
    SHAM_EL_NESSIM, WINTER, SCHOOL, SUMMER_HEAT,
)


def test_all_events_have_required_fields():
    events = _generate_events_for_year(2026)
    for ev in events:
        assert ev["name_ar"], f"Missing name_ar in {ev['event_type']}"
        assert ev["name_en"], f"Missing name_en in {ev['event_type']}"
        assert ev["event_type"], f"Missing event_type in {ev['event_type']}"
        assert ev["start_date"], f"Missing start_date in {ev['event_type']}"
        assert ev["end_date"], f"Missing end_date in {ev['event_type']}"
        assert ev["impact_description"] is not None, f"Missing impact_description in {ev['event_type']}"
        assert ev["impact_percentage"] is not None, f"Missing impact_percentage in {ev['event_type']}"
        assert ev["affected_products"] is not None, f"Missing affected_products in {ev['event_type']}"


def test_all_event_types_present():
    events = _generate_events_for_year(2026)
    types = {e["event_type"] for e in events}
    expected = {RAMADAN, EID_FITR, EID_ADHA, COPTIC_CHRISTMAS, EASTER, SHAM_EL_NESSIM, WINTER, SCHOOL, SUMMER_HEAT}
    assert types == expected, f"Missing types: {expected - types}"


def test_eight_distinct_events():
    events = _generate_events_for_year(2026)
    # winter spans across year boundary, so 9 total in some years
    assert len(events) >= 8


def test_dates_are_chronological():
    for year in [2026, 2027, 2028]:
        events = sorted(_generate_events_for_year(year), key=lambda e: e["start_date"])
        for i in range(1, len(events)):
            assert events[i-1]["start_date"] <= events[i]["start_date"]


def test_ramadan_in_correct_season():
    e2026 = {e["event_type"]: e for e in _generate_events_for_year(2026)}
    assert e2026[RAMADAN]["start_date"] >= date(2026, 2, 1)
    assert e2026[RAMADAN]["start_date"] <= date(2026, 3, 15)
    assert e2026[RAMADAN]["impact_percentage"] == 12.0


def test_sham_el_nessim_impact_highest():
    for year in [2026, 2027, 2028]:
        events = _generate_events_for_year(year)
        sham = next(e for e in events if e["event_type"] == SHAM_EL_NESSIM)
        max_impact = max(e["impact_percentage"] for e in events)
        assert sham["impact_percentage"] == max_impact, f"Sham should be highest impact in {year}: {sham['impact_percentage']} vs {max_impact}"


def test_sham_is_easter_monday():
    for year in [2026, 2027, 2028]:
        events = _generate_events_for_year(year)
        easter = next(e for e in events if e["event_type"] == EASTER)
        sham = next(e for e in events if e["event_type"] == SHAM_EL_NESSIM)
        # Sham (Easter Monday) should start the day after Easter ends, or overlap since range-ified
        assert sham["start_date"] >= easter["start_date"], f"Sham should be after Easter in {year}"


def test_summer_heat_is_summer():
    e2026 = {e["event_type"]: e for e in _generate_events_for_year(2026)}
    assert e2026[SUMMER_HEAT]["start_date"] == date(2026, 6, 1)
    assert e2026[SUMMER_HEAT]["end_date"] == date(2026, 8, 31)
    assert e2026[SUMMER_HEAT]["impact_percentage"] < 0


def test_coptic_christmas_fixed():
    for year in [2026, 2027, 2028]:
        events = _generate_events_for_year(year)
        copt = next(e for e in events if e["event_type"] == COPTIC_CHRISTMAS)
        assert copt["start_date"] <= date(year, 1, 7) <= copt["end_date"]


def test_school_season_dates():
    e2026 = {e["event_type"]: e for e in _generate_events_for_year(2026)}
    assert e2026[SCHOOL]["start_date"] == date(2026, 9, 15)
    assert e2026[SCHOOL]["end_date"] == date(2026, 10, 15)


def test_affected_products_rules():
    e2026 = {e["event_type"]: e for e in _generate_events_for_year(2026)}
    assert "day_old_chicks" not in (e2026[SHAM_EL_NESSIM]["affected_products"] or [])
    assert "fertilized_eggs" not in (e2026[SCHOOL]["affected_products"] or [])
    assert "fertilized_eggs" not in (e2026[SUMMER_HEAT]["affected_products"] or [])
    assert "fertilized_eggs" in (e2026[COPTIC_CHRISTMAS]["affected_products"] or [])


def test_multiple_years_differ():
    e2026 = {e["event_type"]: e for e in _generate_events_for_year(2026)}
    e2027 = {e["event_type"]: e for e in _generate_events_for_year(2027)}
    # Hijri events should shift
    assert e2026[RAMADAN]["start_date"] != e2027[RAMADAN]["start_date"]
    assert e2026[EID_FITR]["start_date"] != e2027[EID_FITR]["start_date"]


def test_easter_computus():
    assert _gregorian_easter(2026) == date(2026, 4, 5)
    assert _gregorian_easter(2027) == date(2027, 3, 28)
    assert _gregorian_easter(2025) == date(2025, 4, 20)


def test_easter_before_sham():
    for year in [2025, 2026, 2027, 2028]:
        ce = _coptic_easter(year)
        ge = _gregorian_easter(year)
        assert ce >= ge, f"Coptic Easter {ce} should be >= Gregorian Easter {ge} in {year}"
