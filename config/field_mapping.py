"""Configurable labels used to find values in application PDFs."""

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class FieldPattern:
    key: str
    label: str
    patterns: tuple[str, ...]


# Add or adjust aliases here as document formats change. Extraction may join a
# label/value across one line break, but never guesses unknown identity values.
FIELD_PATTERNS = (
    FieldPattern("full_name", "Applicant full name", (r"(?:applicant['’]?s?\s+)?name", r"full\s*name", r"name\s+of\s+applicant")),
    FieldPattern("passport_number", "Passport number", (r"passport\s*(?:no\.?|number|#)", r"passport\s+number")),
    FieldPattern("date_of_birth", "Date of birth", (r"date\s+of\s+birth", r"birth\s+date", r"dob")),
    FieldPattern("nationality", "Nationality", (r"nationality",)),
    FieldPattern("gender", "Gender", (r"gender", r"sex")),
    FieldPattern("webfile_number", "Webfile number", (r"web\s*file\s*(?:no\.?|number|#)?", r"application\s+webfile\s*(?:no\.?|number|#)?")),
    FieldPattern("visa_application_reference", "Visa application reference", (r"(?:visa\s+)?application\s+(?:reference|ref\.?|number|no\.?|#)", r"visa\s+application\s+id")),
    # Passport dates use passport-specific labels. Generic "issue date" and
    # "expiry date" are intentionally excluded to avoid confusing application dates.
    FieldPattern("passport_issue_date", "Passport issue date", (r"passport\s+(?:date\s+of\s+)?issue(?:\s+date)?", r"date\s+of\s+issue\s+of\s+passport")),
    FieldPattern("passport_expiry_date", "Passport expiry date", (r"passport\s+(?:date\s+of\s+)?expir(?:y|ation)(?:\s+date)?", r"date\s+of\s+expir(?:y|ation)\s+of\s+passport", r"passport\s+valid\s+until")),
)


def compile_label_pattern(label_pattern: str) -> re.Pattern[str]:
    """Compile a label matcher that accepts common punctuation separators."""
    return re.compile(rf"^\s*(?:{label_pattern})\s*[:：\-]?\s*(.*?)\s*$", re.IGNORECASE)
