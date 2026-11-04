"""Visible, applicant-controlled browser launch for the official IVAC site."""

from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import urlsplit


IVAC_URL = "https://appointment.ivacbd.com/"


class BrowserLaunchError(RuntimeError):
    """A safe, user-displayable error while preparing the visible browser."""


def validate_ivac_url(url: str) -> str:
    """Accept only the official HTTPS appointment host and no embedded credentials."""
    if not isinstance(url, str):
        raise ValueError("The IVAC address must be a URL string.")
    try:
        parsed = urlsplit(url.strip())
        valid_port = parsed.port in (None, 443)
    except ValueError as exc:
        raise ValueError("The IVAC address is not a valid URL.") from exc
    if (
        parsed.scheme != "https"
        or parsed.hostname != "appointment.ivacbd.com"
        or parsed.username is not None
        or parsed.password is not None
        or not valid_port
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("For safety, the browser assistant only opens https://appointment.ivacbd.com.")
    return IVAC_URL


@dataclass
class BrowserSession:
    """Handles owned by the dashboard so the applicant can close the browser."""

    playwright: Any
    browser: Any
    page: Any
    closed: bool = False

    @property
    def is_open(self) -> bool:
        """Report whether the visible page is still open when the driver supports it."""
        if self.closed:
            return False
        try:
            return not self.page.is_closed()
        except AttributeError:
            return True

    def close(self) -> None:
        """Close Chromium and stop the Playwright driver, including partial cleanup."""
        if self.closed:
            return
        self.closed = True
        try:
            self.browser.close()
        finally:
            self.playwright.stop()


def open_official_site(url: str = IVAC_URL, playwright_factory: Optional[Any] = None) -> BrowserSession:
    """Open the official IVAC page in visible Chromium without interacting with it."""
    safe_url = validate_ivac_url(url)
    if playwright_factory is None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise BrowserLaunchError("Playwright is not installed. Install requirements, then restart the app.") from exc
        playwright_factory = sync_playwright

    playwright = None
    browser = None
    try:
        playwright = playwright_factory().start()
        browser = playwright.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(safe_url, wait_until="domcontentloaded", timeout=30000)
        return BrowserSession(playwright, browser, page)
    except Exception as exc:
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass
        if playwright is not None:
            try:
                playwright.stop()
            except Exception:
                pass
        detail = str(exc).casefold()
        if "executable doesn't exist" in detail or "please run" in detail and "install" in detail:
            message = "Chromium is not installed. Run `python -m playwright install chromium`, then try again."
        elif "playwright is not installed" in detail or "no module named" in detail:
            message = "Playwright is not installed. Install requirements, then restart the app."
        else:
            message = "Could not connect to the IVAC site in visible Chromium. Check your internet connection and try again."
        raise BrowserLaunchError(message) from exc
