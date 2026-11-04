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


def test_ambiguous_duplicate_requires_review():
    fields = extract_fields(PDFExtraction((PDFPage(1, "Name: First"), PDFPage(2, "Name: Second"))))
    name = next(field for field in fields if field.key == "full_name")
    assert name.status.startswith("Ambiguous")
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
