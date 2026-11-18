# Auto Appointment Tracker V3

V3 is a local Node.js dashboard with a visible Playwright browser, private local document storage, a testable workflow state machine, and a fully local Mock IVAC environment. Mock automation can exercise chronological date attempts and stops at the simulated payment stage. Real IVAC automation is intentionally disabled until current rules, permitted selectors, and rate limits are verified.

## What works

- Express dashboard bound only to `127.0.0.1`.
- Visible Chromium launch for the local mock or official IVAC landing page. Real login and OTP are manual.
- Four private local PDF slots with PDF-header and 15 MB checks, replacement/deletion, persistent local metadata in SQLite, and clear controls.
- Mock login/dashboard, Webfile upload screen, date calendar, time-slot simulation, changing calendar, session expiry, navigation failure, unexpected popup, and payment-stage simulation.
- Mock workflow controls, chronological date selection, attempt results, pause/resume/stop, bounded recovery handling, and payment stop.
- Local desktop notifications on pause/error/payment where the platform supports them.
- Sanitized, read-only inspection of visible page labels and structure only when on the official IVAC HTTPS origin. Unknown wording is omitted; values, hidden fields, cookies, storage, network data, and all CAPTCHA-related elements or metadata are excluded from inspection.

## macOS install and run

Install a current Node.js LTS release and Python only if you also want to run the preserved V2 tests. In Terminal:

```bash
npm ci
npx playwright install chromium
npm start
```

Open <http://127.0.0.1:4173> in your local browser. Choose **Mock IVAC**, then **Open visible browser**. The mock browser has synthetic login controls; use **Simulate manual login** there. No real credentials are accepted by the mock. For a full mock calendar run, save a synthetic or applicant PDF locally, choose a scenario and interval, start the workflow, and confirm mock login in the visible mock browser. The payment-stage screen is simulation-only and has no payment controls.

## Windows install and run

Install a current Node.js LTS release. In PowerShell from the project folder:

```powershell
npm ci
npx playwright install chromium
npm start
```

Open <http://127.0.0.1:4173>. Use the Mock IVAC mode for test workflows. The browser remains visible and applicant documents stay on the local computer.

## Applicant document storage

V3 stores PDFs and SQLite metadata outside the repository. The default location is:

- macOS: `~/Library/Application Support/AutoAppointmentTrackerV3/`
- Windows: `%LOCALAPPDATA%\AutoAppointmentTrackerV3\`
- Other systems: `$XDG_DATA_HOME/AutoAppointmentTrackerV3/` or `~/.local/share/AutoAppointmentTrackerV3/`

POSIX directories/files use restrictive modes where supported; Windows inherits the current user's local application-data ACL. Use the dashboard delete controls to remove documents. V3 does not parse, preview, OCR, or log PDF contents. Local files are persistent until deleted; they are not synced to cloud storage by the app.

## Mock scenarios

Use the Settings selector to test no dates, second date available, last date available, changing dates, session expiry, navigation failure, unexpected popup, and payment reached. The calendar engine deduplicates attempts within a cycle, refreshes newly displayed dates, sorts chronologically, and chooses the first valid mock time slot. The observation interval is configurable; the mock runner is bounded to two date cycles so a test cannot run indefinitely. Repeated attempts run only in the synthetic mock workflow.

## Real IVAC mode and supervised inspection

Choose **Supervised real IVAC** and open the visible browser to manually visit <https://appointment.ivacbd.com>. Login, OTP, CAPTCHA, uploads, and all consequential actions remain under applicant control. The **Start mock workflow** button is blocked in real mode. The inspection button reads a sanitized description of the visible page and performs no website action.

The live portal was unavailable during this implementation. No authenticated page or live selector was verified, so V3 does not claim real IVAC workflow automation and does not run real polling, date selection, booking, or upload automation. Before adding any such integration, verify current IVAC terms, authorized behavior, and rate/frequency limits. If permission cannot be established, use applicant-triggered inspection of the currently visible page only. Never bypass queues, CAPTCHA, anti-bot controls, or rate limits. V3 never submits final booking confirmation or automates payment.

## Tests

Run V3 unit and local Playwright integration tests:

```bash
npm test
```

Tests use local mock pages and synthetic PDFs only. They do not contact the live IVAC site.

The original V2 implementation and all 47 V2 tests are preserved under `legacy/v2/`. To run them, install its Python requirements in a virtual environment, activate it, and run:

```bash
python -m pip install -r legacy/v2/requirements.txt
npm run test:v2
```

## Project layout

- `src/server/` — loopback-only Express app and local SQLite metadata.
- `src/browser/` — Playwright lifecycle, mock page-state helper, and real-site read-only adapter.
- `src/automation/` — state machine and synthetic workflow runner.
- `src/calendar/` — date normalization, ordering, duplicate prevention, and time-slot choice.
- `src/documents/` — private persistent local PDF storage.
- `src/notifications/` — local desktop notifications.
- `public/` — dashboard and isolated synthetic mock pages.
- `tests/` — Vitest unit and local browser integration tests.
- `legacy/v2/` — preserved Python/Streamlit V2 app and its original tests.
