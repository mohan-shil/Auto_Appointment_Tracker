"""Local PDF validation and page-by-page text extraction."""

from dataclasses import dataclass
from typing import BinaryIO, Optional

import fitz


MAX_PDF_BYTES = 15 * 1024 * 1024


class PDFReadError(ValueError):
    """Raised when a PDF cannot be safely read."""


@dataclass(frozen=True)
class PDFPage:
    page_number: int
    text: str
    ocr_text: Optional[str] = None
    ocr_confidence: Optional[float] = None

    @property
    def text_for_review(self) -> str:
        """Keep native text authoritative; OCR fills only pages without native text."""
        return self.text if self.text.strip() else (self.ocr_text or "")

    @property
    def extraction_method(self) -> str:
        if self.text.strip():
            return "Selectable text"
        if self.ocr_text and self.ocr_text.strip():
            return "OCR (local Tesseract)"
        return "Not detected"


@dataclass(frozen=True)
class PDFExtraction:
    pages: tuple[PDFPage, ...]

    @property
    def full_text(self) -> str:
        return "\n\n".join(page.text for page in self.pages)

    @property
    def has_text(self) -> bool:
        return bool(self.full_text.strip())

    @property
    def has_review_text(self) -> bool:
        """Return true for either native text or separately retained OCR text."""
        return any(page.text_for_review.strip() for page in self.pages)

    @property
    def pages_without_text(self) -> tuple[int, ...]:
        """Page numbers that have no selectable text (often scanned pages)."""
        return tuple(page.page_number for page in self.pages if not page.text.strip())


def extract_pdf(upload: BinaryIO, filename: str, max_bytes: int = MAX_PDF_BYTES) -> PDFExtraction:
    """Extract selectable text without writing the uploaded document to disk."""
    if not filename.lower().endswith(".pdf"):
        raise PDFReadError("Please upload a PDF file.")
    if max_bytes <= 0:
        raise PDFReadError("The PDF size limit must be a positive number.")
    try:
        raw = upload.read(max_bytes + 1)
    except Exception as exc:
        raise PDFReadError("The uploaded file could not be read. Please choose the PDF again.") from exc
    if not raw:
        raise PDFReadError("The uploaded PDF is empty (0 bytes). Please choose a non-empty PDF.")
    if len(raw) > max_bytes:
        raise PDFReadError(f"The PDF is too large. Maximum size is {max_bytes // (1024 * 1024)} MB.")
    # The PDF specification permits a short binary marker before its header.
    if b"%PDF-" not in raw[:1024]:
        raise PDFReadError("This file does not appear to be a valid PDF.")
    try:
        with fitz.open(stream=raw, filetype="pdf") as document:
            if document.is_encrypted:
                raise PDFReadError("This PDF is password-protected. Unlock it yourself and upload the permitted readable copy; this app will not request or store its password.")
            if document.page_count == 0:
                raise PDFReadError("The PDF has no pages. Please choose a complete application PDF.")
            if document.page_count > 300:
                raise PDFReadError("The PDF has more than 300 pages. Split it into smaller documents before upload.")
            pages = tuple(PDFPage(index + 1, page.get_text("text", sort=True).strip()) for index, page in enumerate(document))
    except PDFReadError:
        raise
    except Exception as exc:
        raise PDFReadError("The PDF is damaged or unreadable. Please export or download the original Webfile again.") from exc
    if not pages:
        raise PDFReadError("The PDF contains no pages.")
    return PDFExtraction(pages)
