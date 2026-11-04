import io

import fitz
import pytest

from modules.pdf_reader import PDFReadError, extract_pdf


def make_pdf(*texts):
    document = fitz.open()
    for text in texts:
        page = document.new_page()
        if text:
            page.insert_text((72, 72), text)
    raw = document.tobytes()
    document.close()
    return raw


def test_extracts_multiple_pages():
    result = extract_pdf(io.BytesIO(make_pdf("Name: A", "Passport No: B")), "test.pdf")
    assert len(result.pages) == 2
    assert "Name: A" in result.pages[0].text
    assert "Passport No: B" in result.pages[1].text


def test_detects_scanned_or_empty_text_pdf():
    result = extract_pdf(io.BytesIO(make_pdf("")), "scan.pdf")
    assert not result.has_text


def test_rejects_non_pdf():
    with pytest.raises(PDFReadError, match="PDF"):
        extract_pdf(io.BytesIO(b"not pdf"), "bad.txt")


def test_rejects_over_limit():
    with pytest.raises(PDFReadError, match="too large"):
        extract_pdf(io.BytesIO(make_pdf("text")), "large.pdf", max_bytes=5)


def test_rejects_empty_upload():
    with pytest.raises(PDFReadError, match="empty"):
        extract_pdf(io.BytesIO(b""), "empty.pdf")


def test_rejects_password_protected_pdf_without_password_prompt():
    document = fitz.open()
    document.new_page()
    raw = document.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="user")
    document.close()
    with pytest.raises(PDFReadError, match="password-protected"):
        extract_pdf(io.BytesIO(raw), "locked.pdf")


def test_reports_corrupt_pdf_clearly():
    with pytest.raises(PDFReadError, match="damaged or unreadable"):
        extract_pdf(io.BytesIO(b"%PDF-1.4\nnot really a pdf"), "corrupt.pdf")


def test_tracks_pages_without_selectable_text():
    result = extract_pdf(io.BytesIO(make_pdf("Selectable", "")), "mixed.pdf")
    assert result.has_text
    assert result.pages_without_text == (2,)


def test_rejects_invalid_size_limit():
    with pytest.raises(PDFReadError, match="positive"):
        extract_pdf(io.BytesIO(make_pdf("ok")), "valid.pdf", max_bytes=0)
