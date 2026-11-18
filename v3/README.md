# Auto Appointment Tracker V3 — foundation

This directory is an isolated V3 development area. The existing Python/Streamlit V2 remains untouched and runnable.

## Current scope

- Node.js 20+ foundation using built-in modules only.
- Local synthetic mock portal at `http://127.0.0.1:4173`.
- Mock-only scenarios for manual login handoff, appointment dates, session expiry, unexpected errors, and payment-stop behavior.
- Automated tests use only the local mock server. No test visits the real IVAC website.
- No applicant documents, credentials, OTPs, browser profiles, or portal data are stored by this mock.

## Run the mock

```bash
cd v3
npm run start:mock
```

Open `http://127.0.0.1:4173` in a browser. This is a synthetic training/test page, not IVAC and not a booking service.

## Run tests

```bash
cd v3
npm test
```

## Safety and next steps

The mock server is deliberately not connected to the live IVAC portal. A real portal adapter is blocked until the current official rules, permitted actions, and permitted request frequency are established. Continuous polling, date cycling, automated slot selection, and automated upload remain disabled. Login, OTP, CAPTCHA, queue/security challenges, final booking submission, and payment remain manual or prohibited as defined in the repository-level `AGENTS.md`.

Next implementation phases:
1. Define the V3 local application shell and persistent private document manager.
2. Implement a tested workflow state machine against the mock only.
3. Implement mock-only browser adapter and dashboard controls.
4. Evaluate whether any narrowly scoped real-site interaction is explicitly permitted by current IVAC rules before designing a real adapter.
5. Only after equivalent V3 tests and a migration review, consider retiring V2.
