"""Layout-aware Webfile field extraction and applicant-side validation."""

from dataclasses import dataclass
from datetime import date, datetime
import re
from typing import List, Optional, Sequence, Tuple

from pydantic import ValidationError

from config.field_mapping import BOUNDARY_ALIASES, FIELD_PATTERNS, FieldPattern
from models.applicant import ApplicantWebfile, IVACAccountProfile
from modules.pdf_reader import PDFExtraction, PDFPage, PDFWord


DATE_KEYS = frozenset(("date_of_birth", "passport_issue_date", "passport_expiry_date"))
DATE_PATTERN = re.compile(
    r"(?<!\d)(?:\d{4}\s*-\s*\d{1,2}\s*-\s*\d{1,2}|"
    r"\d{1,2}\s*[-/]\s*[A-Za-z]{3,9}\s*[-/]\s*\d{4}|"
    r"\d{1,2}\s*[-/]\s*\d{1,2}\s*[-/]\s*\d{2,4})(?!\d)"
)


@dataclass(frozen=True)
class SourceReference:
    page_number: int
    extraction_method: str
    source_text: str
    confidence: str


@dataclass(frozen=True)
class FieldValidation:
    passed: bool
    normalized_value: Optional[str]
    message: str


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
    original_value: Optional[str] = None
    normalized_value: Optional[str] = None


@dataclass(frozen=True)
class _Candidate:
    value: str
    normalized_value: Optional[str]
    reference: SourceReference


def _word_token(value: str) -> str:
    """Normalize one PDF word for exact alias comparison."""
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _alias_tokens(alias: str) -> Tuple[str, ...]:
    normalized = alias.casefold().replace("'", "").replace("’", "")
    return tuple(_word_token(token) for token in re.findall(r"[^\W_]+", normalized, re.UNICODE) if _word_token(token))


def _rows(words: Sequence[PDFWord]) -> List[List[PDFWord]]:
    """Group positioned words by visual baseline, including adjacent columns."""
    rows: List[List[PDFWord]] = []
    centers: List[float] = []
    for word in sorted(words, key=lambda item: ((item.y0 + item.y1) / 2, item.x0)):
        center = (word.y0 + word.y1) / 2
        row_index = next((index for index, row_center in enumerate(centers) if abs(center - row_center) <= 3.0), None)
        if row_index is None:
            centers.append(center)
            rows.append([word])
        else:
            rows[row_index].append(word)
            centers[row_index] = sum((item.y0 + item.y1) / 2 for item in rows[row_index]) / len(rows[row_index])
    return [sorted(row, key=lambda item: item.x0) for row in rows]


def _find_aliases(words: Sequence[PDFWord], aliases: Sequence[str], start_at: int = 0) -> List[Tuple[int, int, str]]:
    tokens = [_word_token(word.text) for word in words]
    matches = []
    for alias in sorted(aliases, key=lambda item: len(_alias_tokens(item)), reverse=True):
        alias_tokens = _alias_tokens(alias)
        if not alias_tokens:
            continue
        limit = len(tokens) - len(alias_tokens) + 1
        for start in range(start_at, max(start_at, limit)):
            if tuple(tokens[start:start + len(alias_tokens)]) == alias_tokens:
                matches.append((start, start + len(alias_tokens), alias))
    # Prefer the longest alias when labels share a prefix (e.g. Webfile and
    # Webfile Number). Short aliases must not consume a field suffix as value.
    selected = []
    for match in sorted(matches, key=lambda item: (item[0], -(item[1] - item[0]))):
        if selected and match[0] < selected[-1][1]:
            continue
        selected.append(match)
    return selected


def _all_boundary_aliases() -> Tuple[str, ...]:
    aliases = [alias for field in FIELD_PATTERNS for alias in field.aliases]
    aliases.extend(BOUNDARY_ALIASES)
    return tuple(dict.fromkeys(aliases))


BOUNDARY_LABELS = _all_boundary_aliases()


