import re
from datetime import date, datetime
from typing import Optional

POULTRY_TERMS = [
    "كتكوت", "كتاكيت", "بيض مخصب", "بيض", "دواجن", "عمر يوم",
    "ساسو", "كتكوت ساسو", "كتاكيت ساسو",
    "فرخة", "فراخ", "دجاج", "أمهات", "أمهات بياض",
    "poultry", "chick", "broiler",
]

MONEY_PATTERN = re.compile(r"\d+\s*(?:\S+\s+)*(جنيه|ج\.م|جم|EGP|le)", re.IGNORECASE)

CURRENCY_WORDS = re.compile(r"(جنيه|ج\.م|جم|EGP|le)", re.IGNORECASE)

LARGE_MULTIPLIERS = re.compile(r"(مليون|ملايين|مليار|مليارات|آلاف|ألف)", re.IGNORECASE)


def is_poultry_relevant(text: str) -> bool:
    if CURRENCY_WORDS.search(text):
        for term in POULTRY_TERMS:
            if term in text:
                return True
        return False
    return True


def contains_large_money(text: str) -> bool:
    return bool(CURRENCY_WORDS.search(text) and LARGE_MULTIPLIERS.search(text))


TABLE_EGG_PHRASES = [
    "بيض مائدة", "بيض ابيض بطاريات", "بيض أبيض بطاريات",
    "بيض احمر", "بيض أحمر", "كراتين بيض", "كرتونة بيض",
    "طبق بيض", "egg tray", "table eggs",
    "بيض بلدى مائدة", "بيض بلدي مائدة",
]

FERTILIZED_EGG_PHRASES = [
    "بيض مخصب", "بيض تفريخ", "بيض أمهات", "بيض امهات",
    "بيض تسمين", "بيض ساسو مخصب",
    "hatching eggs", "fertile eggs",
]

FERTILIZED_EGG_PATTERNS = [
    re.compile(r"(?:\s|^)" + re.escape(p) + r"(?:\s|$)", re.IGNORECASE)
    for p in FERTILIZED_EGG_PHRASES
]

BREED_KEYWORDS = {
    "white": ["أبيض", "ابيض", "white", "hybrid", "هايبرد"],
    "baladi": ["بلدي", "baladi", "بلدى", "محلي"],
    "brown": ["بني", "brown", "براون", "أحمر", "احمر"],
    "sasso": ["ساسو", "sasso"],
    "turkey": ["رومى", "رومي"],
    "duck": ["بط"],
}

PRODUCT_GROUP_RULES = [
    ("fertilized_eggs", FERTILIZED_EGG_PHRASES),
    ("chicks", ["كتكوت", "كتاكيت", "ساسو"]),
    ("ducks", ["بط", "بطة"]),
    ("feed", ["علف", "أعلاف", "Feed", "feed"]),
]

GOVERNORATE_KEYWORDS = [
    "القاهرة", "الإسكندرية", "الجيزة", "الدقهلية", "الشرقية",
    "البحيرة", "الغربية", "القليوبية", "المنوفية", "كفر الشيخ",
    "دمياط", "بورسعيد", "الإسماعيلية", "السويس", "المنيا",
    "أسيوط", "سوهاج", "قنا", "الأقصر", "أسوان", "الفيوم",
    "بني سويف", "مطروح",
]

UNIT_KEYWORDS = {
    "per_1000": ["للـ 1000", "لل 1000", "للألف", "per 1000", "/1000", "للاف", "للألف"],
    "per_egg": ["للبيضة", "للبيضه", "للحبة", "per egg", "للبيض"],
    "per_kilo": ["للكيلو", "لل kilo", "per kg", "كجم", "للكيلوجرام"],
}

PRICE_PATTERNS = [
    re.compile(r"(\d+[\.,]?\d*)\s*(جنيه|ج\.م|جم|EGP|le|ج\.م\.)", re.IGNORECASE),
    re.compile(r"(\d+[\.,]?\d*)\s*(قرش)", re.IGNORECASE),
    re.compile(r"سعر\s*(?:ال|الـ|)\s*(\d+[\.,]?\d*)", re.IGNORECASE),
    re.compile(r"(\d+[\.,]?\d*)\s*(?:ج|جنيه)", re.IGNORECASE),
    re.compile(r"(\d+[\.,]?\d*)\s*جنية\b", re.IGNORECASE),
    re.compile(r"(\d{2,3})\s*(?:جنيه|جنية|ج\.)", re.IGNORECASE),
    re.compile(r"بسعر\s*(\d+[\.,]?\d*)", re.IGNORECASE),
    re.compile(r"(\d+[\.,]?\d*)\s*جنيه\s*لل", re.IGNORECASE),
    re.compile(r"(\d{2,}(?:[\.,]\d{1,2})?)\s*$", re.IGNORECASE),
]

DATE_PATTERNS = [
    re.compile(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})"),
    re.compile(r"(\d{4})-(\d{2})-(\d{2})"),
    re.compile(r"(\d{1,2})\s*(يناير|فبراير|مارس|أبريل|مايو|يونيو|يوليو|أغسطس|سبتمبر|أكتوبر|نوفمبر|ديسمبر)\s*(\d{4})"),
    re.compile(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})"),
    re.compile(r"(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{2,4})"),
]

MONTH_MAP = {
    "يناير": 1, "فبراير": 2, "مارس": 3, "أبريل": 4,
    "مايو": 5, "يونيو": 6, "يوليو": 7, "أغسطس": 8,
    "سبتمبر": 9, "أكتوبر": 10, "نوفمبر": 11, "ديسمبر": 12,
}


