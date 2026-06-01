import io
import logging
import shutil
from typing import Optional

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

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


def preprocess_image(img: Image.Image, scale: int = 2) -> Image.Image:
    """Preprocess image for better OCR: grayscale → contrast → sharpen → threshold → upscale."""
    img = img.convert("L")

    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)

    img = img.filter(ImageFilter.SHARPEN)
    img = img.filter(ImageFilter.SHARPEN)

    img = img.point(lambda p: 255 if p > 140 else 0)

    w, h = img.size
    img = img.resize((w * scale, h * scale), Image.LANCZOS)

    return img


def ocr_full_arabic(img: Image.Image) -> str:
    import pytesseract
    if _arabic_lang_available():
        return pytesseract.image_to_string(img, lang="ara", config="--psm 6 --oem 3")
    text = pytesseract.image_to_string(img, lang="ara+eng", config="--psm 6 --oem 3")
    if not text.strip():
        text = pytesseract.image_to_string(img, config="--psm 6 --oem 3")
    return text.strip()


def ocr_numeric(img: Image.Image) -> str:
    """Numeric-focused OCR pass with digit whitelist to better capture prices."""
    import pytesseract
    config = "--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789٠١٢٣٤٥٦٧٨٩.,٫/ج"
    if _arabic_lang_available():
        return pytesseract.image_to_string(img, lang="ara", config=config).strip()
    return pytesseract.image_to_string(img, lang="ara+eng", config=config).strip()


def _normalize_arabic_digits(text: str) -> str:
    """Normalize all Arabic/Eastern digit forms to ASCII."""
    mapping = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
    return text.translate(mapping).replace("٫", ".").replace(",", ".")


def merge_ocr_results(full_text: str, numeric_text: str) -> str:
    """Merge full Arabic OCR with numeric-pass OCR, preferring numeric where available."""
    if not numeric_text.strip():
        return full_text
    if not full_text.strip():
        return numeric_text

    full_lines = full_text.split("\n")
    num_lines = numeric_text.split("\n")

    merged = []
    max_len = max(len(full_lines), len(num_lines))
    for i in range(max_len):
        f_line = full_lines[i] if i < len(full_lines) else ""
        n_line = num_lines[i] if i < len(num_lines) else ""

        f_norm = _normalize_arabic_digits(f_line)
        n_clean = n_line.strip()

        if n_clean and not f_norm.strip():
            merged.append(n_clean)
        elif f_norm.strip():
            merged.append(f_norm)
        else:
            merged.append(f_line)

    return "\n".join(merged).strip()


async def ocr_image(image_bytes: bytes) -> tuple[bool, str, Optional[str]]:
    """Run OCR with preprocessing and multi-pass (full Arabic + numeric focused).

    Returns (success, merged_text, error_message).
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
        preprocessed = preprocess_image(img, scale=2)

        full_text = ocr_full_arabic(preprocessed)
        numeric_text = ocr_numeric(preprocessed)

        merged = merge_ocr_results(full_text, numeric_text)

        if not merged:
            preprocessed_3x = preprocess_image(img, scale=3)
            merged = ocr_full_arabic(preprocessed_3x)
            merged = merged.strip()

        if not merged:
            return False, "", "لم يتم استخراج أي نص من الصورة"

        logger.info(f"OCR success: extracted {len(merged)} chars (full={len(full_text)}, numeric={len(numeric_text)})")
        return True, merged, None

    except Exception as e:
        logger.exception(f"OCR failed: {e}")
        return False, "", f"فشل التعرف على النص: {e}"
