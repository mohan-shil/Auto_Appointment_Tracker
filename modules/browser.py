"""Safe browser preparation; no automatic form interaction is implemented."""

IVAC_URL = "https://appointment.ivacbd.com"


def open_official_site():
    """Launch a visible browser at IVAC for the user to continue manually."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright is not installed. Install requirements first.") from exc
    playwright = sync_playwright().start()
    browser = None
    try:
        browser = playwright.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(IVAC_URL, wait_until="domcontentloaded", timeout=30000)
    except Exception as exc:
        if browser is not None:
            browser.close()
        playwright.stop()
        raise RuntimeError("Could not open the official IVAC site in Chromium. Confirm internet access and install the Playwright browser with `python -m playwright install chromium`.") from exc
    return playwright, browser, page
