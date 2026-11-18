# V3 Project Guidance

## 1. Product direction

- V3 is a local JavaScript/Node.js application using Playwright and a local dashboard.
- Support macOS and Windows.
- Keep applicant data on the applicant's device.
- No external AI, analytics, telemetry, cloud storage, or third-party document services.
- Preserve V2 until migration is explicitly approved.

## 2. Applicant documents

- Support one primary applicant PDF and up to three optional secondary applicant PDFs.
- Store documents in a private application-owned local directory outside the repository.
- Keep documents between sessions as requested by the applicant.
- Provide controls to replace and delete individual files and clear all local data.
- Apply restrictive filesystem permissions or platform-appropriate ACLs.
- Never commit applicant PDFs or private information.
- Do not extract, OCR, preview, log, or transmit document contents to third parties.
- Upload a selected PDF only when the applicant explicitly authorizes it, the visible browser is on the verified official IVAC HTTPS website, and current IVAC rules permit the action.
- If authorization or permission is uncertain, pause and request manual upload.

## 3. Browser automation

- Use Playwright with a visible Chromium browser.
- Restrict browser automation to the verified official IVAC HTTPS host.
- Login and OTP entry must always be manual.
- Never collect, store, enter, intercept, or log credentials or OTPs.
- Never bypass CAPTCHA, queues, rate limits, anti-bot protections, or other security controls.
- Never use hidden APIs, direct network requests, injected network calls, or alternative sessions to bypass portal behavior.
- Read only the visible page information necessary for the current workflow.
- Do not inspect cookies, authentication storage, authorization headers, CAPTCHA internals, or network request/response bodies.
- Allow the applicant to pause or stop automation at any time.

## 4. Supervised automation policy

V3 may use Playwright for applicant-authorized actions when permitted by current IVAC terms and website rules.

Permitted actions may include:
- Navigating appointment pages.
- Detecting workflow states.
- Uploading explicitly selected applicant documents.
- Detecting calendar dates.
- Selecting dates chronologically.
- Selecting the first available valid time slot.
- Detecting whether the portal advances to the next workflow step.

Keep the browser visible and provide clear workflow status.

The applicant must remain in control. Pause for manual authentication, security challenges, uncertain page states, and actions requiring human judgment.

## 5. Calendar monitoring restrictions

- Implement calendar detection and date-selection logic as separate, testable modules.
- Continuous monitoring, repeated date selection, automatic refreshes, and retry loops are allowed only when current IVAC rules explicitly permit the method and frequency.
- Do not assume that a 20-second interval is permitted.
- Make the interval configurable, with safe defaults based on verified published restrictions.
- If permission cannot be established, disable continuous monitoring and offer applicant-triggered availability checks on the currently visible page.
- Never bypass rate limits, queues, anti-bot controls, or access restrictions.
- A successful click is not proof of availability.
- Verify actual page progression before reporting success.
- Prevent duplicate or uncertain booking actions.

## 6. Payment and booking safety

- Never automate payment.
- Never collect or store payment credentials.
- Never submit final booking confirmation or payment.
- Detect the payment page or payment options and immediately stop automation.
- Keep the browser open and notify the applicant.
- Require the applicant to perform all remaining payment and confirmation actions manually.

## 7. Session and error management

- Detect session expiration.
- Pause and ask the applicant to log in manually.
- Resume only after verifying the authenticated state and workflow position.
- Allow a maximum of three recovery attempts for recoverable browser errors.
- Do not blindly repeat actions that could create duplicate bookings.
- Pause when the result of an action is uncertain, a security challenge appears, or the page is unrecognized.
- Notify the applicant when intervention is required.

## 8. Privacy and logging

- Keep logs local.
- Do not log document contents, credentials, OTPs, payment details, or sensitive applicant information.
- Keep browser profiles and session data outside version control.
- Add appropriate `.gitignore` rules during the approved migration.

## 9. Architecture and testing

- Keep browser, automation, calendar, documents, notifications, storage, and dashboard modules separate.
- Do not use placeholder functions that claim to implement unverified portal behavior.
- Use synthetic fixtures and mocked pages for tests.
- Never run automated tests against the live IVAC portal or attempt real bookings or payments.
- Preserve existing V2 tests and functionality until migration is explicitly approved.

## 10. Migration approval

Changing these instructions does not itself authorize a code migration.

Do not delete the V2 Python application, replace its tests, or change dependencies until the user explicitly approves the V2-to-V3 migration.
