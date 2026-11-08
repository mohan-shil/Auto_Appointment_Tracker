import pytest

from modules.browser import BrowserLaunchError, IVAC_URL, open_official_site, validate_ivac_url


class FakePage:
    def __init__(self, error=None, stay_blank=False):
        self.error = error
        self.stay_blank = stay_blank
        self.url = "about:blank"
        self.visited = []
        self.closed = False

    def goto(self, url, **kwargs):
        if self.error:
            raise self.error
        self.visited.append((url, kwargs))
        if not self.stay_blank:
            self.url = url

    def is_closed(self):
        return self.closed


class FakeBrowser:
    def __init__(self, page):
        self.page = page
        self.closed = 0
        self.extra_pages = []

    @property
    def pages(self):
        return [self.page, *self.extra_pages]

    def new_page(self):
        page = FakePage()
        self.extra_pages.append(page)
        return page

    def close(self):
        self.closed += 1
        for page in self.pages:
            page.closed = True


class FakeChromium:
    def __init__(self, browser, launch_error=None):
        self.browser = browser
        self.launch_error = launch_error
        self.options = []

    def launch_persistent_context(self, **kwargs):
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


def configure_chrome(monkeypatch, tmp_path, profile_directory="Default"):
    profile_root = tmp_path / "Chrome User Data"
    (profile_root / profile_directory).mkdir(parents=True)
    monkeypatch.setattr("modules.browser.chrome_user_data_dir", lambda: profile_root)
    executable = tmp_path / "google-chrome"
    monkeypatch.setattr("modules.browser.find_chrome_executable", lambda: executable)
    return profile_root, executable


def test_browser_initialization_uses_existing_google_chrome_profile(monkeypatch, tmp_path):
    profile_root, executable = configure_chrome(monkeypatch, tmp_path)
    factory, playwright, browser = fake_factory()
    session = open_official_site(playwright_factory=factory)
    assert session.page.visited == [(IVAC_URL, {"wait_until": "commit", "timeout": 30000})]
    assert playwright.chromium.options == [{
        "user_data_dir": str(profile_root),
        "headless": False,
        "executable_path": str(executable),
        "args": ["--profile-directory=Default"],
    }]
    assert session.is_open
    session.close()
    assert browser.closed == 1
    assert playwright.stopped == 1


def test_browser_navigates_a_new_tab_when_existing_tab_is_not_blank(monkeypatch, tmp_path):
    configure_chrome(monkeypatch, tmp_path)
    factory, _, browser = fake_factory()
    browser.page.url = "https://example.test/"
    session = open_official_site(playwright_factory=factory)
    assert session.page is browser.extra_pages[0]
    assert session.page.visited == [(IVAC_URL, {"wait_until": "commit", "timeout": 30000})]
    session.close()


def test_browser_reports_if_navigation_remains_blank(monkeypatch, tmp_path):
    configure_chrome(monkeypatch, tmp_path)
    factory, playwright, browser = fake_factory()
    browser.page.stay_blank = True
    with pytest.raises(BrowserLaunchError, match="stayed on a blank page"):
        open_official_site(playwright_factory=factory)
    assert browser.closed == 1
    assert playwright.stopped == 1


def test_browser_shutdown_is_idempotent(monkeypatch, tmp_path):
    configure_chrome(monkeypatch, tmp_path)
    factory, playwright, browser = fake_factory()
    session = open_official_site(playwright_factory=factory)
    session.close()
    session.close()
    assert browser.closed == 1
    assert playwright.stopped == 1
    assert not session.is_open


def test_connection_error_closes_partial_browser_and_playwright(monkeypatch, tmp_path):
    configure_chrome(monkeypatch, tmp_path)
    factory, playwright, browser = fake_factory(error=OSError("network unavailable"))
    with pytest.raises(BrowserLaunchError, match="internet connection"):
        open_official_site(playwright_factory=factory)
    assert browser.closed == 1
    assert playwright.stopped == 1


def test_chrome_launch_error_cleans_playwright(monkeypatch, tmp_path):
    configure_chrome(monkeypatch, tmp_path)
    factory, playwright, browser = fake_factory(launch_error=RuntimeError("Executable doesn't exist"))
    with pytest.raises(BrowserLaunchError, match="Google Chrome could not be started"):
        open_official_site(playwright_factory=factory)
    assert browser.closed == 0
    assert playwright.stopped == 1


def test_missing_profile_is_reported_before_browser_starts(monkeypatch, tmp_path):
    profile_root = tmp_path / "Chrome User Data"
    profile_root.mkdir()
    monkeypatch.setattr("modules.browser.chrome_user_data_dir", lambda: profile_root)
    factory, _, _ = fake_factory()
    with pytest.raises(BrowserLaunchError, match="profile was not found"):
        open_official_site(playwright_factory=factory)
    assert factory.starts == 0


def test_profile_discovery_only_lists_standard_existing_profiles(monkeypatch, tmp_path):
    from modules.browser import available_chrome_profiles

    profile_root = tmp_path / "Chrome User Data"
    for name in ("Default", "Profile 1", "System Profile", "Guest Profile"):
        (profile_root / name).mkdir(parents=True)
    monkeypatch.setattr("modules.browser.chrome_user_data_dir", lambda: profile_root)
    assert available_chrome_profiles() == ("Default", "Profile 1")


def test_custom_official_path_is_navigated(monkeypatch, tmp_path):
    configure_chrome(monkeypatch, tmp_path)
    factory, _, _ = fake_factory()
    session = open_official_site(
        "https://appointment.ivacbd.com/login/",
        playwright_factory=factory,
    )
    assert session.page.visited == [
        ("https://appointment.ivacbd.com/login/", {"wait_until": "commit", "timeout": 30000})
    ]
    session.close()


@pytest.mark.parametrize("url", [
    "http://appointment.ivacbd.com/",
    "https://example.test/",
    "https://user:secret@appointment.ivacbd.com/",
    "https://appointment.ivacbd.com/?token=secret",
    "https://appointment.ivacbd.com/path#login",
])
def test_nonofficial_urls_are_rejected_before_browser_starts(url):
    factory, _, _ = fake_factory()
    with pytest.raises(ValueError):
        open_official_site(url, playwright_factory=factory)
    assert factory.starts == 0


def test_official_url_canonicalizes_to_root():
    assert validate_ivac_url("https://appointment.ivacbd.com") == IVAC_URL


def test_official_path_is_preserved_and_hostname_is_canonicalized():
    assert validate_ivac_url("https://APPOINTMENT.IVACBD.COM/login/") == "https://appointment.ivacbd.com/login/"
