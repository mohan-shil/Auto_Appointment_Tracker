"""Explicit JSON export for applicant-confirmed values only."""

import json
from typing import Any, Dict, Iterable, Optional


ALLOWED_FIELD_KEYS = (
    "key", "label", "value", "normalized_value", "original_extracted_value",
    "source_pages", "extraction_method", "confidence", "verification_status",
    "validation_passed", "validation_message",
)


def build_review_export(applicants: Iterable[Dict[str, Any]], profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build an allowlisted export; never copy PDF text or source excerpts."""
    exported_applicants = []
    for applicant in applicants:
        fields = []
        for field in applicant.get("fields", []):
            if field.get("verification_status") != "Confirmed by applicant" or not field.get("value") or field.get("validation_passed") is not True:
                continue
            fields.append({key: field.get(key) for key in ALLOWED_FIELD_KEYS if key in field})
        if fields:
            exported_applicants.append({"applicant": applicant.get("applicant", "Applicant"), "fields": fields})

    result: Dict[str, Any] = {"applicants": exported_applicants}
    if profile and profile.get("confirmed") is True and profile.get("validation_passed") is True and profile.get("values"):
        # Profile data is a separate user-confirmed section, not extracted PDF text.
        result["primary_account_profile"] = {
            key: value for key, value in profile["values"].items() if value not in (None, "")
        }
    if not exported_applicants and "primary_account_profile" not in result:
        raise ValueError("Confirm at least one applicant field or the account profile before exporting.")
    return result


def serialize_reviewed_applicants(applicants: Iterable[Dict[str, Any]], profile: Optional[Dict[str, Any]] = None) -> bytes:
    """Serialize explicitly reviewed applicant data to UTF-8 JSON bytes."""
    return json.dumps(build_review_export(applicants, profile), ensure_ascii=False, indent=2).encode("utf-8")
