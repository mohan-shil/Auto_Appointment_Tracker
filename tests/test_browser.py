import pytest

from modules.browser import BrowserLaunchError, IVAC_URL, open_official_site, validate_ivac_url
from modules.ivac_automation import confirmed_applicant_summary


class FakePage:
    def __init__(self, goto_error=None):
        self.goto_error = goto_error
        self.visited = []
        self.closed = False

    def goto(self, url, **kwargs):
        if self.goto_error:
            raise self.goto_error
        self.visited.append((url, kwargs))

    def is_closed(self):
        return self.closed


class FakeBrowser:
    def __init__(self, page=None):
        self.page = page or FakePage()
        self.closed = 0

    def new_page(self):
        return self.page

    def close(self):
        self.closed += 1
        self.page.closed = True


class FakeChromium:
    def __init__(self, browser=None, launch_error=None):
        self.browser = browser or FakeBrowser()
        self.launch_error = launch_error
        self.launch_options = []

    def launch(self, **kwargs):
        self.launch_options.append(kwargs)
        if self.launch_error:
            raise self.launch_error
        return self.browser


class FakePlaywright:
    def __init__(self, chromium):
        self.chromium = chromium
        self.stopped = 0

    def stop(self):
        self.stopped += 1


class FakeFactory:
    def __init__(self, playwright):
        self.playwright = playwright
        self.starts = 0

    def __call__(self):
        return self

    def start(self):
        self.starts += 1
        return self.playwright


def make_factory(*, launch_error=None, page=None):
    browser = FakeBrowser(page)
    playwright = FakePlaywright(FakeChromium(browser, launch_error))
    factory = FakeFactory(playwright)
    return factory, playwright, browser


def test_browser_initialization_opens_only_official_site_visibly():
    factory, playwright, browser = make_factory()
    session = open_official_site(playwright_factory=factory)
    assert session.page.visited == [(IVAC_URL, {"wait_until": "domcontentloaded", "timeout": 30000})]
    assert playwright.chromium.launch_options == [{"headless": False}]
    assert not session.closed
    assert browser.closed == 0
    assert session.is_open


def test_browser_shutdown_is_idempotent_and_stops_driver():
    factory, playwright, browser = make_factory()
    session = open_official_site(playwright_factory=factory)
    session.close()
    session.close()
    assert browser.closed == 1
    assert playwright.stopped == 1
    assert session.closed
    assert not session.is_open


def test_connection_error_cleans_up_browser_and_playwright():
    page = FakePage(goto_error=OSError("network unavailable"))
    factory, playwright, browser = make_factory(page=page)
    with pytest.raises(BrowserLaunchError, match="internet connection"):
        open_official_site(playwright_factory=factory)
    assert browser.closed == 1
    assert playwright.stopped == 1


def test_missing_chromium_has_install_guidance_and_stops_driver():
    factory, playwright, browser = make_factory(launch_error=RuntimeError("Executable doesn't exist at path"))
    with pytest.raises(BrowserLaunchError, match="playwright install chromium"):
        open_official_site(playwright_factory=factory)
    assert browser.closed == 0
    assert playwright.stopped == 1


@pytest.mark.parametrize("url", [
    "http://appointment.ivacbd.com/",
    "https://example.com/",
    "https://user:secret@appointment.ivacbd.com/",
    "https://appointment.ivacbd.com/other",
    "https://appointment.ivacbd.com/?token=secret",
])
def test_invalid_or_nonofficial_urls_are_rejected_before_playwright_starts(url):
    factory, _, _ = make_factory()
    with pytest.raises(ValueError):
        open_official_site(url, playwright_factory=factory)
    assert factory.starts == 0


def test_official_url_is_canonicalized():
    assert validate_ivac_url("https://appointment.ivacbd.com") == IVAC_URL


def test_applicant_summary_includes_only_confirmed_validated_allowlisted_fields():
    summary = confirmed_applicant_summary([{
        "applicant": "Primary applicant",
        "fields": [
            {"key": "full_name", "value": "Fictional Person", "verification_status": "Confirmed by applicant", "validation_passed": True},
            {"key": "passport_number", "value": "ZZ123456", "verification_status": "Confirmed by applicant", "validation_passed": False},
            {"key": "webfile_number", "value": "WF123456", "verification_status": "Needs verification", "validation_passed": True},
            {"key": "visa_application_reference", "value": "REF123456", "verification_status": "Confirmed by applicant", "validation_passed": True},
            {"key": "email", "value": "person@example.test", "verification_status": "Confirmed by applicant", "validation_passed": True},
        ],
    }])
    assert summary == [{
        "applicant": "Primary applicant",
        "status": "Some reviewed fields missing",
        "fields": {
            "full_name": {"label": "Applicant name", "value": "Fictional Person"},
            "visa_application_reference": {"label": "Visa reference", "value": "REF123456"},
        },
    }]
