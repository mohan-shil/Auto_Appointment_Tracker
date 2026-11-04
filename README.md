# Auto Appointment Tracker V2

A local Streamlit desktop-style helper for managing original IVAC Webfile PDFs and opening the official appointment portal in a visible Chromium window. Applicants perform all portal actions themselves.

## What V2 does

- Provides exactly four applicant slots: one required primary applicant and three optional secondary applicants.
- Accepts PDF files only, displays the original filename and size, supports replacement and secondary-slot removal, and offers **Clear All Files**.
- Copies the uploaded PDF bytes unchanged into a private temporary directory outside the repository. The app does not read, preview, or interpret PDF contents, create identity records, log applicant details, or transmit documents.
- Opens the official IVAC appointment website in a separate visible Chromium browser after the primary PDF is present.
- Shows manual workflow steps and a progress indicator. Progress is based only on applicant-selected checkboxes and is not a portal status.
- Removes its temporary files on normal process shutdown and cleans abandoned sessions when the app starts again.

The application does not automate login, credentials, OTP, CAPTCHA, uploads to IVAC, forms, date/centre selection, appointment polling, booking submission, or payment. It does not dismiss unknown portal pop-ups. Review and handle all portal content yourself.

## Requirements

- macOS 12 or newer, or another supported desktop operating system.
- Python 3.9 or newer.
- Chromium installed for Playwright.

## Install on macOS

From the project folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m playwright install chromium
```

The browser installation command is needed once per Playwright environment. If Chromium is missing later, the dashboard displays the same command.

## Run

```bash
source .venv/bin/activate
streamlit run app.py
```

Open the local address shown by Streamlit. Use **Applicant Documents** to upload the primary Webfile PDF. Add secondary slots only when needed. Re-select a file to replace it; use the secondary applicant's remove control to remove that applicant and file. **Clear All Files** removes saved PDFs and ends the current temporary storage session; the app creates a fresh empty storage session on the next rerun.

After the primary PDF is present, choose **Open Browser**. A separate visible Chromium window opens at <https://appointment.ivacbd.com/>. Sign in yourself and complete every website step manually. Use the **Appointment Workflow** checkboxes to track your own progress, then choose **Close Browser** when finished.

## Temporary storage and cleanup

Files are stored under an application-specific directory inside the operating system's temporary folder, outside the Git checkout. Each app session uses a random directory. On POSIX systems, the cache/session directories use mode `0700` and PDF files use mode `0600`. PDF bytes are copied as-is; filenames appear only in the local dashboard and are not used as on-disk paths. The app stores no credentials, OTPs, or account data.

The app does not claim to detect dashboard-tab closure immediately. **Clear All Files** removes PDFs and the current storage directory on request. A normal Streamlit process shutdown removes session directories owned by that process; the next app startup removes abandoned sessions whose owner process is no longer running. A crash or forced termination may leave temporary PDFs until startup cleanup runs. Removal unlinks files and is not a forensic secure-erase guarantee.

## Privacy and security

- All file management is local. PDFs are not sent to external APIs or uploaded by this app to IVAC.
- The browser opens only the official HTTPS host. The applicant interacts with the site directly in visible Chromium.
- Credentials and OTPs must be entered only by the applicant on the official website and are never collected by this application.
- Do not use this tool on a shared or untrusted computer. Use the operating-system account protections and clear files when finished.
- The official FAQ advises applicants to perform booking themselves and warns against unauthorized agents. Follow current instructions on the [IVAC portal](https://appointment.ivacbd.com/) and [official FAQ](https://www.ivacbd.com/faq/appointment-management-system).

## IVAC workflow notes

The public portal's observed landing notice states the booking hours and requires original Webfiles no older than 30 days. The published FAQ describes sign-up with mobile and email OTP, primary then optional secondary Webfile upload, eligible centre selection, an available future date, payment, and invoice confirmation. The centre/date screen order may differ from the dashboard's reminder order; follow the live portal. Neither the app nor its checklist checks appointment availability.

See [the detailed observation and guidance notes](docs/IVAC_BROWSER_GUIDE.md) for verified public-page observations, FAQ guidance, and interface assumptions.

## Project structure

- `app.py` — four-slot document manager, browser controls, workflow checklist, and storage status.
- `modules/document_store.py` — temporary session directories, PDF-only checks, byte-preserving writes, permissions, and cleanup.
- `modules/browser.py` — official-URL validation, visible Playwright Chromium lifecycle, and shutdown cleanup.
- `modules/workflow.py` — static applicant-controlled workflow labels.
- `tests/` — document storage, browser lifecycle, URL validation, and Streamlit state/UI tests.

The file manager checks the `.pdf` filename extension and a PDF header signature. It does not open or validate the document structure.

## Tests

```bash
source .venv/bin/activate
python -m pytest -v
```

Browser tests use mocks. Document tests use fictional synthetic PDF bytes. No automated booking or payment tests run against the IVAC portal.
