# Project guidance

## Repository structure
- The existing V2 application is the known working baseline. Do not delete, rewrite, or move V2 files until V3 has equivalent verified functionality and a reviewed migration plan.
- Build V3 in the isolated `v3/` directory. Keep V2 runnable while V3 is developed.
- Use JavaScript on a supported Node.js LTS release for V3. Keep the mock portal, mock adapter, and real IVAC adapter strictly separated.
- Never claim live IVAC compatibility until the current official portal has been inspected lawfully and the adapter has been tested without submitting a real booking.

## User data and privacy
- Keep applicant documents and metadata on the user's device in a private application-data directory outside the repository.
- Persist documents between app restarts as requested; delete them only on explicit user action or a clearly documented retention policy. Never put applicant files, real identifiers, credentials, OTPs, cookies, browser profiles, or session tokens in Git.
- Do not parse, OCR, preview, log, transmit, or send applicant document contents to external services. Validate only file type, size, and basic PDF signature unless the user explicitly approves a different local-only validation.
- Do not add external AI, analytics, telemetry, cloud storage, or third-party document processing.

## Browser and portal safety
- Use a visible browser. The applicant must perform login, OTP, CAPTCHA, queues, and any security challenge personally.
- Supervised automation may interact only with visible, ordinary portal controls and only where current official IVAC rules and technical restrictions explicitly permit the specific action and its frequency.
- Continuous polling, date cycling, automatic slot selection, and automated document upload are disabled by default. Do not implement or enable them until the current official rules explicitly permit the exact behavior and frequency. Never evade rate limits or anti-bot controls.
- Do not bypass CAPTCHA, OTP, login, queues, rate limits, access controls, or anti-bot protections. Do not use hidden APIs, direct network calls, injected authentication state, or undocumented endpoints to control the portal.
- Never inspect or export cookies, local/session storage, authorization headers, hidden authentication fields, CAPTCHA internals, or network request/response bodies.
- Verify the official HTTPS hostname before any portal interaction. Do not navigate to lookalike or third-party hosts.
- Require explicit user authorization before uploading any applicant document to IVAC. Show the applicant and filename and ask for confirmation before each upload.
- Never submit a booking, final confirmation, or payment. If a payment page or payment option is detected, immediately stop automation, leave the browser open, and notify the user. Do not click payment controls.
- Avoid blind retries. On ambiguous state, unexpected dialogs, session expiry, or uncertain action result, pause and ask the user to resolve it. Limit recovery attempts to three safe, non-submitting attempts, then stop.
- The user can pause or stop the automation at any time. Stop must close or safely detach from the automation without deleting persisted applicant documents.

## Testing and delivery
- Use synthetic documents and a local mock IVAC portal only. Never run automated tests, load tests, or exploratory automation against the live IVAC site.
- Mock scenarios must cover login handoff, authenticated state, document upload simulation, no dates, available dates, date updates, session expiry, unexpected dialogs/errors, and payment-page stop behavior.
- Keep mock code and test fixtures separate from the real IVAC adapter.
- Run all available tests and builds before claiming a change is verified. If execution is unavailable, state that clearly and do not claim tests passed.
- Do not commit or push secrets, real applicant data, or generated user documents.
