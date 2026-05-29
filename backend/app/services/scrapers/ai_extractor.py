"""
AI-powered text extractor for messy/unstructured posts.
Uses OpenAI to extract structured price data from Arabic text.
Falls back gracefully if API key is not configured.
"""
import json
import logging
from typing import Optional
from datetime import date, datetime
from .price_normalizer import ExtractedPrice, normalizer
from .config import get_scraper_settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a poultry market price extractor for Egypt. 
Extract structured data from the given Arabic text. Return ONLY valid JSON:
{
  "product_type": "fertilized_eggs" | "day_old_chicks" | null,
  "category": "white" | "baladi" | "brown" | "sasso" | null,
  "price": number | null,
  "currency": "EGP",
  "unit": "per_1000" | "per_egg" | "per_kilo" | null,
  "region": string | null,
  "recorded_date": "YYYY-MM-DD" | null,
  "confidence": 0.0-1.0
}
If extraction is uncertain, set confidence < 0.5. Use null for unknown fields."""


class AIExtractor:
    def __init__(self):
        self.settings = get_scraper_settings()
        self.client = None
        self._init_client()

    def _init_client(self):
        if not self.settings.ai_extraction_enabled:
            return
        if not self.settings.openai_api_key:
            logger.warning("OPENAI_API_KEY not set — AI extraction disabled")
            return
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.settings.openai_api_key)
        except ImportError:
            logger.warning("openai package not installed — AI extraction disabled")

    def extract(self, text: str) -> Optional[ExtractedPrice]:
        structured = self._ai_extract(text)
        if structured and structured["confidence"] and structured["confidence"] >= 0.5:
            result = ExtractedPrice(
                product_type=structured.get("product_type"),
                category=structured.get("category"),
                price=structured.get("price"),
                currency=structured.get("currency", "EGP"),
                unit=structured.get("unit"),
                region=structured.get("region"),
                recorded_date=self._parse_date(structured.get("recorded_date")),
                confidence=structured.get("confidence", 0.0),
            )
            if result.is_valid():
                return result

        fallback = normalizer.normalize(text)
        if fallback.is_valid():
            return fallback
        return None

    def _ai_extract(self, text: str) -> Optional[dict]:
        if not self.client:
            return None
        try:
            response = self.client.chat.completions.create(
                model=self.settings.ai_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                temperature=0.1,
                max_tokens=300,
            )
            content = response.choices[0].message.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[-1]
                content = content.rsplit("\n", 1)[0]
                if content.endswith("```"):
                    content = content[:-3]
            return json.loads(content)
        except Exception as e:
            logger.error(f"AI extraction failed: {e}")
            return None

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> Optional[date]:
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return None


ai_extractor = AIExtractor()
