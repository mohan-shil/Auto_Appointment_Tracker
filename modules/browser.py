"""Visible, applicant-controlled browser launch for the official IVAC site."""

from dataclasses import dataclass
import atexit
import os
from pathlib import Path
import re
import shutil
import sys
from typing import Any, Optional
from urllib.parse import urlsplit


IVAC_URL = "https://appointment.ivacbd.com/"
_BROWSER_SESSIONS = []


class BrowserLaunchError(RuntimeError):
    """A safe, user-displayable error while preparing the visible browser."""


def chrome_user_data_dir() -> Path:
    """Return the standard Google Chrome profile directory for this operating system."""
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "Google" / "Chrome" / "User Data"
        return Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "User Data"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
    config_dir = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return config_dir / "google-chrome"


def find_chrome_executable() -> Optional[Path]:
    """Locate the installed Google Chrome executable."""
    for command in ("google-chrome", "google-chrome-stable", "chrome"):
        executable = shutil.which(command)
        if executable:
            return Path(executable)

    if sys.platform == "darwin":
        candidates = (Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),)
    elif sys.platform == "win32":
        candidates = tuple(
            Path(base) / "Google" / "Chrome" / "Application" / "chrome.exe"
            for base in (
                os.environ.get("PROGRAMFILES", ""),
                os.environ.get("PROGRAMFILES(X86)", ""),
                os.environ.get("LOCALAPPDATA", ""),
            )
            if base
        )
    else:
        candidates = ()
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def available_chrome_profiles() -> tuple[str, ...]:
    """List existing standard Chrome profile folders without reading profile contents."""
    profile_root = chrome_user_data_dir()
    if not profile_root.is_dir():
        return ()
    profiles = [
        path.name
        for path in profile_root.iterdir()
        if path.is_dir() and re.fullmatch(r"(?:Default|Profile \d+)", path.name)
    ]
    return tuple(sorted(profiles, key=lambda name: (name != "Default", name)))


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
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "For safety, use an HTTPS link on appointment.ivacbd.com without query parameters or fragments."
        )
    return f"https://appointment.ivacbd.com{parsed.path or '/'}"


@dataclass
class BrowserSession:
    """Handles owned by the dashboard so the applicant can close the browser."""

    playwright: Any
    context: Any
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
        except Exception:
            return False

    def close(self) -> None:
        """Close Google Chrome and stop the Playwright driver, including partial cleanup."""
        if self.closed:
            return
        self.closed = True
        try:
            self.context.close()
        finally:
            try:
                self.playwright.stop()
            finally:
                if self in _BROWSER_SESSIONS:
                    _BROWSER_SESSIONS.remove(self)


def _close_browser_sessions() -> None:
    for session in tuple(_BROWSER_SESSIONS):
        try:
            session.close()
        except Exception:
            pass


atexit.register(_close_browser_sessions)


def open_official_site(
    url: str = IVAC_URL,
    playwright_factory: Optional[Any] = None,
    profile_directory: str = "Default",
) -> BrowserSession:
    """Open IVAC in visible Google Chrome using an existing local Chrome profile."""
    safe_url = validate_ivac_url(url)
    if not re.fullmatch(r"(?:Default|Profile \d+)", profile_directory):
        raise BrowserLaunchError("Choose an existing Google Chrome profile.")
    user_data_dir = chrome_user_data_dir()
    if not (user_data_dir / profile_directory).is_dir():
        raise BrowserLaunchError("The selected Chrome profile was not found. Open Chrome once to create it, then try again.")
    chrome_executable = find_chrome_executable()
    if chrome_executable is None:
        raise BrowserLaunchError("Google Chrome was not found. Install Google Chrome and open your profile once, then try again.")
    if playwright_factory is None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise BrowserLaunchError("Playwright is not installed. Install requirements, then restart the app.") from exc
        playwright_factory = sync_playwright

    playwright = None
    context = None
    try:
        playwright = playwright_factory().start()
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,
            executable_path=str(chrome_executable),
            args=[f"--profile-directory={profile_directory}"],
        )
        page = next((candidate for candidate in context.pages if candidate.url == "about:blank"), None)
        if page is None:
            page = context.new_page()
        page.goto(safe_url, wait_until="commit", timeout=30000)
        if page.url == "about:blank":
            raise BrowserLaunchError(
                "Google Chrome stayed on a blank page instead of opening the IVAC link. "
                "Check the selected profile and try again."
            )
        session = BrowserSession(playwright, context, page)
        _BROWSER_SESSIONS.append(session)
        return session
    except Exception as exc:
        if context is not None:
            try:
                context.close()
            except Exception:
                pass
        if playwright is not None:
            try:
                playwright.stop()
            except Exception:
                pass
        if isinstance(exc, BrowserLaunchError):
            message = str(exc)
        else:
            detail = str(exc).casefold()
            if "executable doesn't exist" in detail or "please run" in detail and "install" in detail:
                message = "Google Chrome could not be started. Confirm it is installed, then try again."
            elif "playwright is not installed" in detail or "no module named" in detail:
                message = "Playwright is not installed. Install requirements, then restart the app."
            elif "user data directory is already in use" in detail or "processsingleton" in detail or "profile is in use" in detail:
                message = "Close all Google Chrome windows, then try opening the profile again."
            else:
                message = "Could not open the IVAC site in Google Chrome. Check your internet connection and Chrome profile, then try again."
        raise BrowserLaunchError(message) from exc
