"""Optional local OCR for PDF pages with no selectable text."""

from dataclasses import replace
import math
from typing import Dict, Optional, Tuple

import fitz

from modules.pdf_reader import MAX_PDF_BYTES, PDFExtraction

MAX_OCR_PAGES = 50
MAX_RENDER_PIXELS = 12_000_000
OCR_TIMEOUT_SECONDS = 15


class OCRUnavailable(RuntimeError):
    """Raised when pytesseract or the local Tesseract executable is missing."""


class OCRProcessingError(RuntimeError):
    """Raised when local OCR cannot process the PDF safely."""


def _load_engine():
    """Import pytesseract only when OCR is requested."""
    import pytesseract

    return pytesseract


def get_ocr_status() -> Tuple[bool, str]:
    """Check both the Python wrapper and local Tesseract executable."""
    try:
        engine = _load_engine()
    except ImportError:
        return False, (
            "Optional OCR is not installed. In your activated project environment, run "
            "`python -m pip install -r requirements-ocr.txt`, then install Tesseract with "
            "`brew install tesseract`. Restart Streamlit afterward."
        )
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        return False, "Pillow is missing. Install optional OCR dependencies with `python -m pip install -r requirements-ocr.txt`."
    try:
        version = engine.get_tesseract_version()
    except Exception:
        return False, (
            "The pytesseract Python package is installed, but the local Tesseract executable "
            "is not available. On macOS, run `brew install tesseract`, then restart Streamlit."
        )
    return True, f"Local Tesseract OCR is ready (version {version})."


def get_ocr_languages() -> Tuple[str, ...]:
    """Return trained language models installed with the local Tesseract binary."""
    try:
        engine = _load_engine()
        languages = engine.get_languages(config="")
    except Exception:
        return ()
    return tuple(language for language in languages if language != "osd")


def apply_ocr_results(extraction: PDFExtraction, results: Dict[int, Tuple[str, Optional[float]]]) -> PDFExtraction:
    """Return a new extraction with OCR stored separately from original PDF text."""
    pages = tuple(
        replace(page, ocr_text=results[page.page_number][0], ocr_confidence=results[page.page_number][1])
        if page.page_number in results and not page.text.strip()
        else page
        for page in extraction.pages
    )
    return PDFExtraction(pages)


def run_local_ocr(upload, extraction: PDFExtraction, language: str = "eng") -> PDFExtraction:
    """OCR only blank-text pages; never alter or replace native PDF text."""
    ready, status_message = get_ocr_status()
    if not ready:
        raise OCRUnavailable(status_message)
    missing = extraction.pages_without_text
    if not missing:
        return extraction
    if len(missing) > MAX_OCR_PAGES:
        raise OCRProcessingError(f"OCR is limited to {MAX_OCR_PAGES} blank-text pages per run. Split the document and try again.")

    try:
        upload.seek(0)
        raw = upload.read(MAX_PDF_BYTES + 1)
        if len(raw) > MAX_PDF_BYTES:
            raise OCRProcessingError("The PDF is over the 15 MB limit and cannot be processed for OCR.")
        with fitz.open(stream=raw, filetype="pdf") as document:
            results = {}
            engine = _load_engine()
            from PIL import Image

            for page_number in missing:
                page = document.load_page(page_number - 1)
                width = max(float(page.rect.width), 1.0)
                height = max(float(page.rect.height), 1.0)
                requested_scale = 180 / 72
                bounded_scale = math.sqrt(MAX_RENDER_PIXELS / (width * height))
                scale = min(requested_scale, bounded_scale)
                pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
                data = engine.image_to_data(
                    image,
                    lang=language,
                    output_type=engine.Output.DICT,
                    timeout=OCR_TIMEOUT_SECONDS,
                )
                lines = {}
                confidences = []
                for index, raw_word in enumerate(data.get("text", [])):
                    word = str(raw_word).strip()
                    if not word:
                        continue
                    try:
                        confidence = float(data.get("conf", [])[index])
                    except (ValueError, IndexError, TypeError):
                        confidence = -1
                    if confidence >= 0:
                        confidences.append(confidence)
                    line_key = tuple(data.get(name, [0] * len(data.get("text", [])))[index] for name in ("block_num", "par_num", "line_num"))
                    lines.setdefault(line_key, []).append(word)
                text = "\n".join(" ".join(words) for words in lines.values()).strip()
                mean_confidence = sum(confidences) / len(confidences) if confidences else None
                results[page_number] = (text, mean_confidence)
        return apply_ocr_results(extraction, results)
    except OCRProcessingError:
        raise
    except Exception as exc:
        raise OCRProcessingError("Local OCR could not process this page. Check the PDF and local Tesseract language data, then try again.") from exc