class ExtractedPrice:
    def __init__(
        self,
        product_type: Optional[str] = None,
        category: Optional[str] = None,
        price: Optional[float] = None,
        currency: str = "EGP",
        unit: Optional[str] = None,
        region: Optional[str] = None,
        recorded_date: Optional[date] = None,
        confidence: float = 0.0,
        raw_product_name: Optional[str] = None,
        product_group: Optional[str] = None,
        matched_price_str: Optional[str] = None,
    ):
        self.product_type = product_type
        self.category = category
        self.price = price
        self.currency = currency
        self.unit = unit
        self.region = region
        self.recorded_date = recorded_date
        self.confidence = confidence
        self.raw_product_name = raw_product_name
        self.product_group = product_group
        self.matched_price_str = matched_price_str

    def is_valid(self) -> bool:
        return bool(self.product_type and self.price and self.price > 0 and self.recorded_date)

    def to_dict(self) -> dict:
        return {
            "product_type": self.product_type,
            "category": self.category,
            "price": self.price,
            "currency": self.currency,
            "unit": self.unit,
            "region": self.region,
            "recorded_date": self.recorded_date.isoformat() if self.recorded_date else None,
            "confidence": self.confidence,
            "raw_product_name": self.raw_product_name,
            "product_group": self.product_group,
        }


class PriceNormalizer:
    def normalize(self, text: str) -> ExtractedPrice:
        result = ExtractedPrice()
        result.raw_product_name = text.strip()
        result.product_group = self._extract_product_group(text)
        result.product_type = self._extract_product_type(text, result.product_group)
        result.category = self._extract_breed(text)
        result.price, result.matched_price_str = self._extract_price(text)
        result.region = self._extract_governorate(text)
        result.recorded_date = self._extract_date(text)
        result.unit = self._extract_unit(text, result.product_group)
        result.confidence = self._calculate_confidence(text, result)
        return result

    def _is_table_egg(self, text: str) -> bool:
        for phrase in TABLE_EGG_PHRASES:
            if phrase in text:
                return True
        return False

    def _extract_product_group(self, text: str) -> Optional[str]:
        if self._is_table_egg(text):
            return None
        for pattern in FERTILIZED_EGG_PATTERNS:
            if pattern.search(text):
                return "fertilized_eggs"
        for group, keywords in PRODUCT_GROUP_RULES:
            if group == "fertilized_eggs":
                continue
            for kw in keywords:
                if isinstance(kw, re.Pattern):
                    if kw.search(text):
                        return group
                elif kw in text:
                    return group
        return "other"

    def _extract_product_type(self, text: str, product_group: Optional[str]) -> Optional[str]:
        mapping = {
            "fertilized_eggs": "fertilized_eggs",
            "chicks": "day_old_chicks",
            "ducks": "ducks",
            "feed": "feed",
            "other": "other",
        }
        return mapping.get(product_group) if product_group else None

    def _extract_breed(self, text: str) -> Optional[str]:
        for breed, keywords in BREED_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    return breed
        return None

    _CONTEXT_WINDOW = 30

    def _extract_price(self, text: str) -> tuple[Optional[float], Optional[str]]:
        for pattern in PRICE_PATTERNS:
            match = pattern.search(text)
            if match:
                try:
                    raw = match.group(1)
                    val = float(raw.replace(",", "."))
                    if match.group(0).endswith("قرش"):
                        val /= 100
                    start = max(0, match.start() - self._CONTEXT_WINDOW)
                    end = min(len(text), match.end() + self._CONTEXT_WINDOW)
                    context = text[start:end]
                    if LARGE_MULTIPLIERS.search(context):
                        continue
                    if not 0.1 < val < 200_000:
                        continue
                    return val, raw
                except ValueError:
                    continue
        return None, None

    def _extract_governorate(self, text: str) -> Optional[str]:
        for gov in GOVERNORATE_KEYWORDS:
            if gov in text:
                return gov
        return None

    def _extract_unit(self, text: str, product_group: Optional[str]) -> Optional[str]:
        if "كراتين" in text or "كرتونة" in text:
            return "per_carton"
        if product_group == "fertilized_eggs":
            return "per_tray"
        if product_group in ("chicks", "ducks"):
            return "per_unit"
        if product_group == "feed":
            return "per_kilo"
        for unit, keywords in UNIT_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    return unit
        return None

    def _extract_date(self, text: str) -> Optional[date]:
        today = date.today()
        for pattern in DATE_PATTERNS:
            match = pattern.search(text)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 3:
                        if groups[1] in MONTH_MAP:
                            day = int(groups[0])
                            month = MONTH_MAP[groups[1]]
                            year = int(groups[2])
                            return date(year, month, day)
                        else:
                            a, b, c = int(groups[0]), int(groups[1]), int(groups[2])
                            if c > 100:
                                return date(c, b, a) if a <= 31 else date(c, a, b)
                            else:
                                year = 2000 + c if c < 100 else c
                                return date(year, b, a) if a <= 31 else date(year, a, b)
                except (ValueError, IndexError):
                    continue
        return today

    def _calculate_confidence(self, text: str, result: ExtractedPrice) -> float:
        score = 0.0

        if result.product_group and result.product_group != "other":
            score += 0.15

        if result.product_type:
            score += 0.15

        if result.category:
            score += 0.15

        if result.price:
            score += 0.35
            if 5 < result.price < 200:
                score += 0.05
            elif 1 < result.price < 500:
                score += 0.02

        if result.region:
            score += 0.10

        if result.unit:
            score += 0.05

        if result.recorded_date:
            score += 0.10
            if result.recorded_date == date.today():
                score += 0.02

        return min(score, 1.0)


normalizer = PriceNormalizer()
