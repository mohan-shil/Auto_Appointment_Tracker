import json

import pytest

from modules.data_export import build_review_export, serialize_reviewed_applicants


def test_export_includes_only_applicant_confirmed_allowlisted_fields():
    applicants = [{
        "applicant": "Primary applicant",
        "fields": [
            {
                "key": "passport_number",
                "label": "Passport number",
                "value": "ZZ123456",
                "source_pages": [1],
                "extraction_method": "Selectable text",
                "confidence": "High",
                "verification_status": "Confirmed by applicant",
                "source_text": "Passport No: ZZ123456",
                "pdf_content": "large original document contents",
            },
            {"key": "full_name", "value": "Not yet reviewed", "verification_status": "Needs verification"},
        ],
    }]
    payload = build_review_export(applicants)
    field = payload["applicants"][0]["fields"][0]
    assert field["value"] == "ZZ123456"
    assert field["source_pages"] == [1]
    assert "source_text" not in field
    serialized = serialize_reviewed_applicants(applicants).decode("utf-8")
    assert "large original document contents" not in serialized
    assert json.loads(serialized) == payload
    assert len(payload["applicants"][0]["fields"]) == 1


def test_export_requires_at_least_one_confirmed_value():
    with pytest.raises(ValueError, match="Confirm at least one"):
        build_review_export([{"applicant": "Primary", "fields": [{"value": "ZZ", "verification_status": "Needs verification"}]}])


def test_profile_export_requires_separate_explicit_confirmation():
    with pytest.raises(ValueError, match="Confirm at least one"):
        build_review_export([], {"confirmed": False, "values": {"email": "safe@example.test"}})
    exported = build_review_export([], {"confirmed": True, "values": {"email": "safe@example.test", "mobile_number": ""}})
    assert exported["primary_account_profile"] == {"email": "safe@example.test"}
