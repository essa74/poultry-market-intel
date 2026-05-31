import io
import logging
import shutil
from typing import Optional

from PIL import Image

logger = logging.getLogger(__name__)


def _tesseract_available() -> bool:
    return shutil.which("tesseract") is not None


def _arabic_lang_available() -> bool:
    try:
        import pytesseract
        langs = pytesseract.get_languages()
        return "ara" in langs
    except Exception:
        return False


def validate_image(image_bytes: bytes) -> tuple[bool, Optional[str]]:
    if not image_bytes:
        return False, "الملف فارغ"
    if len(image_bytes) < 100:
        return False, "الملف صغير جداً أو تالف"
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.verify()
        return True, None
    except Exception:
        return False, "تعذر التعرف على الصورة — تأكد من رفع ملف صورة صحيح (jpg/png/webp)"


async def ocr_image(image_bytes: bytes) -> tuple[bool, str, Optional[str]]:
    """
    Run OCR on image bytes, trying Arabic first, then falling back to any language.

    Returns (success, extracted_text, error_message).
    On success, error_message is None.
    On failure, extracted_text is empty and error_message describes the issue.
    """
    if not _tesseract_available():
        return False, "", "OCR غير متاح حالياً على السيرفر (tesseract not installed)"

    try:
        import pytesseract
    except ImportError:
        return False, "", "OCR غير متاح حالياً على السيرفر (pytesseract not installed)"

    valid, err = validate_image(image_bytes)
    if not valid:
        return False, "", err

    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as e:
        return False, "", f"تعذر فتح الصورة: {e}"

    try:
        if _arabic_lang_available():
            text = pytesseract.image_to_string(img, lang="ara", config="--psm 6")
        else:
            text = pytesseract.image_to_string(img, lang="ara+eng", config="--psm 6")
            if not text.strip():
                text = pytesseract.image_to_string(img, config="--psm 6")

        text = text.strip()
        if not text:
            return False, "", "لم يتم استخراج أي نص من الصورة"

        logger.info(f"OCR success: extracted {len(text)} chars")
        return True, text, None

    except Exception as e:
        logger.exception(f"OCR failed: {e}")
        return False, "", f"فشل التعرف على النص: {e}"
