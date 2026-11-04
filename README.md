# Auto_Appointment_Tracker — Auto Appointment Tracker

A local applicant-assistance tool for reviewing IVAC Webfiles and preparing for the official appointment process. It does not log in, solve CAPTCHA, handle OTP, submit forms, poll for slots, reserve appointments, or make payments. Applicants must perform every IVAC website action themselves.

## What it does

- Accepts up to four applicant Webfile PDFs (one primary and up to three secondary applicants), each up to 15 MB.
- Extracts selectable text locally with PyMuPDF, preserves each page's original text, and limits PDFs to 300 pages.
- Can optionally run local Tesseract OCR on pages that have no selectable text. OCR output is kept separate from native PDF text and every extracted identity value still requires applicant confirmation.
- Flags empty, unreadable, password-protected, scanned/no-text, duplicate, and conflicting data for review. It never guesses or silently corrects identity details.
- Recognizes configurable name, passport number, DOB, nationality, gender, Webfile, visa reference, passport issue date and passport expiry labels. It handles split lines and spacing variations while avoiding generic application dates for passport-specific date fields.
- Shows field-level source page and excerpt, extraction method, heuristic confidence category, and applicant verification status.
- Provides an applicant list, missing-information indicators, 30-day Webfile date check, and a manually completed preparation checklist.
- Offers an explicit JSON download of applicant-confirmed values; the export excludes source excerpts and original PDF contents.
- Processes files and values in the Streamlit session only; this project does not write them to disk or send applicant data to an external AI service. Streamlit usage statistics are disabled in `.streamlit/config.toml`.

## IVAC FAQ guidance

The checklist reflects the [official IVAC Appointment Management System FAQ](https://www.ivacbd.com/faq/appointment-management-system): a Webfile must be no older than 30 days; one account can include at most four applicants (one primary and up to three secondary); applicants select an eligible IVAC centre and an available future date; booking is confirmed after successful payment and an invoice is generated. The FAQ advises applicants to sign up and book themselves and warns against unauthorized agents and intermediaries.

The tool asks the applicant to read each Webfile date from the original document. It does not infer document age from unrelated dates. A completed checklist is not evidence that a slot is available or that an appointment has been booked. Check the linked FAQ for current requirements.

## Project structure

- `app.py` — Streamlit dashboard, PDF review and readiness checklist.
- `modules/pdf_reader.py` — in-memory PDF validation, page extraction and clear PDF errors.
- `modules/data_validator.py` — configurable label extraction, duplicate/conflict detection, and separate validation of Webfile and account-profile values.
- `modules/ocr_reader.py` — optional local OCR, page rendering limits, OCR dependency checks, and separate OCR text storage.
- `modules/data_export.py` — allowlisted JSON serialization of confirmed values only.
- `models/applicant.py` — separate `ApplicantWebfile`, `IVACAccountProfile`, and `ManualConfirmations` Pydantic models.
- `config/field_mapping.py` — recognized Webfile field labels.
- `config/readiness.py` — checklist limits and Webfile age calculation.
- `modules/browser.py` — optional visible manual browser launch only; not connected to the dashboard workflow.
- `modules/ivac_automation.py` — explicit safe-scope note for future work.
- `.streamlit/config.toml` — disables Streamlit usage statistics.
- `tests/` — PDF, field-validation, readiness, model-separation, and dashboard startup tests.
- `requirements-ocr.txt` — optional Python wrapper and Pillow dependencies for OCR; the Tesseract executable is installed separately.

## Install

Python 3.9 or newer is supported by the current dependencies.

```bash
python3 -m venv .venv
source .venv/bin/activate      # macOS/Linux
# Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
```

The manual browser helper needs Chromium only if you explicitly use that later:

```bash
python -m playwright install chromium
```

## Optional local OCR on macOS

Environment inspection for this project found macOS on Apple Silicon, Homebrew and Pillow installed, but no `pytesseract` Python wrapper or `tesseract` executable. OCR has not been installed automatically. To enable it, activate the project virtual environment and install both the optional Python packages and local OCR engine:

```bash
python -m pip install -r requirements-ocr.txt
brew install tesseract
```

Restart Streamlit after installation. The app detects if either component is missing and displays the setup instructions. On a scanned page, choose installed OCR language data (English is selected when available) and explicitly click **Run local OCR**. Add other Tesseract language data through your local package manager if needed. The app OCRs only pages without selectable text, with bounded render resolution and a 50-page OCR run limit. It does not rewrite the PDF. Text recognition can be wrong, especially on low-quality scans; OCR fields are labeled and remain unverified until you confirm them.

Local OCR uses [Tesseract's macOS/Homebrew installation](https://tesseract-ocr.github.io/tessdoc/Installation.html) and [pytesseract](https://github.com/madmaze/pytesseract), a Python wrapper that invokes the local executable. Neither sends applicant documents to an online OCR service.

## Run the dashboard

```bash
streamlit run app.py
```

Open the local address Streamlit prints. Choose the applicant count, upload each original Webfile PDF, and compare all displayed values against the original documents. Enter portal profile details manually in the separate profile section. Read the Webfile date from each original document and use the checklist to record your own confirmations.

Each applicant card shows recognized and missing fields, source page excerpts, extraction method, a qualitative heuristic confidence label, and a checkbox for your verification. The confidence labels are not statistical probabilities. Similar values found more than once and conflicting values are flagged for review. Date values are displayed as found; date format validation accepts ISO or day-first forms, so verify every identity date against the PDF.

## Export reviewed data

Open **Optional JSON export of reviewed information**, read the sensitive-data warning, check its confirmation box, then choose **Prepare reviewed applicant JSON**. The download button appears only after that explicit action. Only fields you marked as confirmed are included. The export includes their page references and extraction metadata, but not page text, source excerpts, or the original PDF. Account profile values are exported only if you separately confirm the profile review. The JSON is prepared in session memory for download and is not written to a server file by this app.

The app detects PDFs with no selectable text and identifies pages without text. OCR is optional and is not installed by the base setup. A PDF being readable or passing basic format checks does not prove its information is accurate or acceptable to IVAC. Password-protected PDFs are not unlocked by this app.

## Tests

```bash
pytest
```

Tests use synthetic PDFs and values, including multiple layouts, split-line labels, multipage and image-only pages, unavailable and simulated low-quality OCR, conflicting passport values, date interpretation, and export validation. OCR tests use a synthetic Tesseract stub; they do not require installing the OCR engine or access the official website.

## Privacy and limitations

Applicant documents and extracted information may remain in the current Streamlit session's memory until that session ends. Explicit exports are downloaded to your device only after confirmation. Do not use the app on a shared or untrusted computer. The app does not write uploads, extracted records, or activity logs to disk. The label matcher only recognizes configured Webfile labels in `config/field_mapping.py`; unfamiliar layouts need manual review. The checklist is preparation guidance, not an IVAC connection or booking status.
