import logging
import shutil
import tempfile
from pathlib import Path
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

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name
        try:
            img = Image.open(tmp)
            img.save(tmp_path)
        except Exception:
            pass

    try:
        img = Image.open(tmp_path)

        if _arabic_lang_available():
            text = pytesseract.image_to_string(img, lang="ara", config="--psm 6")
        else:
            text = pytesseract.image_to_string(img, lang="ara+eng", config="--psm 6")
            if not text.strip():
                text = pytesseract.image_to_string(img, config="--psm 6")

        text = text.strip()
        if not text:
            return False, "", "لم يتم استخراج أي نص من الصورة"

        return True, text, None

    except Exception as e:
        logger.exception(f"OCR failed: {e}")
        return False, "", f"فشل التعرف على النص: {e}"

    finally:
        Path(tmp_path).unlink(missing_ok=True)
