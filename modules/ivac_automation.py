"""Read-only IVAC workflow guidance; no website interactions are automated."""

SAFE_SCOPE = (
    "The applicant performs all login, OTP, CAPTCHA, upload, form entry, centre/date selection, "
    "submission, booking, and payment actions personally."
)

FAQ_BOOKING_STEPS = (
    "Sign in manually",
    "Choose Book Your Appointment",
    "Upload the primary Webfile, then secondary Webfiles if applicable",
    "Review and select an eligible IVAC centre",
    "Choose an available future appointment date, if one is offered",
    "Review the booking and complete payment personally",
    "Confirm booking and download the invoice if the portal confirms success",
)

DISPLAY_FIELDS = (
    ("full_name", "Applicant name"),
    ("passport_number", "Passport number"),
    ("webfile_number", "Webfile number"),
    ("visa_application_reference", "Visa reference"),
)


def confirmed_applicant_summary(applicants):
    """Return only applicant-confirmed, validation-passed identity values."""
    summary = []
    for applicant in applicants:
        fields = {
            item.get("key"): item
            for item in applicant.get("fields", [])
            if item.get("verification_status") == "Confirmed by applicant"
            and item.get("validation_passed") is True
            and isinstance(item.get("value"), str)
            and item.get("value", "").strip()
        }
        visible_fields = {
            key: {"label": label, "value": fields[key]["value"]}
            for key, label in DISPLAY_FIELDS
            if key in fields
        }
        if visible_fields:
            summary.append({
                "applicant": applicant.get("applicant", "Applicant"),
                "status": "Reviewed fields available" if len(visible_fields) == len(DISPLAY_FIELDS) else "Some reviewed fields missing",
                "fields": visible_fields,
            })
        else:
            summary.append({
                "applicant": applicant.get("applicant", "Applicant"),
                "status": "Needs applicant review",
                "fields": {},
            })
    return summary