def _value_words(words: Sequence[PDFWord], start: int, end: int, key: str) -> List[PDFWord]:
    selected = [word for word in words[start:end] if _word_token(word.text)]
    # A visual gap after a label's first value usually signals a neighboring
    # column whose label is absent or unfamiliar. Stop before absorbing it.
    result = []
    previous = None
    for word in selected:
        if previous is not None and word.x0 - previous.x1 > 35:
            break
        result.append(word)
        previous = word
        if key in ("passport_number", "date_of_birth", "passport_issue_date", "passport_expiry_date", "gender") and len(result) >= 4:
            break
        if key in ("full_name", "nationality") and len(result) >= 5:
            break
        if key in ("webfile_number", "visa_application_reference") and len(result) >= 4:
            break
    return result


def _split_date(raw_value: str) -> Optional[Tuple[str, str]]:
    """Return original date text and ISO normalization when a date is valid."""
    match = DATE_PATTERN.search(raw_value)
    if not match:
        return None
    original = re.sub(r"\s*([/-])\s*", r"\1", match.group(0)).strip()
    parsed = _parse_date(original)
    if parsed is None:
        return (original, "")
    return original, parsed.isoformat()


def _candidate_value(key: str, words: Sequence[PDFWord]) -> Tuple[Optional[str], Optional[str]]:
    if not words:
        return None, None
    raw = " ".join(word.text.strip() for word in words if word.text.strip()).strip(" \t:：-–—,;|")
    if not raw:
        return None, None
    if key in DATE_KEYS:
        result = _split_date(raw)
        return (result[0], result[1] or None) if result else (None, None)
    if key == "passport_number":
        token = next((word.text.strip(" \t:：-–—,;|") for word in words if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{3,19}", word.text.strip(" \t:：-–—,;|"))), None)
        return (token, None) if token else (None, None)
    return raw, None


def _layout_candidates(field: FieldPattern, page: PDFPage, words: Sequence[PDFWord], method: str, ocr_confidence: Optional[float]) -> List[_Candidate]:
    visual_rows = _rows(words)
    candidates: List[_Candidate] = []
    for row_index, row in enumerate(visual_rows):
        for label_start, label_end, alias in _find_aliases(row, field.aliases):
            # "Nationality/Status" is a combined label, not a nationality value.
            next_raw = row[label_end].text if label_end < len(row) else ""
            if field.key == "nationality" and next_raw.startswith("/"):
                continue

            next_label_positions = [match[0] for match in _find_aliases(row, BOUNDARY_LABELS, label_end)]
            boundary = min(next_label_positions) if next_label_positions else len(row)
            value_words = _value_words(row, label_end, boundary, field.key)
            confidence = "High" if value_words else "Not detected"
            source_words = list(row[label_start:label_end]) + value_words

            if not value_words and row_index + 1 < len(visual_rows):
                next_row = visual_rows[row_index + 1]
                vertical_gap = min(word.y0 for word in next_row) - max(word.y1 for word in row)
                nearby_labels = _find_aliases(next_row, BOUNDARY_LABELS)
                label = row[label_start:label_end]
                x_anchor = label[0].x0
                column_end = x_anchor + max(200, label[-1].x1 - x_anchor + 70)
                column_words = [word for word in next_row if x_anchor - 10 <= word.x0 <= column_end]
                if 0 <= vertical_gap <= 28 and not nearby_labels:
                    value_words = _value_words(column_words, 0, len(column_words), field.key)
                    source_words = list(label) + value_words
                    confidence = "Medium" if value_words else "Not detected"

            value, normalized = _candidate_value(field.key, value_words)
            if not value:
                continue
            if field.key in DATE_KEYS and not normalized:
                confidence = "Low"
            if method == "OCR (local Tesseract)":
                confidence = "Medium" if ocr_confidence is not None and ocr_confidence >= 70 else "Low"
            excerpt = " ".join(word.text for word in source_words).strip()
            candidates.append(_Candidate(value, normalized, SourceReference(page.page_number, method, excerpt, confidence)))
            # Continue scanning the row to retain repeated labels and conflicts.
    return candidates


def _fallback_words(text: str) -> Tuple[PDFWord, ...]:
    """Create line/column-compatible word positions if source geometry is absent."""
    words = []
    for line_number, line in enumerate(text.splitlines()):
        for word_number, match in enumerate(re.finditer(r"\S+", line)):
            x0 = float(match.start() * 5)
            x1 = float(match.end() * 5)
            y0 = float(line_number * 14)
            words.append(PDFWord(match.group(0), x0, y0, x1, y0 + 10, 0, line_number, word_number))
    return tuple(words)


def _line_candidates(field: FieldPattern, page: PDFPage, text: str, method: str, ocr_confidence: Optional[float]) -> List[_Candidate]:
    """Exact-label fallback for OCR and synthetic text without coordinate data."""
    lines = text.splitlines()
    candidates = []
    aliases = sorted(field.aliases, key=lambda item: len(_alias_tokens(item)), reverse=True)
    all_aliases = sorted(BOUNDARY_LABELS, key=lambda item: len(_alias_tokens(item)), reverse=True)
    for index, line in enumerate(lines):
        for alias in aliases:
            alias_re = r"\s+".join(re.escape(word) for word in alias.split())
            match = re.match(rf"^\s*{alias_re}(?=$|\s|[:：\-])\s*[:：\-]?\s*(.*?)\s*$", line, re.IGNORECASE)
            source_lines = [line]
            tail = match.group(1).strip() if match else ""
            confidence = "High"
            if (not match or not tail) and index + 1 < len(lines):
                next_line = lines[index + 1]
                next_is_label = False
                for candidate in all_aliases:
                    candidate_re = r"\s+".join(re.escape(word) for word in candidate.split())
                    if re.match(rf"^\s*{candidate_re}(?=$|\s|[:：\-])", next_line, re.IGNORECASE):
                        next_is_label = True
                        break
                if not next_is_label:
                    combined = line.strip() + " " + next_line.strip()
                    cross_match = re.match(rf"^\s*{alias_re}(?=$|\s|[:：\-])\s*[:：\-]?\s*(.*?)\s*$", combined, re.IGNORECASE)
                    if cross_match and cross_match.group(1).strip():
                        match, tail = cross_match, cross_match.group(1).strip()
                        source_lines = [line, next_line]
                        confidence = "Medium"
            if not match or not tail:
                continue
            # Cut at any configured adjacent field/boundary label. Punctuation
            # and slash combined labels must not become identity values.
            cut_points = []
            for candidate in all_aliases:
                candidate_re = r"\s+".join(re.escape(word) for word in candidate.split())
                boundary_match = re.search(rf"\s+(?:{candidate_re})(?=$|\s|[:：\-])", tail, re.IGNORECASE)
                if boundary_match:
                    cut_points.append(boundary_match.start())
            if cut_points:
                tail = tail[: min(cut_points)].strip()
            if field.key == "nationality" and tail.lstrip().startswith("/"):
                continue
            words = _fallback_words(tail)
            value, normalized = _candidate_value(field.key, words)
            if not value:
                continue
            if field.key in DATE_KEYS and not normalized:
                confidence = "Low"
            if method == "OCR (local Tesseract)":
                confidence = "Medium" if ocr_confidence is not None and ocr_confidence >= 70 else "Low"
            candidates.append(_Candidate(value, normalized, SourceReference(page.page_number, method, "\n".join(source_lines).strip(), confidence)))
            break
    return candidates


def _extract_page_candidates(field: FieldPattern, page: PDFPage, text: str, method: str, ocr_confidence: Optional[float]) -> List[_Candidate]:
    words = page.words if method == "Selectable text" else ()
    candidates = _layout_candidates(field, page, words, method, ocr_confidence) if words else []
    if not candidates:
        fallback = _fallback_words(text)
        candidates = _layout_candidates(field, page, fallback, method, ocr_confidence)
    if not candidates:
        candidates = _line_candidates(field, page, text, method, ocr_confidence)
    return candidates


def extract_fields(pdf: PDFExtraction) -> list[ExtractedField]:
    """Extract using word geometry first and exact configured aliases as fallback."""
    found = []
    for field in FIELD_PATTERNS:
        matches = []
        for page in pdf.pages:
            if page.text.strip():
                matches.extend(_extract_page_candidates(field, page, page.text, "Selectable text", None))
            elif page.ocr_text and page.ocr_text.strip():
                matches.extend(_extract_page_candidates(field, page, page.ocr_text, "OCR (local Tesseract)", page.ocr_confidence))
        distinct_values = {candidate.value for candidate in matches}
        references = tuple(candidate.reference for candidate in matches)
        source_pages = tuple(reference.page_number for reference in references)
        if not matches:
            value, normalized, source_page, status, method, confidence = None, None, None, "Needs review — not found", "Not detected", "Not detected"
        elif len(distinct_values) == 1 and len(matches) == 1:
            value, normalized, source_page, status = matches[0].value, matches[0].normalized_value, matches[0].reference.page_number, "Needs review"
            method, confidence = matches[0].reference.extraction_method, matches[0].reference.confidence
        elif len(distinct_values) == 1:
            value, normalized, source_page, status = matches[0].value, matches[0].normalized_value, None, "Duplicate value found — needs review"
            methods = {reference.extraction_method for reference in references}
            method = next(iter(methods)) if len(methods) == 1 else "Mixed extraction methods"
            confidence = "Low"
        else:
            value = " / ".join(dict.fromkeys(candidate.value for candidate in matches))
            normalized, source_page, status = None, None, "Conflicting values — needs review"
            methods = {reference.extraction_method for reference in references}
            method, confidence = (next(iter(methods)) if len(methods) == 1 else "Mixed extraction methods"), "Low"
        found.append(ExtractedField(field.key, field.label, value, source_page, status, source_pages, method, confidence, "Needs verification", references, value, normalized))
    return found


def validate_field_value(field_key: str, value: object) -> FieldValidation:
    """Validate presence and field-specific date syntax without claiming identity accuracy."""
    text = value.strip() if isinstance(value, str) else ""
    if not text:
        return FieldValidation(False, None, "Not validated — value is missing.")
    if field_key in DATE_KEYS:
        parsed = _parse_date(text)
        if parsed is None:
            return FieldValidation(False, None, "Needs review — date must be DD-MMM-YYYY, DD/MM/YYYY, DD-MM-YYYY, or YYYY-MM-DD.")
        return FieldValidation(True, parsed.isoformat(), "Passed date-format validation; compare it with the original document.")
    return FieldValidation(True, text, "Value present; content is not independently authenticated.")


def is_fully_verified(value: object, applicant_confirmed: bool, validation_passed: bool) -> bool:
    """A value is fully verified only when all three independent states pass."""
    return bool(value) and applicant_confirmed and validation_passed


def validate_applicant(values: dict[str, object]) -> tuple[Optional[ApplicantWebfile], list[str]]:
    """Validate Webfile values without requiring fields or guessing missing data."""
    cleaned = {key: (value.strip() if isinstance(value, str) else value) for key, value in values.items()}
    cleaned = {key: value or None for key, value in cleaned.items()}
    errors: list[str] = []
    for key in DATE_KEYS:
        value = cleaned.get(key)
        if isinstance(value, str) and value:
            parsed = _parse_date(value)
            if parsed is None:
                errors.append(validate_field_value(key, value).message)
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
    formats = (
        "%d-%b-%Y", "%d-%B-%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d",
        "%d %b %Y", "%d %B %Y",
    )
    for fmt in formats:
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None
