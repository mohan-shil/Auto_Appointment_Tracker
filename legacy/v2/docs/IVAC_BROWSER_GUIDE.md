# IVAC portal observation and applicant workflow

**Observation date:** 4 November 2026

**Portal:** <https://appointment.ivacbd.com/>

**Published reference:** [IVAC Appointment Management System FAQ](https://www.ivacbd.com/faq/appointment-management-system)

This note distinguishes the page seen without authentication from steps described by the official FAQ. No authenticated page, booking, appointment availability, or payment was tested.

## Verified public-page observation

Opening the public portal without signing in displayed an **IMPORTANT NOTICE**. Its visible text stated:

- Booking hours are Sunday to Thursday, noon to 5:00 PM, and Saturday, 10:00 AM to noon.
- Uploaded Webfiles must be original visa application PDFs and no older than 30 days; altered, edited, or tampered files will be rejected.

No sign-in form, account page, booking form, appointment calendar, centre selector, payment page, or invoice was visible during this observation.

## Published FAQ guidance

The FAQ describes mobile and email verification during sign-up and lists mobile number, email, given name, surname, passport number, NID/citizenship number, and date of birth as profile details. It says these details should match the primary Webfile. It also advises applicants to complete the process themselves and warns against unauthorized agents and intermediaries.

The FAQ's described booking sequence is:

1. Sign in and choose **Book Your Appointment**.
2. Upload the primary Webfile, followed by secondary Webfiles where applicable. One account can include one primary and up to three secondary applicants.
3. The portal extracts the Mission Centre from the primary Webfile and presents eligible IVAC centres; the applicant selects an available centre.
4. The portal then displays available future dates in a calendar. Dates depend on slot availability; same-day booking is not offered. The FAQ describes a two-week appointment cycle and a 15-minute booking session.
5. The applicant reviews details, proceeds to payment, pays manually, and confirms the portal's result. The FAQ says an invoice is generated when an appointment is successfully confirmed.

Availability varies and is not checked by this application. The current portal instructions take precedence if a live screen differs from the FAQ or this description.

## What this application does

The app can copy original uploaded PDF bytes to a private temporary local session folder and open a separate visible Chromium window at the official HTTPS portal. It does not inspect PDF content or send PDFs to the website. It does not automatically dismiss pop-ups or interact with the portal. The applicant controls sign-in, OTP/CAPTCHA, uploads, all selections, submissions, booking confirmation, and payment.

The dashboard workflow checklist is a reminder sequence, not a claim about the portal's actual screen order or state. Its progress only reflects boxes the applicant manually checks. A browser status means only that the app's Chromium page is open; it does not mean the applicant is signed in or has a booking.
