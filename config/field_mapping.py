"""Configurable labels used to find values in application PDFs."""

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class FieldPattern:
    key: str
    label: str
    patterns: tuple[str, ...]


# Add or adjust aliases here as document formats change. Patterns capture only
# text on the same line after a known label; no identity details are guessed.
FIELD_PATTERNS = (
    FieldPattern("full_name", "Applicant full name", (r"(?:applicant\s+)?name", r"full\s+name")),
    FieldPattern("passport_number", "Passport number", (r"passport\s*(?:no\.?|number)",)),
    FieldPattern("date_of_birth", "Date of birth", (r"date\s+of\s+birth", r"dob")),
    FieldPattern("nationality", "Nationality", (r"nationality",)),
    FieldPattern("gender", "Gender", (r"gender", r"sex",)),
    FieldPattern("webfile_number", "Webfile number", (r"webfile\s*(?:no\.?|number)?",)),
    FieldPattern("visa_application_reference", "Visa application reference", (r"(?:visa\s+)?application\s+(?:reference|ref|number|no\.?)",)),
)


def compile_label_pattern(label_pattern: str) -> re.Pattern[str]:
    """Compile a label matcher that accepts common punctuation separators."""
    return re.compile(rf"^\s*(?:{label_pattern})\s*[:：\-]?\s*(.*?)\s*$", re.IGNORECASE)
