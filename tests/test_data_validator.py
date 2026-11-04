from datetime import date

from config.readiness import MAX_APPLICANTS, webfile_age_status
from models.applicant import ApplicantWebfile, IVACAccountProfile, ManualConfirmations
from modules.data_validator import extract_fields, validate_account_profile, validate_applicant
from modules.pdf_reader import PDFExtraction, PDFPage


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
    fields = extract_fields(PDFExtraction((PDFPage(1, "Name: First"), PDFPage(2, "Name: Second"))))
    name = next(field for field in fields if field.key == "full_name")
    assert name.status.startswith("Conflicting")
    assert name.source_page is None
    assert name.source_pages == (1, 2)


def test_duplicate_matching_values_are_reported_with_all_pages():
    fields = extract_fields(PDFExtraction((PDFPage(1, "Name: Same"), PDFPage(2, "Name: Same"))))
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
