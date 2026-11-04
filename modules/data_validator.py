"""Conservative field extraction and validation helpers."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from pydantic import ValidationError

from config.field_mapping import FIELD_PATTERNS, compile_label_pattern
from models.applicant import ApplicantWebfile, IVACAccountProfile
from modules.pdf_reader import PDFExtraction


@dataclass(frozen=True)
class ExtractedField:
    key: str
    label: str
    value: Optional[str]
    source_page: Optional[int]
    status: str
    source_pages: tuple[int, ...] = ()


def extract_fields(pdf: PDFExtraction) -> list[ExtractedField]:
    """Find same-line label/value pairs; duplicate matches require user review."""
    found: list[ExtractedField] = []
    for field in FIELD_PATTERNS:
        matches: list[tuple[str, int]] = []
        for page in pdf.pages:
            for line in page.text.splitlines():
                for label_pattern in field.patterns:
                    match = compile_label_pattern(label_pattern).match(line)
                    if match and match.group(1).strip():
                        matches.append((match.group(1).strip(), page.page_number))
                        break
        distinct = {value for value, _ in matches}
        source_pages = tuple(page for _, page in matches)
        if len(distinct) == 1 and len(matches) == 1:
            value, page_number = matches[0]
            status = "Needs review"
        elif len(distinct) == 1:
            value, page_number, status = matches[0][0], None, "Duplicate value found — needs review"
        elif len(distinct) > 1:
            value, page_number, status = " / ".join(sorted(distinct)), None, "Ambiguous — needs review"
        else:
            value, page_number, status, source_pages = None, None, "Needs review — not found", ()
        found.append(ExtractedField(field.key, field.label, value, page_number, status, source_pages))
    return found


def validate_applicant(values: dict[str, object]) -> tuple[Optional[ApplicantWebfile], list[str]]:
    """Validate supplied values without making any fields mandatory."""
    cleaned = {key: (value.strip() if isinstance(value, str) else value) for key, value in values.items()}
    cleaned = {key: value or None for key, value in cleaned.items()}
    errors: list[str] = []
    dob = cleaned.get("date_of_birth")
    if isinstance(dob, str) and dob:
        parsed = _parse_date(dob)
        if parsed is None:
            errors.append("Date of birth needs review: use YYYY-MM-DD or DD/MM/YYYY.")
            cleaned["date_of_birth"] = None
        else:
            cleaned["date_of_birth"] = parsed
    try:
        model = ApplicantWebfile(**cleaned)
    except ValidationError as exc:
        errors.extend(error["msg"] for error in exc.errors())
        model = None
    return model, errors


def validate_account_profile(values: dict[str, object]) -> tuple[Optional[IVACAccountProfile], list[str]]:
    """Validate manually provided portal profile details, separately from PDF fields."""
    cleaned = {key: (value.strip() if isinstance(value, str) else value) for key, value in values.items()}
    cleaned = {key: value or None for key, value in cleaned.items()}
    errors: list[str] = []
    email = cleaned.get("email")
    if email and (not isinstance(email, str) or "@" not in email or "." not in email.rsplit("@", 1)[-1]):
        errors.append("Account email needs review: check its format.")
    dob = cleaned.get("date_of_birth")
    if isinstance(dob, str) and dob:
        parsed = _parse_date(dob)
        if parsed is None:
            errors.append("Account date of birth needs review: use YYYY-MM-DD or DD/MM/YYYY.")
            cleaned["date_of_birth"] = None
        else:
            cleaned["date_of_birth"] = parsed
    try:
        model = IVACAccountProfile(**cleaned)
    except ValidationError as exc:
        errors.extend(error["msg"] for error in exc.errors())
        model = None
    return model, errors


def _parse_date(value: str) -> Optional[date]:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return date.fromisoformat(value) if fmt == "%Y-%m-%d" else datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None
