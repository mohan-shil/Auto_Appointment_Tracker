"""Configurable labels used to find values in application PDFs."""

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class FieldPattern:
    key: str
    label: str
    patterns: tuple[str, ...]
    aliases: tuple[str, ...] = ()


# Add or adjust aliases here as document formats change. Extraction may join a
# label/value across one line break, but never guesses unknown identity values.
FIELD_PATTERNS = (
    # Name aliases intentionally require an applicant-specific label. A bare
    # "Name" can refer to a hotel, institution, company, or document heading.
    FieldPattern("full_name", "Applicant full name", (r"applicant(?:['’]s)?\s+name", r"full\s*name", r"name\s+of\s+applicant"), ("Applicant Name", "Applicant's Name", "Applicant Full Name", "Full Name", "Name of Applicant")),
    FieldPattern("passport_number", "Passport number", (r"passport\s*(?:no\.?|number|#)", r"passport\s+number"), ("Passport No", "Passport Number")),
    FieldPattern("date_of_birth", "Date of birth", (r"date\s+of\s+birth", r"birth\s+date", r"dob"), ("Date of Birth", "Birth Date", "DOB")),
    FieldPattern("nationality", "Nationality", (r"nationality",), ("Nationality",)),
    FieldPattern("gender", "Gender", (r"gender", r"sex"), ("Gender", "Sex")),
    FieldPattern("webfile_number", "Webfile number", (r"web\s*file\s*(?:no\.?|number|#)?", r"application\s+webfile\s*(?:no\.?|number|#)?"), ("Webfile", "Webfile No", "Webfile Number", "Web File No", "Web File Number", "Application Webfile No", "Application Webfile Number")),
    FieldPattern("visa_application_reference", "Visa application reference", (r"(?:visa\s+)?application\s+(?:reference|ref\.?|number|no\.?|#)", r"visa\s+application\s+id"), ("Visa Application Reference", "Visa Application Ref", "Application Reference No", "Application Reference Number", "Visa Application ID")),
    # Passport dates use passport-specific labels. Generic "issue date" and
    # "expiry date" are intentionally excluded to avoid confusing application dates.
    FieldPattern("passport_issue_date", "Passport issue date", (r"passport\s+(?:date\s+of\s+)?issue(?:\s+date)?", r"date\s+of\s+issue\s+of\s+passport"), ("Passport Issue Date", "Passport Date of Issue", "Date of Issue of Passport")),
    FieldPattern("passport_expiry_date", "Passport expiry date", (r"passport\s+(?:date\s+of\s+)?expir(?:y|ation)(?:\s+date)?", r"date\s+of\s+expir(?:y|ation)\s+of\s+passport", r"passport\s+valid\s+until"), ("Passport Expiry Date", "Passport Expiration Date", "Passport Date of Expiry", "Date of Expiry of Passport", "Passport Valid Until")),
)

# These neighboring labels are not values. They delimit fields even though the
# app does not currently extract their contents.
BOUNDARY_ALIASES = (
    "Religion", "Marital Status", "Nationality/Status", "Status",
    "Application Date", "Date of Application", "Date of Submission",
    "Place of Birth", "Place of Issue", "Issuing Authority",
)


def compile_label_pattern(label_pattern: str) -> re.Pattern[str]:
    """Compile a label matcher that accepts common punctuation separators."""
    return re.compile(rf"^\s*(?:{label_pattern})\s*[:：\-]?\s*(.*?)\s*$", re.IGNORECASE)
