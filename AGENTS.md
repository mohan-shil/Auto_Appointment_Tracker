# Project guidance

- Keep applicant information local; do not add external AI or telemetry.
- Never automate CAPTCHA, OTP, login, booking submission, payment, or slot polling.
- Do not extract, preview, log, or transmit applicant document contents.
- Store uploaded PDFs only in the explicitly requested private temporary session directory outside the repository; remove them on clear, normal process shutdown, or stale-session cleanup.
- Never commit applicant PDFs, private information, passwords, or OTPs.
- Keep every IVAC website interaction under the applicant's direct control.
