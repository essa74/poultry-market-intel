import logging
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import HolidayCalendar

logger = logging.getLogger(__name__)

# ── Event type constants ──────────────────────────────────────────────
RAMADAN = "ramadan"
EID_FITR = "eid_fitr"
EID_ADHA = "eid_adha"
COPTIC_CHRISTMAS = "coptic_christmas"
EASTER = "easter"
SHAM_EL_NESSIM = "sham_el_nessim"
WINTER = "winter"
SCHOOL = "school"
SUMMER_HEAT = "summer_heat"

# ── Product constants ─────────────────────────────────────────────────
EGGS = "fertilized_eggs"
CHICKS = "day_old_chicks"

# ── Known Hijri-to-Gregorian reference points ─────────────────────────
#   Each tuple: (hijri_year, gregorian_date_of_1_Ramadan)
#   Hijri year ~354 days, so Ramadan shifts ~11 days earlier each year.
_KNOWN_RAMADAN_STARTS = {
    1447: date(2026, 2, 18),
    1448: date(2027, 2, 7),
    1449: date(2028, 1, 27),
    1450: date(2029, 1, 16),
    1451: date(2030, 1, 5),
    1452: date(2030, 12, 26),
}


def _hijri_year_for(target: date) -> int:
    """Return the Hijri year whose Ramadan contains *target* (or the most recent past Ramadan)."""
    best = max((y for y, d in _KNOWN_RAMADAN_STARTS.items() if d <= target), default=None)
    if best is None:
        return max(_KNOWN_RAMADAN_STARTS)
    return best


def _ramadan_start(year: int) -> date:
    if year in _KNOWN_RAMADAN_STARTS:
        return _KNOWN_RAMADAN_STARTS[year]
    # approximate: ramadan 1447 = 2026-02-18, each hijri year ~354 days
    known_year = max(_KNOWN_RAMADAN_STARTS)
    shift = (year - known_year) * 354
    return _KNOWN_RAMADAN_STARTS[known_year] - timedelta(days=shift)


