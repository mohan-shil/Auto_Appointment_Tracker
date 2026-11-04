# IVAC Browser Assistant: workflow notes

**Updated:** 4 November 2026

**Official portal:** <https://appointment.ivacbd.com/>

**Published guidance:** [IVAC Appointment Management System FAQ](https://www.ivacbd.com/faq/appointment-management-system)

This guide separates what was visible on the public portal, what the published FAQ says, and what this application assumes for its user interface. It is preparation guidance only. Website screens can change, and booking availability is not checked by this application.

## Live public-page observation

On 4 November 2026, opening the public appointment portal without signing in displayed an **IMPORTANT NOTICE**. The visible notice said:

- Booking is open Sunday–Thursday, 12:00 noon–5:00 PM, and Saturday, 10:00 AM–12:00 noon.
- Uploaded Webfiles must be original visa-application PDFs and no older than 30 days; altered, edited, or tampered files will be rejected.

No sign-in screen, account page, booking form, centre selector, appointment calendar, payment page, or invoice was visible in this public-page observation. Those screens have not been explored with an authenticated account.

## Published FAQ guidance (not directly observed in the public page)

The linked FAQ describes these requirements and steps:

1. **Account registration:** Sign-up uses mobile number, email, given name, surname, passport number, NID or citizenship number, and date of birth. The FAQ says these details should match the primary Webfile; mobile and email require OTP verification. Applicants should do this themselves and keep credentials and OTPs private.
2. **Applicant group:** One account can include one primary applicant and up to three secondary applicants (four Webfiles maximum).
3. **Documents:** Choose **Book Your Appointment**, upload the primary Webfile first, then secondary Webfiles if applicable. The Webfiles should be valid and correspond to the included applicants. The FAQ also says the Webfile must be no older than 30 days and must not be altered.
4. **Centre selection:** After primary Webfile upload, the system extracts its Mission Centre and presents eligible IVAC centre options. The applicant chooses an available centre.
5. **Appointment selection:** The FAQ describes an available-date calendar after centre selection. Applicants may choose an available future date in the open two-week cycle; same-day appointments are not offered. Availability depends on mission and visa category. This application does not check or imply that a slot exists.
6. **Payment and confirmation:** The FAQ says the portal proceeds to payment after centre and date selection. The applicant completes payment. The FAQ describes successful payment as the booking confirmation point and says an invoice is generated for a confirmed appointment; the applicant should download and retain it. The applicant must verify the portal's actual result.

The FAQ also says the booking session has a 15-minute time limit after starting **Book Your Appointment**. Treat the live portal's instructions as authoritative if they differ. This app does not start that session or reserve a slot.

## Application assistance and manual actions

The **IVAC Browser Assistant** opens a visible Chromium window to the official HTTPS host. It displays a compact reference panel containing only applicant fields that are both confirmed by the applicant and validation-passed. It never enters those values into the website.

The applicant personally performs every portal action: registration, login, OTP and CAPTCHA, document upload, form entry, centre/date selection, submission, booking confirmation, and payment. The application does not collect credentials, issue hidden requests, inspect an authenticated workflow, poll for availability, reserve slots, or modify Webfiles. Closing the assistant closes the Chromium session started by the app.

## UI assumptions

- The browser-assistant status reports whether this app's Chromium session was launched; it is not a portal login or booking status.
- Checklist completion is applicant-entered preparation information, not proof that a portal action succeeded.
- Website availability and form requirements may change. Follow the live portal and current official FAQ, and stop if their instructions differ from this guide.
