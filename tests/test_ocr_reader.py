import io

import fitz
from PIL import Image, ImageDraw
import pytest

from modules.data_validator import extract_fields
from modules.ocr_reader import OCRUnavailable, get_ocr_languages, get_ocr_status, run_local_ocr
from modules.pdf_reader import PDFExtraction, PDFPage, extract_pdf


def make_scanned_pdf():
    image = Image.new("RGB", (900, 350), "white")
    draw = ImageDraw.Draw(image)
    draw.text((30, 30), "Passport No: ZZ123456", fill="black")
    draw.text((30, 90), "Applicant Name: Synthetic Person", fill="black")
    png = io.BytesIO()
    image.save(png, format="PNG")
    document = fitz.open()
    page = document.new_page(width=450, height=175)
    page.insert_image(page.rect, stream=png.getvalue())
    raw = document.tobytes()
    document.close()
    return raw


def make_mixed_pdf():
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Nationality: Exampleland")
    scanned = fitz.open(stream=make_scanned_pdf(), filetype="pdf")
    document.insert_pdf(scanned)
    raw = document.tobytes()
    scanned.close()
    document.close()
    return raw


class FakeTesseract:
    class Output:
        DICT = "dict"

    def __init__(self, confidence):
        self.confidence = confidence

    def get_tesseract_version(self):
        return "synthetic-test"

    def get_languages(self, config=""):
        return ["eng", "ben", "osd"]

    def image_to_data(self, image, **kwargs):
        words = ["Passport", "No:", "ZZ123456"]
        return {
            "text": words,
            "conf": [str(self.confidence)] * len(words),
            "block_num": [1, 1, 1],
            "par_num": [1, 1, 1],
            "line_num": [1, 1, 1],
        }


def test_detects_synthetic_image_only_scanned_page():
    result = extract_pdf(io.BytesIO(make_scanned_pdf()), "synthetic-scan.pdf")
    assert not result.has_text
    assert result.pages_without_text == (1,)


def test_ocr_missing_is_detected_without_installing_dependencies(monkeypatch):
    def missing_engine():
        raise ImportError("not installed")

    monkeypatch.setattr("modules.ocr_reader._load_engine", missing_engine)
    ready, message = get_ocr_status()
    assert not ready
    assert "brew install tesseract" in message
    extraction = PDFExtraction((PDFPage(1, ""),))
    with pytest.raises(OCRUnavailable):
        run_local_ocr(io.BytesIO(b""), extraction)


def test_local_language_models_are_configurable(monkeypatch):
    from modules import ocr_reader

    monkeypatch.setattr(ocr_reader, "_load_engine", lambda: FakeTesseract(90))
    assert get_ocr_languages() == ("eng", "ben")


def test_ocr_fills_only_scanned_page_and_preserves_native_source(monkeypatch):
    from modules import ocr_reader

    fake = FakeTesseract(92)
    monkeypatch.setattr(ocr_reader, "_load_engine", lambda: fake)
    upload = io.BytesIO(make_mixed_pdf())
    extraction = extract_pdf(io.BytesIO(upload.getvalue()), "mixed.pdf")
    assert extraction.pages[0].text == "Nationality: Exampleland"
    assert extraction.pages[1].text == ""

    enhanced = run_local_ocr(upload, extraction)
    assert enhanced.pages[0].text == "Nationality: Exampleland"
    assert enhanced.pages[0].ocr_text is None
    assert enhanced.pages[1].text == ""
    assert enhanced.pages[1].ocr_text == "Passport No: ZZ123456"
    assert enhanced.pages[1].ocr_confidence == 92
    passport = next(field for field in extract_fields(enhanced) if field.key == "passport_number")
    assert passport.value == "ZZ123456"
    assert passport.source_page == 2
    assert passport.extraction_method == "OCR (local Tesseract)"
    assert passport.confidence == "Medium"


def test_low_quality_ocr_is_labeled_low_confidence(monkeypatch):
    from modules import ocr_reader

    monkeypatch.setattr(ocr_reader, "_load_engine", lambda: FakeTesseract(22))
    extraction = extract_pdf(io.BytesIO(make_scanned_pdf()), "scanned.pdf")
    result = run_local_ocr(io.BytesIO(make_scanned_pdf()), extraction)
    passport = next(field for field in extract_fields(result) if field.key == "passport_number")
    assert passport.value == "ZZ123456"
    assert passport.confidence == "Low"