def _gregorian_easter(year: int) -> date:
    """Computus for Gregorian Easter (used by Western + Coptic date approximation)."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _coptic_easter(year: int) -> date:
    """Coptic Orthodox Easter — usually 1-5 weeks after Gregorian Easter."""
    # Simplified: add ~7 days to Gregorian Easter as approximation
    ge = _gregorian_easter(year)
    coptic_offset = {2025: 4, 2026: 0, 2027: 5, 2028: 2}.get(year, 7)
    return ge + timedelta(days=coptic_offset + 7)


def _generate_events_for_year(year: int) -> list[dict]:
    """Generate all seasonal events for a given Gregorian year."""
    events = []

    # ── Ramadan (Hijri, ~30 days) ──────────────────────────────────────
    hy = _hijri_year_for(date(year, 6, 1))
    ram_start = _ramadan_start(hy)
    if ram_start.year > year:
        hy2 = hy - 1
        ram_start = _ramadan_start(hy2)
    # If the computed start is still in the wrong year, try the next
    if ram_start.year < year - 1:
        ram_start = _ramadan_start(hy + 1)
    ram_end = ram_start + timedelta(days=29)

    events.append({
        "name_ar": "شهر رمضان",
        "name_en": "Ramadan",
        "event_type": RAMADAN,
        "start_date": ram_start,
        "end_date": ram_end,
        "impact_description": "ارتفاع",
        "impact_percentage": 12.0,
        "affected_products": [EGGS, CHICKS],
        "notes": "زيادة الطلب على البيض والدواجن قبل وأثناء الشهر بنسبة 15-20%",
    })

    # ── Eid Al-Fitr (Hijri, 3 days) ────────────────────────────────────
    eid_fitr_start = ram_end + timedelta(days=1)
    eid_fitr_end = eid_fitr_start + timedelta(days=2)
    events.append({
        "name_ar": "عيد الفطر",
        "name_en": "Eid Al-Fitr",
        "event_type": EID_FITR,
        "start_date": eid_fitr_start,
        "end_date": eid_fitr_end,
        "impact_description": "انخفاض",
        "impact_percentage": -5.0,
        "affected_products": [EGGS, CHICKS],
        "notes": "انخفاض الطلب بعد انتهاء رمضان وعودة الإنتاج إلى مستوياته الطبيعية",
    })

    # ── Eid Al-Adha (Hijri, Dhul Hijjah 10-13, ~70 days after Fitr) ──
    eid_adha_start = eid_fitr_start + timedelta(days=70)
    eid_adha_end = eid_adha_start + timedelta(days=3)
    events.append({
        "name_ar": "عيد الأضحى",
        "name_en": "Eid Al-Adha",
        "event_type": EID_ADHA,
        "start_date": eid_adha_start,
        "end_date": eid_adha_end,
        "impact_description": "ارتفاع",
        "impact_percentage": 8.0,
        "affected_products": [EGGS, CHICKS],
        "notes": "زيادة الطلب على الدواجن والبيض مع ارتفاع الأسعار بنسبة 8-10%",
    })

    # ── Coptic Christmas (Jan 7, fixed) ────────────────────────────────
    copt_xmas = date(year, 1, 7)
    events.append({
        "name_ar": "عيد الميلاد المجيد",
        "name_en": "Coptic Christmas",
        "event_type": COPTIC_CHRISTMAS,
        "start_date": copt_xmas - timedelta(days=1),
        "end_date": copt_xmas + timedelta(days=1),
        "impact_description": "ارتفاع",
        "impact_percentage": 6.0,
        "affected_products": [EGGS],
        "notes": "زيادة استهلاك البيض في صناعة الحلويات والمخبوزات",
    })

    # ── Easter (Coptic Orthodox, variable) ─────────────────────────────
    easter = _coptic_easter(year)
    events.append({
        "name_ar": "عيد القيامة المجيد",
        "name_en": "Easter",
        "event_type": EASTER,
        "start_date": easter - timedelta(days=2),
        "end_date": easter + timedelta(days=1),
        "impact_description": "انخفاض",
        "impact_percentage": -3.0,
        "affected_products": [EGGS],
        "notes": "فترة أسبوع الآلام تشهد انخفاضاً طفيفاً في الطلب",
    })

    # ── Sham El-Nessim (Easter Monday) ────────────────────────────────
    sham = easter + timedelta(days=1)
    events.append({
        "name_ar": "شم النسيم",
        "name_en": "Sham El-Nessim",
        "event_type": SHAM_EL_NESSIM,
        "start_date": sham - timedelta(days=1),
        "end_date": sham + timedelta(days=1),
        "impact_description": "ارتفاع حاد",
        "impact_percentage": 18.0,
        "affected_products": [EGGS],
        "notes": "أعلى تأثير موسمي — يزداد استهلاك البيض بنسبة 18-20% مع ذروة سعرية قبل أسبوع من العيد",
    })

    # ── Winter (Dec 21 – Mar 20) ─────────────────────────────────────
    # Split across year boundary: Dec 21 – Dec 31 + Jan 1 – Mar 20
    winter_start = date(year, 12, 21)
    winter_end = date(year + 1, 3, 20)
    if winter_start <= date(year + 1, 1, 1):
        events.append({
            "name_ar": "فصل الشتاء",
            "name_en": "Winter Season",
            "event_type": WINTER,
            "start_date": winter_start,
            "end_date": date(year + 1, 3, 20),
            "impact_description": "ارتفاع",
            "impact_percentage": 10.0,
            "affected_products": [EGGS, CHICKS],
            "notes": "ارتفاع الطلب بنسبة 8-12% بسبب زيادة استهلاك البيض في الأجواء الباردة",
        })

    # ── School Season (mid-Sep to mid-Oct) ───────────────────────────
    school_start = date(year, 9, 15)
    school_end = date(year, 10, 15)
    events.append({
        "name_ar": "موسم المدارس",
        "name_en": "School Season",
        "event_type": SCHOOL,
        "start_date": school_start,
        "end_date": school_end,
        "impact_description": "انخفاض",
        "impact_percentage": -4.0,
        "affected_products": [CHICKS],
        "notes": "انخفاض الطلب على الكتاكيت مع انشغال الأسر بالمصاريف الدراسية",
    })

    # ── Summer Heat (Jun – Aug) ───────────────────────────────────────
    summer_start = date(year, 6, 1)
    summer_end = date(year, 8, 31)
    events.append({
        "name_ar": "موجة الحر الصيفي",
        "name_en": "Summer Heat Season",
        "event_type": SUMMER_HEAT,
        "start_date": summer_start,
        "end_date": summer_end,
        "impact_description": "انخفاض",
        "impact_percentage": -8.0,
        "affected_products": [CHICKS],
        "notes": "انخفاض الإنتاج وارتفاع النفوق بسبب الحرارة — يقل المعروض من الكتاكيت",
    })

    return events


async def get_holidays(
    db: AsyncSession,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    event_type: Optional[str] = None,
    limit: int = 100,
) -> list[HolidayCalendar]:
    stmt = select(HolidayCalendar)
    if from_date:
        stmt = stmt.where(HolidayCalendar.end_date >= from_date)
    if to_date:
        stmt = stmt.where(HolidayCalendar.start_date <= to_date)
    if event_type:
        stmt = stmt.where(HolidayCalendar.event_type == event_type)
    stmt = stmt.order_by(HolidayCalendar.start_date).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_upcoming_events(db: AsyncSession, days: int = 60) -> list[HolidayCalendar]:
    today = date.today()
    horizon = today + timedelta(days=days)
    stmt = (
        select(HolidayCalendar)
        .where(
            and_(
                HolidayCalendar.start_date >= today,
                HolidayCalendar.start_date <= horizon,
            )
        )
        .order_by(HolidayCalendar.start_date)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_active_events(db: AsyncSession) -> list[HolidayCalendar]:
    """Return events that are active *right now* (start <= today <= end)."""
    today = date.today()
    stmt = (
        select(HolidayCalendar)
        .where(
            and_(
                HolidayCalendar.start_date <= today,
                HolidayCalendar.end_date >= today,
            )
        )
        .order_by(HolidayCalendar.end_date)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def seed_holidays(db: AsyncSession, years: list[int] | None = None) -> int:
    """Generate and upsert holiday events for given years (default: current + 2)."""
    from sqlalchemy import delete

    if years is None:
        today = date.today()
        years = [today.year, today.year + 1, today.year + 2]

    total = 0
    for year in years:
        events = _generate_events_for_year(year)
        for ev in events:
            # upsert: delete any existing event with same type + start_date
            await db.execute(
                delete(HolidayCalendar).where(
                    HolidayCalendar.event_type == ev["event_type"],
                    HolidayCalendar.start_date == ev["start_date"],
                )
            )
            db.add(HolidayCalendar(**ev))
            total += 1

    await db.commit()
    logger.info("Seeded %d holiday events for years %s", total, years)
    return total


async def get_event_impact(
    db: AsyncSession,
    product_type: str,
    target_date: Optional[date] = None,
) -> float:
    """Return cumulative impact percentage for a product on a given date."""
    if target_date is None:
        target_date = date.today()

    stmt = (
        select(HolidayCalendar)
        .where(
            and_(
                HolidayCalendar.start_date <= target_date,
                HolidayCalendar.end_date >= target_date,
                HolidayCalendar.affected_products.isnot(None),
            )
        )
    )
    result = await db.execute(stmt)
    total_impact = 0.0
    for ev in result.scalars().all():
        products = ev.affected_products or []
        if product_type in products and ev.impact_percentage is not None:
            total_impact += ev.impact_percentage
    return total_impact


async def get_all_event_types(db: AsyncSession) -> list[str]:
    stmt = select(HolidayCalendar.event_type).distinct().order_by(HolidayCalendar.event_type)
    result = await db.execute(stmt)
    return list(result.scalars().all())
