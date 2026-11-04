"""Conservative field extraction with traceable source and review metadata."""

from dataclasses import dataclass
from datetime import date, datetime
import re
from typing import Optional, Tuple

from pydantic import ValidationError

from config.field_mapping import FIELD_PATTERNS, FieldPattern, compile_label_pattern
from models.applicant import ApplicantWebfile, IVACAccountProfile
from modules.pdf_reader import PDFExtraction, PDFPage


@dataclass(frozen=True)
class SourceReference:
    page_number: int
    extraction_method: str
    source_text: str
    confidence: str


@dataclass(frozen=True)
class ExtractedField:
    key: str
    label: str
    value: Optional[str]
    source_page: Optional[int]
    status: str
    source_pages: tuple[int, ...] = ()
    extraction_method: str = "Not detected"
    confidence: str = "Not detected"
    verification_status: str = "Needs verification"
    source_references: Tuple[SourceReference, ...] = ()


@dataclass(frozen=True)
class _Candidate:
    value: str
    reference: SourceReference


def _normalize_line(line: str) -> str:
    """Normalize layout whitespace for matching, without changing source excerpts."""
    return re.sub(r"\s+", " ", line.replace("\u00a0", " ").replace("\u200b", "").replace("\ufeff", " ")).strip()


def _starts_any_field(line: str) -> bool:
    candidate = _normalize_line(line)
    for field in FIELD_PATTERNS:
        if any(compile_label_pattern(pattern).match(candidate) for pattern in field.patterns):
            return True
    return False


def _trim_next_field(value: str, current_key: str) -> str:
    """Keep a same-line field value from absorbing a following labeled field."""
    cut_points = []
    for field in FIELD_PATTERNS:
        if field.key == current_key:
            continue
        for label in field.patterns:
            next_label = re.compile(rf"\s+(?:{label})\s*[:：\-]", re.IGNORECASE).search(value)
            if next_label:
                cut_points.append(next_label.start())
    return value[: min(cut_points)].strip(" \t,;|") if cut_points else value.strip()


def _field_candidates(field: FieldPattern, page: PDFPage, text: str, method: str, ocr_confidence: Optional[float]) -> list[_Candidate]:
    lines = text.splitlines()
    candidates = []
    for line_number, original_line in enumerate(lines):
        normalized_line = _normalize_line(original_line)
        if not normalized_line:
            continue
        for pattern in field.patterns:
            match = compile_label_pattern(pattern).match(normalized_line)
            source_lines = [original_line]
            raw_value = match.group(1).strip() if match else ""
            normalized_match = True

            # A label can end one line and its value start on the next, or the
            # label itself can be split across two lines. Don't consume another
            # configured field as a supposed value.
            if (not match or not raw_value) and line_number + 1 < len(lines):
                next_line = lines[line_number + 1]
                if _normalize_line(next_line) and not _starts_any_field(next_line):
                    combined = normalized_line + " " + _normalize_line(next_line)
                    combined_match = compile_label_pattern(pattern).match(combined)
                    if combined_match and combined_match.group(1).strip():
                        match = combined_match
                        raw_value = combined_match.group(1).strip()
                        source_lines = [original_line, next_line]
                        normalized_match = False
            if not match or not raw_value:
                continue

            value = _trim_next_field(raw_value, field.key)
            if not value:
                continue
            if method == "OCR (local Tesseract)":
                confidence = "Medium" if ocr_confidence is not None and ocr_confidence >= 70 else "Low"
            else:
                confidence = "High" if normalized_match and normalized_line == original_line.strip() else "Medium"
            excerpt = "\n".join(source_lines).strip()
            candidates.append(_Candidate(value, SourceReference(page.page_number, method, excerpt, confidence)))
            break
    return candidates


def extract_fields(pdf: PDFExtraction) -> list[ExtractedField]:
    """Extract same-line and split-line labels, keeping every source reference."""
    found = []
    for field in FIELD_PATTERNS:
        matches = []
        for page in pdf.pages:
            if page.text.strip():
                matches.extend(_field_candidates(field, page, page.text, "Selectable text", None))
            elif page.ocr_text and page.ocr_text.strip():
                matches.extend(_field_candidates(field, page, page.ocr_text, "OCR (local Tesseract)", page.ocr_confidence))

        distinct_values = {candidate.value for candidate in matches}
        source_references = tuple(candidate.reference for candidate in matches)
        source_pages = tuple(reference.page_number for reference in source_references)
        if not matches:
            value, source_page, status, method, confidence = None, None, "Needs review — not found", "Not detected", "Not detected"
        elif len(distinct_values) == 1 and len(matches) == 1:
            value, source_page, status = matches[0].value, matches[0].reference.page_number, "Needs review"
            method, confidence = matches[0].reference.extraction_method, matches[0].reference.confidence
        elif len(distinct_values) == 1:
            value, source_page, status = matches[0].value, None, "Duplicate value found — needs review"
            methods = {reference.extraction_method for reference in source_references}
            method = next(iter(methods)) if len(methods) == 1 else "Mixed extraction methods"
            confidence = "Low"
        else:
            value, source_page, status = " / ".join(dict.fromkeys(candidate.value for candidate in matches)), None, "Conflicting values — needs review"
            methods = {reference.extraction_method for reference in source_references}
            method = next(iter(methods)) if len(methods) == 1 else "Mixed extraction methods"
            confidence = "Low"
        found.append(ExtractedField(field.key, field.label, value, source_page, status, source_pages, method, confidence, "Needs verification", source_references))
    return found


def validate_applicant(values: dict[str, object]) -> tuple[Optional[ApplicantWebfile], list[str]]:
    """Validate Webfile values without requiring fields or guessing missing data."""
    cleaned = {key: (value.strip() if isinstance(value, str) else value) for key, value in values.items()}
    cleaned = {key: value or None for key, value in cleaned.items()}
    errors: list[str] = []
    for key in ("date_of_birth", "passport_issue_date", "passport_expiry_date"):
        value = cleaned.get(key)
        if isinstance(value, str) and value:
            parsed = _parse_date(value)
            if parsed is None:
                errors.append(f"{key.replace('_', ' ').title()} needs review: use YYYY-MM-DD or DD/MM/YYYY.")
                cleaned[key] = None
            else:
                cleaned[key] = parsed
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
    """Parse explicit ISO or day-first Webfile dates; source strings stay unchanged in UI/export."""
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return date.fromisoformat(value) if fmt == "%Y-%m-%d" else datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None
