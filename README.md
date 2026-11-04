# Auto_Appointment_Tracker — Auto Appointment Tracker

A local applicant-assistance tool for reviewing IVAC Webfiles and preparing for the official appointment process. It does not log in, solve CAPTCHA, handle OTP, submit forms, poll for slots, reserve appointments, or make payments. Applicants must perform every IVAC website action themselves.

## What it does

- Accepts up to four applicant Webfile PDFs (one primary and up to three secondary applicants), each up to 15 MB.
- Extracts selectable text locally with PyMuPDF and retains page numbers.
- Flags empty, unreadable, password-protected, scanned/no-text, duplicate, and conflicting data for review. It never guesses or silently corrects identity details.
- Separates Webfile information from account-profile information. Mobile, email, NID/citizenship number and other profile details are entered manually; they are not inferred from Webfiles.
- Provides an applicant list, missing-information indicators, 30-day Webfile date check, and a manually completed preparation checklist.
- Processes files and values in the Streamlit session only; this project does not write them to disk or send applicant data to an external AI service. Streamlit usage statistics are disabled in `.streamlit/config.toml`.

## IVAC FAQ guidance

The checklist reflects the [official IVAC Appointment Management System FAQ](https://www.ivacbd.com/faq/appointment-management-system): a Webfile must be no older than 30 days; one account can include at most four applicants (one primary and up to three secondary); applicants select an eligible IVAC centre and an available future date; booking is confirmed after successful payment and an invoice is generated. The FAQ advises applicants to sign up and book themselves and warns against unauthorized agents and intermediaries.

The tool asks the applicant to read each Webfile date from the original document. It does not infer document age from unrelated dates. A completed checklist is not evidence that a slot is available or that an appointment has been booked. Check the linked FAQ for current requirements.

## Project structure

- `app.py` — Streamlit dashboard, PDF review and readiness checklist.
- `modules/pdf_reader.py` — in-memory PDF validation, page extraction and clear PDF errors.
- `modules/data_validator.py` — configurable label extraction, duplicate/conflict detection, and separate validation of Webfile and account-profile values.
- `models/applicant.py` — separate `ApplicantWebfile`, `IVACAccountProfile`, and `ManualConfirmations` Pydantic models.
- `config/field_mapping.py` — recognized Webfile field labels.
- `config/readiness.py` — checklist limits and Webfile age calculation.
- `modules/browser.py` — optional visible manual browser launch only; not connected to the dashboard workflow.
- `modules/ivac_automation.py` — explicit safe-scope note for future work.
- `.streamlit/config.toml` — disables Streamlit usage statistics.
- `tests/` — PDF, field-validation, readiness, model-separation, and dashboard startup tests.

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

## Run the dashboard

```bash
streamlit run app.py
```

Open the local address Streamlit prints. Choose the applicant count, upload each original Webfile PDF, and compare all displayed values against the original documents. Enter portal profile details manually in the separate profile section. Read the Webfile date from each original document and use the checklist to record your own confirmations.

The app detects PDFs with no selectable text and identifies pages without text; OCR is not enabled. A PDF being readable or passing basic format checks does not prove its information is accurate or acceptable to IVAC. Password-protected PDFs are not unlocked by this app.

## Tests

```bash
pytest
```

Tests use synthetic PDFs, including multipage, no-text, empty, corrupt and password-protected examples. They do not access the official website.

## Privacy and limitations

Applicant documents and extracted information may remain in the current Streamlit session's memory until that session ends. Do not use the app on a shared or untrusted computer. The app does not create activity logs, exports, or persistent applicant records. The label matcher only recognizes configured same-line labels in `config/field_mapping.py`; unfamiliar layouts need manual review. The checklist is preparation guidance, not an IVAC connection or booking status.
