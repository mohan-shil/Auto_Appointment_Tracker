from datetime import date
import io

import fitz

from config.readiness import MAX_APPLICANTS, webfile_age_status
from models.applicant import ApplicantWebfile, IVACAccountProfile, ManualConfirmations
from modules.data_validator import extract_fields, is_fully_verified, validate_account_profile, validate_applicant, validate_field_value
from modules.pdf_reader import PDFExtraction, PDFPage, extract_pdf


def test_extracts_label_and_source_page():
    fields = extract_fields(PDFExtraction((PDFPage(1, "Applicant Name: Example Person\nPassport No: AB123"),)))
    name = next(field for field in fields if field.key == "full_name")
    assert name.value == "Example Person"
    assert name.source_page == 1
    assert name.status == "Needs review"
    assert name.extraction_method == "Selectable text"
    assert name.confidence == "High"
    assert name.verification_status == "Needs verification"
    assert name.source_references[0].source_text == "Applicant Name: Example Person"


def test_ambiguous_duplicate_requires_review():
    fields = extract_fields(PDFExtraction((PDFPage(1, "Applicant Name: First"), PDFPage(2, "Applicant Name: Second"))))
    name = next(field for field in fields if field.key == "full_name")
    assert name.status.startswith("Conflicting")
    assert name.source_page is None
    assert name.source_pages == (1, 2)


def test_duplicate_matching_values_are_reported_with_all_pages():
    fields = extract_fields(PDFExtraction((PDFPage(1, "Applicant Name: Same"), PDFPage(2, "Applicant Name: Same"))))
    name = next(field for field in fields if field.key == "full_name")
    assert name.value == "Same"
    assert name.source_pages == (1, 2)
    assert name.status.startswith("Duplicate")


def test_missing_fields_are_not_required():
    model, errors = validate_applicant({"full_name": "", "passport_number": ""})
    assert model is not None
    assert errors == []


def test_invalid_webfile_date_needs_review():
    _, errors = validate_applicant({"date_of_birth": "not a date"})
    assert len(errors) == 1


def test_profile_fields_are_separate_from_webfile_fields():
    webfile = ApplicantWebfile(full_name="Example")
    profile = IVACAccountProfile(email="person@example.com", nid_or_citizenship_number="123")
    assert "email" not in webfile.model_dump()
    assert "nid_or_citizenship_number" in profile.model_dump()


def test_manual_confirmations_are_not_extracted_fields():
    confirmations = ManualConfirmations(webfiles_unmodified=True)
    assert confirmations.webfiles_unmodified is True
    assert confirmations.applicant_details_consistent is None


def test_profile_validation_is_separate_and_optional():
    model, errors = validate_account_profile({"email": "bad", "date_of_birth": "not a date"})
    assert model is not None
    assert len(errors) == 2
    empty, empty_errors = validate_account_profile({})
    assert empty is not None
    assert empty_errors == []


def test_webfile_age_limit_includes_day_30_not_day_31():
    today = date(2026, 11, 4)
    assert webfile_age_status(date(2026, 10, 5), today)[0]
    assert not webfile_age_status(date(2026, 10, 4), today)[0]
    assert MAX_APPLICANTS == 4


def test_future_webfile_date_is_not_valid():
    valid, message = webfile_age_status(date(2026, 11, 5), date(2026, 11, 4))
    assert not valid
    assert "future" in message


def test_multiple_webfile_layouts_and_field_aliases():
    page = PDFPage(1, """APPLICANT NAME: Synthetic Applicant
Passport   No. : ZZ123456
Nationality : Exampleland
Sex: X
Web File No: WF1234
Visa Application Ref.: REF5678
Passport Date of Issue: 02/01/2025
Date of Expiry of Passport: 01/01/2035
Application Date: 03/04/2020""")
    fields = {field.key: field for field in extract_fields(PDFExtraction((page,)))}
    assert fields["full_name"].value == "Synthetic Applicant"
    assert fields["passport_number"].value == "ZZ123456"
    assert fields["gender"].value == "X"
    assert fields["webfile_number"].value == "WF1234"
    assert fields["visa_application_reference"].value == "REF5678"
    assert fields["passport_issue_date"].value == "02/01/2025"
    assert fields["passport_expiry_date"].value == "01/01/2035"
    assert fields["date_of_birth"].value is None


def test_field_split_across_lines_and_unusual_spacing():
    page = PDFPage(1, "Passport\u00a0\u00a0No. :\n  ZZ123456  \nDate of\nBirth: 05/06/1990")
    fields = {field.key: field for field in extract_fields(PDFExtraction((page,)))}
    assert fields["passport_number"].value == "ZZ123456"
    assert fields["passport_number"].confidence == "Medium"
    assert fields["date_of_birth"].value == "05/06/1990"
    assert fields["date_of_birth"].source_page == 1


def test_conflicting_passport_numbers_keep_both_page_sources():
    pages = (PDFPage(1, "Passport No: ZZ111"), PDFPage(2, "Passport Number: ZZ222"))
    field = next(field for field in extract_fields(PDFExtraction(pages)) if field.key == "passport_number")
    assert field.value == "ZZ111 / ZZ222"
    assert field.status.startswith("Conflicting")
    assert field.source_pages == (1, 2)
    assert field.confidence == "Low"


def test_missing_identity_field_has_not_detected_confidence():
    field = next(field for field in extract_fields(PDFExtraction((PDFPage(1, "Application Date: 03/04/2020"),))) if field.key == "passport_number")
    assert field.value is None
    assert field.confidence == "Not detected"
    assert field.verification_status == "Needs verification"


