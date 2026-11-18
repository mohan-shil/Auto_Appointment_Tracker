from html.parser import HTMLParser
import json
from pathlib import Path

import pytest

from modules.browser import BrowserSession
from modules.portal_inspector import (
    InspectionError,
    _EXTRACT_SCRIPT,
    capture_portal_page,
    clear_exported_reports,
    export_inspection_reports,
    sanitize_destination,
)

FIXTURE = Path(__file__).parent / "fixtures" / "portal_inspection_synthetic.html"


class FixtureParser(HTMLParser):
    """Small test-only fixture reader; records structure, never form values."""
    def __init__(self):
        super().__init__()
        self.tags = []
        self.text = []
        self.current = None
        self.labels = {}
        self.select_options = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append((tag, attrs))
        if tag == "label" and "for" in attrs:
            self.current = ("label", attrs["for"], [])
        elif tag == "option":
            self.current = ("option", "", [])

    def handle_data(self, data):
        if self.current:
            self.current[2].append(data)

    def handle_endtag(self, tag):
        if self.current and ((tag == "label" and self.current[0] == "label") or (tag == "option" and self.current[0] == "option")):
            kind, key, text = self.current
            if kind == "label":
                self.labels[key] = " ".join("".join(text).split())
            else:
                self.select_options.append(" ".join("".join(text).split()))
            self.current = None

    def structure(self):
        title = next("Appointment Login" for tag, _ in self.tags if tag == "title")
        controls = []
        for tag, attrs in self.tags:
            if tag not in {"input", "select", "textarea"}:
                continue
            kind = attrs.get("type", tag)
            controls.append({"label": self.labels.get(attrs.get("id"), ""), "type": kind,
                             "required": "required" in attrs, "disabled": "disabled" in attrs,
                             "options": self.select_options if tag == "select" else [],
                             "accept": attrs.get("accept", "") if kind == "file" else ""})
        return {
            "title": title, "headings": ["Appointment Login"], "buttons": ["Continue"],
            "links": [{"label": "Home", "destination": "https://appointment.ivacbd.com/"},
                      {"label": "Appointment", "destination": "https://appointment.ivacbd.com/appointment?email=someone@example.test#step"}],
            "controls": controls, "dialogs": [], "navigation": [["Home", "Appointment"]],
            "captcha_present": any("captcha" in (attrs.get("class", "") + attrs.get("id", "")).lower() for tag, attrs in self.tags),
            "url": "https://appointment.ivacbd.com/login?token=secret#private",
        }


class FixturePage:
    url = "https://appointment.ivacbd.com/login?token=secret#private"
    closed = False

    def __init__(self):
        self.html = FIXTURE.read_text(encoding="utf-8")
        self.parser = FixtureParser()
        self.parser.feed(self.html)

    def is_closed(self):
        return self.closed

    def evaluate(self, script):
        assert script == _EXTRACT_SCRIPT
        # Assert the extraction implementation never reads sensitive browser state or values.
        forbidden = (".value", "cookie", "localStorage", "sessionStorage", "innerHTML", "outerHTML", "fetch(", "XMLHttpRequest", "screenshot")
        assert not any(term in script for term in forbidden)
        return self.parser.structure()


def session(page=None):
    class Closable:
        def close(self):
            pass
        def stop(self):
            pass
    return BrowserSession(Closable(), Closable(), page or FixturePage())


def test_capture_extracts_fixture_structure_and_sanitizes_url_and_sensitive_fields():
    report = capture_portal_page(session(), "Login page")
    page = report["page"]
    assert page["title"] == "Appointment Login"
    assert page["hostname"] == "appointment.ivacbd.com"
    assert page["pathname"] == "/login"
    assert page["headings"] == ["Appointment Login"]
    assert page["buttons"] == ["Continue"]
    assert page["links"][1] == {"label": "Appointment", "destination": "/appointment"}
    assert any(item["label"] == "Select centre" and item["options"] == ["Select an option", "[omitted]"] for item in page["form_controls"])
    assert not any(item["type"] == "password" for item in page["form_controls"])
    assert page["captcha_widget_present"] is True
    serialized = json.dumps(report)
    for secret in ("someone@example.test", "123456", "secret", "DO_NOT_READ", "data-sitekey", "value"):
        assert secret not in serialized


def test_destination_sanitization_discards_query_fragment_external_host_and_dynamic_paths():
    assert sanitize_destination("https://appointment.ivacbd.com/calendar?otp=123456#slot") == "/calendar"
    assert sanitize_destination("https://example.test/path?token=secret") == "[external destination omitted]"
    assert sanitize_destination("/applicant/ABCD1234") == "/[dynamic path omitted]"


def test_captcha_presence_is_boolean_only_and_file_accept_types_are_retained():
    page = capture_portal_page(session())["page"]
    assert page["captcha_widget_present"] is True
    file_control = next(item for item in page["form_controls"] if item["type"] == "file")
    assert file_control["accepted_file_types"] == ".pdf,application/pdf"


def test_capture_requires_live_official_application_session():
    with pytest.raises(InspectionError, match="missing or closed"):
        capture_portal_page(None)
    closed = session()
    closed.close()
    with pytest.raises(InspectionError, match="missing or closed"):
        capture_portal_page(closed)


def test_empty_or_unexpected_page_is_not_reported_as_captured():
    class EmptyPage(FixturePage):
        def evaluate(self, script):
            return {"url": self.url, "title": "", "headings": [], "buttons": [], "links": [], "controls": [], "dialogs": [], "navigation": [], "captcha_present": False}
    with pytest.raises(InspectionError, match="No visible page structure"):
        capture_portal_page(session(EmptyPage()))

    class MalformedPage(FixturePage):
        def evaluate(self, script):
            return {"url": self.url, "controls": ["unexpected item"]}
    with pytest.raises(InspectionError, match="unexpected structure"):
        capture_portal_page(session(MalformedPage()))


def test_navigation_timeout_returns_safe_error_without_a_capture():
    class TimeoutPage(FixturePage):
        def wait_for_load_state(self, state, timeout):
            raise TimeoutError("navigation timeout")
    with pytest.raises(InspectionError, match="did not finish loading"):
        capture_portal_page(session(TimeoutPage()))


def test_json_export_is_private_and_clear_removes_only_tracked_app_reports(tmp_path):
    report = capture_portal_page(session())
    output_dir = tmp_path / "IVAC-Inspection"
    file_path = export_inspection_reports([report], output_dir)
    assert json.loads(file_path.read_text()) == [report]
    assert file_path.stat().st_mode & 0o777 == 0o600
    assert output_dir.stat().st_mode & 0o777 == 0o700
    assert clear_exported_reports([file_path]) == 0  # custom export folder is never cleared by default cleanup
    assert file_path.exists()


def test_default_export_clear_only_removes_app_named_reports(tmp_path, monkeypatch):
    private_dir = tmp_path / "Documents" / "IVAC-Inspection"
    monkeypatch.setattr("modules.portal_inspector.DEFAULT_EXPORT_DIR", private_dir)
    path = export_inspection_reports([capture_portal_page(session())], private_dir)
    assert clear_exported_reports([path]) == 1
    assert not path.exists()


def test_export_rejects_project_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(InspectionError, match="outside the project"):
        export_inspection_reports([], tmp_path / "reports")
