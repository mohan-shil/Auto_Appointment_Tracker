import pytest

from modules.browser import BrowserLaunchError, IVAC_URL, open_official_site, validate_ivac_url


class FakePage:
    def __init__(self, error=None):
        self.error = error
        self.visited = []
        self.closed = False

    def goto(self, url, **kwargs):
        if self.error:
            raise self.error
        self.visited.append((url, kwargs))

    def is_closed(self):
        return self.closed


class FakeBrowser:
    def __init__(self, page):
        self.page = page
        self.closed = 0

    def new_page(self):
        return self.page

    def close(self):
        self.closed += 1
        self.page.closed = True


class FakeChromium:
    def __init__(self, browser, launch_error=None):
        self.browser = browser
        self.launch_error = launch_error
        self.options = []

    def launch(self, **kwargs):
        self.options.append(kwargs)
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


def fake_factory(error=None, launch_error=None):
    page = FakePage(error)
    browser = FakeBrowser(page)
    chromium = FakeChromium(browser, launch_error)
    playwright = FakePlaywright(chromium)
    return FakeFactory(playwright), playwright, browser


def test_browser_initialization_launches_visible_chromium_at_official_url():
    factory, playwright, browser = fake_factory()
    session = open_official_site(playwright_factory=factory)
    assert session.page.visited == [(IVAC_URL, {"wait_until": "domcontentloaded", "timeout": 30000})]
    assert playwright.chromium.options == [{"headless": False}]
    assert session.is_open
    session.close()
    assert browser.closed == 1
    assert playwright.stopped == 1


def test_browser_shutdown_is_idempotent():
    factory, playwright, browser = fake_factory()
    session = open_official_site(playwright_factory=factory)
    session.close()
    session.close()
    assert browser.closed == 1
    assert playwright.stopped == 1
    assert not session.is_open


def test_connection_error_closes_partial_browser_and_playwright():
    factory, playwright, browser = fake_factory(error=OSError("network unavailable"))
    with pytest.raises(BrowserLaunchError, match="internet connection"):
        open_official_site(playwright_factory=factory)
    assert browser.closed == 1
    assert playwright.stopped == 1


def test_missing_chromium_reports_setup_command_and_cleans_playwright():
    factory, playwright, browser = fake_factory(launch_error=RuntimeError("Executable doesn't exist"))
    with pytest.raises(BrowserLaunchError, match="python -m playwright install chromium"):
        open_official_site(playwright_factory=factory)
    assert browser.closed == 0
    assert playwright.stopped == 1


@pytest.mark.parametrize("url", [
    "http://appointment.ivacbd.com/",
    "https://example.test/",
    "https://user:secret@appointment.ivacbd.com/",
    "https://appointment.ivacbd.com/path",
    "https://appointment.ivacbd.com/?token=secret",
])
def test_nonofficial_urls_are_rejected_before_browser_starts(url):
    factory, _, _ = fake_factory()
    with pytest.raises(ValueError):
        open_official_site(url, playwright_factory=factory)
    assert factory.starts == 0


def test_official_url_canonicalizes_to_root():
    assert validate_ivac_url("https://appointment.ivacbd.com") == IVAC_URL
