# Auto Appointment Tracker V2

A local Streamlit desktop-style helper for managing original IVAC Webfile PDFs and opening the official appointment portal in visible Google Chrome. Applicants perform all portal actions themselves.

## What V2 does

- Provides exactly four applicant slots: one required primary applicant and three optional secondary applicants.
- Accepts PDF files only, displays the original filename and size, supports replacement and secondary-slot removal, and offers **Clear All Files**.
- Copies the uploaded PDF bytes unchanged into a private temporary directory outside the repository. The app does not read, preview, or interpret PDF contents, create identity records, log applicant details, or transmit documents.
- Opens the official IVAC appointment website in visible Google Chrome using an existing local Chrome profile after the primary PDF is present.
- Shows manual workflow steps and a progress indicator. Progress is based only on applicant-selected checkboxes and is not a portal status.
- Removes its temporary files on normal process shutdown and cleans abandoned sessions when the app starts again.

The application does not automate login, credentials, OTP, CAPTCHA, uploads to IVAC, forms, date/centre selection, appointment polling, booking submission, or payment. It does not dismiss unknown portal pop-ups. Review and handle all portal content yourself.

## Requirements

- macOS 12 or newer, or another supported desktop operating system.
- Python 3.9 or newer.
- Google Chrome installed and an existing profile configured with any extensions you want to use.
- Close all Google Chrome windows before opening that profile from the app.

## Install on macOS

From the project folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

Open Google Chrome once and sign in or enable your VPN extension in the profile you want to use. The app launches installed Google Chrome with that existing profile; it does not use Playwright's temporary test profile.

## Run

```bash
source .venv/bin/activate
streamlit run app.py
```

Open the local address shown by Streamlit. Use **Applicant Documents** to upload the primary Webfile PDF. Add secondary slots only when needed. Re-select a file to replace it; use the secondary applicant's remove control to remove that applicant and file. **Clear All Files** removes saved PDFs and ends the current temporary storage session; the app creates a fresh empty storage session on the next rerun.

After the primary PDF is present, choose the Chrome profile where your VPN extension is enabled, then choose **Open Browser**. Close all other Chrome windows first because Chrome cannot safely share one profile between running processes. The **IVAC link** field defaults to <https://appointment.ivacbd.com/> and lets you change its path if the portal uses a different page; links are restricted to the official appointment host. Sign in yourself and complete every website step manually. Use the **Appointment Workflow** checkboxes to track your own progress, then choose **Close Browser** when finished.

## IVAC Portal Inspection Mode

An authorized tester can use the app to export a privacy-minimized description of pages they can access. The inspection section works only with the visible Chrome session opened by this dashboard. The tester manually navigates; **Capture Current Page Structure** only reads visible semantic labels and structure. It never clicks, fills, submits, or changes portal controls.

### Bangladesh tester steps

1. Pull the latest code from GitHub: `git pull origin main`.
2. Install/update dependencies and make sure Google Chrome and the desired profile are configured, then start the app with `streamlit run app.py`.
3. Upload the required primary Webfile PDF and choose **Open Browser**.
4. In the visible Chrome window, open the official site and navigate manually. Enter credentials and OTPs only on the official IVAC site; do not send them to the developer or include them in a report. Only visit pages you are authorized to access. Do not complete a real booking or payment for inspection.
5. In the dashboard, select the corresponding page name and choose **Capture Current Page Structure**. Repeat for each authorized page. A page is counted only after the app verifies that visible structure was returned.
6. Choose **Export Inspection Report**. By default, the JSON file is saved under `~/Documents/IVAC-Inspection/` (macOS/Linux) or the equivalent Documents folder on Windows. The dashboard displays the exact path.
7. Review the JSON locally, then send/attach that sanitized inspection report to the developer through an agreed channel. Do not send PDFs, credentials, OTPs, screenshots, or browser data.

The report contains a generic page title when recognized, official hostname, sanitized pathname, visible headings, buttons, links, form labels and control metadata, dropdown options, dialogs, navigation labels, and a boolean CAPTCHA-presence indicator. Query strings and fragments are removed. Unknown or potentially personal text is replaced with `[omitted]`; password and hidden controls are excluded. It does not read input values, page HTML/body text, cookies, local/session storage, network traffic, authorization data, screenshots, or CAPTCHA internals. Reports are written with restrictive local permissions and outside the repository. Use **Clear Inspection Reports** to remove captured reports and reports exported by the current app session.

Inspection reports describe only the pages the tester actually captured; they are not a claim that an inaccessible or authenticated page was observed. They may omit unfamiliar interface wording by design. Never use a report as proof of slot availability.

## Temporary storage and cleanup

Files are stored under an application-specific directory inside the operating system's temporary folder, outside the Git checkout. Each app session uses a random directory. On POSIX systems, the cache/session directories use mode `0700` and PDF files use mode `0600`. PDF bytes are copied as-is; filenames appear only in the local dashboard and are not used as on-disk paths. The app stores no credentials, OTPs, or account data.

The app does not claim to detect dashboard-tab closure immediately. **Clear All Files** removes PDFs and the current storage directory on request. A normal Streamlit process shutdown removes session directories owned by that process; the next app startup removes abandoned sessions whose owner process is no longer running. A crash or forced termination may leave temporary PDFs until startup cleanup runs. Removal unlinks files and is not a forensic secure-erase guarantee.

## Privacy and security

- All file management is local. PDFs are not sent to external APIs or uploaded by this app to IVAC.
- The browser opens only the official HTTPS host. The applicant interacts with the site directly in visible Google Chrome. Profile data and extensions stay local; the app does not read them.
- Credentials and OTPs must be entered only by the applicant on the official website and are never collected by this application.
- Do not use this tool on a shared or untrusted computer. Use the operating-system account protections and clear files when finished.
- The official FAQ advises applicants to perform booking themselves and warns against unauthorized agents. Follow current instructions on the [IVAC portal](https://appointment.ivacbd.com/) and [official FAQ](https://www.ivacbd.com/faq/appointment-management-system).

## IVAC workflow notes

The public portal's observed landing notice states the booking hours and requires original Webfiles no older than 30 days. The published FAQ describes sign-up with mobile and email OTP, primary then optional secondary Webfile upload, eligible centre selection, an available future date, payment, and invoice confirmation. The centre/date screen order may differ from the dashboard's reminder order; follow the live portal. Neither the app nor its checklist checks appointment availability.

See [the detailed observation and guidance notes](docs/IVAC_BROWSER_GUIDE.md) for verified public-page observations, FAQ guidance, and interface assumptions.

## Project structure

- `app.py` — four-slot document manager, browser controls, workflow checklist, inspection interface, and storage status.
- `modules/document_store.py` — temporary session directories, PDF-only checks, byte-preserving writes, permissions, and cleanup.
- `modules/browser.py` — official-URL validation, existing Chrome profile selection, visible browser lifecycle, and shutdown cleanup.
- `modules/portal_inspector.py` — read-only visible page structure extraction and private JSON export.
- `modules/workflow.py` — static applicant-controlled workflow labels.
- `tests/` — document storage, browser lifecycle, URL validation, synthetic inspection fixtures, and Streamlit state/UI tests.

The file manager checks the `.pdf` filename extension and a PDF header signature. It does not open or validate the document structure.

## Tests

```bash
source .venv/bin/activate
python -m pytest -v
```

Browser tests use mocks and a synthetic local HTML fixture. Document tests use fictional synthetic PDF bytes. No automated booking, payment, or inspection tests run against the live IVAC portal.