def test_explicit_day_first_date_parsing_does_not_use_application_date():
    model, errors = validate_applicant({"date_of_birth": "05/06/1990", "passport_issue_date": "02/01/2025", "passport_expiry_date": "01/01/2035"})
    assert not errors
    assert model.date_of_birth == date(1990, 6, 5)
    assert model.passport_issue_date == date(2025, 1, 2)


def test_supported_date_formats_normalize_and_invalid_confirmed_date_fails_validation():
    for raw, expected in (
        ("05-Jun-1990", "1990-06-05"),
        ("05/06/1990", "1990-06-05"),
        ("05-06-1990", "1990-06-05"),
        ("1990-06-05", "1990-06-05"),
    ):
        result = validate_field_value("date_of_birth", raw)
        assert result.passed
        assert result.normalized_value == expected
    invalid = validate_field_value("date_of_birth", "31-Feb-1990")
    assert not invalid.passed
    _, errors = validate_applicant({"date_of_birth": "31-Feb-1990"})
    assert errors
    assert not is_fully_verified("31-Feb-1990", applicant_confirmed=True, validation_passed=invalid.passed)
    assert is_fully_verified("1990-06-05", applicant_confirmed=True, validation_passed=True)


def make_visual_webfile_pdf():
    """Create an entirely fictional multi-column Webfile-style PDF page."""
    document = fitz.open()
    page = document.new_page(width=612, height=792)
    rows = (
        (55, 72, "INDIAN VISA APPLICATION CENTRE"),
        (75, 72, "Hotel Name: Synthetic Riverside Hotel"),
        (120, 72, "Applicant Name:"),
        (120, 190, "Synthetic Applicant"),
        (120, 410, "Hotel Name: Example Lodge"),
        (160, 72, "Passport No:"),
        (160, 185, "ZZ123456"),
        (160, 350, "Passport Date of Issue:"),
        (160, 510, "12-Feb-2022"),
        (200, 72, "Date of Birth:"),
        (200, 185, "05/06/1990"),
        (200, 350, "Religion: Fictional"),
        (240, 72, "Nationality/Status"),
        (240, 350, "Gender:"),
        (240, 415, "Female"),
        (240, 490, "Marital Status: Married"),
        (280, 72, "Web File No:"),
        (280, 185, "WF123456"),
        (280, 350, "Visa Application Reference:"),
        (280, 515, "REF12345"),
        (320, 72, "Passport Expiry Date:"),
        (320, 185, "31-Dec-2030"),
        (320, 350, "Application Date: 2022-01-15"),
    )
    for y, x, text in rows:
        page.insert_text((x, y), text, fontsize=10)
    raw = document.tobytes()
    document.close()
    return raw


def test_synthetic_visual_layout_uses_word_positions_and_field_boundaries():
    extracted = extract_pdf(io.BytesIO(make_visual_webfile_pdf()), "layout.pdf")
    assert extracted.pages[0].words
    fields = {field.key: field for field in extract_fields(extracted)}
    assert fields["full_name"].value == "Synthetic Applicant"
    assert fields["passport_number"].value == "ZZ123456"
    assert fields["passport_number"].source_references[0].source_text == "Passport No: ZZ123456"
    assert fields["date_of_birth"].value == "05/06/1990"
    assert fields["date_of_birth"].source_references[0].source_text == "Date of Birth: 05/06/1990"
    assert fields["date_of_birth"].normalized_value == "1990-06-05"
    assert fields["nationality"].value is None
    assert fields["gender"].value == "Female"
    assert fields["gender"].source_references[0].source_text == "Gender: Female"
    assert fields["webfile_number"].value == "WF123456"
    assert fields["visa_application_reference"].value == "REF12345"
    assert fields["passport_issue_date"].value == "12-Feb-2022"
    assert fields["passport_issue_date"].normalized_value == "2022-02-12"
    assert fields["passport_expiry_date"].value == "31-Dec-2030"
    assert fields["passport_expiry_date"].normalized_value == "2030-12-31"
    assert fields["full_name"].source_page == 1
    assert fields["full_name"].source_references[0].source_text == "Applicant Name: Synthetic Applicant"


def test_synthetic_split_label_and_date_variants_normalize():
    document = fitz.open()
    page = document.new_page(width=400, height=300)
    page.insert_text((72, 90), "Date of")
    page.insert_text((72, 105), "Birth:")
    page.insert_text((180, 105), "2020-03-04")
    raw = document.tobytes()
    document.close()
    extracted = extract_pdf(io.BytesIO(raw), "split-label.pdf")
    field = next(field for field in extract_fields(extracted) if field.key == "date_of_birth")
    assert field.value == "2020-03-04"
    assert field.normalized_value == "2020-03-04"
    assert field.source_page == 1


def test_synthetic_pdf_with_conflicting_passport_values_preserves_each_page_source():
    document = fitz.open()
    for value in ("ZZ111111", "ZZ222222"):
        page = document.new_page(width=400, height=300)
        page.insert_text((72, 100), "Passport No:")
        page.insert_text((180, 100), value)
    raw = document.tobytes()
    document.close()
    extracted = extract_pdf(io.BytesIO(raw), "conflicting-values.pdf")
    field = next(field for field in extract_fields(extracted) if field.key == "passport_number")
    assert field.status.startswith("Conflicting")
    assert field.value == "ZZ111111 / ZZ222222"
    assert field.source_pages == (1, 2)


def test_nationality_slash_status_column_is_not_a_nationality_value():
    document = fitz.open()
    page = document.new_page(width=400, height=300)
    page.insert_text((72, 100), "Nationality")
    page.insert_text((150, 100), "/Status")
    extracted = extract_pdf(io.BytesIO(document.tobytes()), "nationality-status.pdf")
    document.close()
    field = next(field for field in extract_fields(extracted) if field.key == "nationality")
    assert field.value is None
    assert field.confidence == "Not detected"
