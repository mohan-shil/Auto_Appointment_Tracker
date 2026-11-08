import sys

from streamlit.testing.v1 import AppTest

from modules.browser import IVAC_URL
from modules.document_store import LocalDocumentStore


def test_dashboard_starts_with_v2_sections_and_primary_required():
    app = AppTest.from_file("app.py").run(timeout=15)
    assert not app.exception
    assert any("Auto Appointment Tracker" in item.value for item in app.title)
    headers = [item.value for item in app.header]
    assert "A. Applicant Documents" in headers
    assert "B. IVAC Browser Assistant" in headers
    assert next(item for item in app.text_input if item.label == "IVAC link").value == IVAC_URL
    assert "IVAC Portal Inspection Mode" in headers
    assert "C. Appointment Workflow" in headers
    assert "D. Session & Storage Management" in headers
    open_button = next(button for button in app.button if button.label == "Open Browser")
    assert open_button.disabled
    assert next(button for button in app.button if button.label == "Capture Current Page Structure").disabled
    assert next(button for button in app.button if button.label == "Export Inspection Report").disabled
    assert next(button for button in app.button if button.label == "Clear Inspection Reports").disabled
    assert any("Primary Webfile required" in item.value for item in app.warning)


def test_four_fixed_slots_and_optional_secondary_add_remove_controls():
    app = AppTest.from_file("app.py").run(timeout=15)
    applicant_headers = [item.value for item in app.subheader]
    assert applicant_headers.count("Primary applicant") == 1
    for index in range(1, 4):
        assert f"Secondary applicant {index}" in applicant_headers
        assert any(button.label == f"Add Secondary applicant {index}" for button in app.button)
    next(button for button in app.button if button.label == "Add Secondary applicant 1").click().run(timeout=15)
    assert not app.exception
    assert any(button.label == "Remove Secondary applicant 1" for button in app.button)


def test_workflow_progress_state_persists_across_streamlit_reruns():
    app = AppTest.from_file("app.py").run(timeout=15)
    sign_in = next(item for item in app.checkbox if item.label == "Sign in manually")
    sign_in.set_value(True).run(timeout=15)
    assert not app.exception
    sign_in_again = next(item for item in app.checkbox if item.label == "Sign in manually")
    assert sign_in_again.value is True


def test_uploaded_document_metadata_persists_across_reruns_and_clear_all_removes_it():
    app = AppTest.from_file("app.py").run(timeout=15)
    store = app.session_state["document_store"]
    synthetic_pdf = b"%PDF-1.7\n% synthetic fictional Webfile\n%%EOF\n"
    saved = store.save(0, "fictional-primary.pdf", synthetic_pdf)
    app.run(timeout=15)
    assert not app.exception
    assert "fictional-primary.pdf" in [item.value.split(": ", 1)[-1] for item in app.text]
    assert str(saved.path) in [item.value for item in app.code]
    assert app.session_state["document_store"] is store
    next(button for button in app.button if button.label == "Clear All Files").click().run(timeout=15)
    assert not app.exception
    assert not saved.path.exists()
    assert not store.session_dir.exists()
    assert app.session_state["document_store"] is not store
    assert not app.session_state["document_store"].documents


def test_manual_chromium_upload_guidance_is_displayed_with_a_saved_pdf_path():
    app = AppTest.from_file("app.py").run(timeout=15)
    store = app.session_state["document_store"]
    store.save(0, "fictional-primary.pdf", b"%PDF-1.7\n% synthetic\n%%EOF\n")
    app.run(timeout=15)
    assert not app.exception
    instruction = next(item.value for item in app.info if "To upload this saved copy in Chromium" in item.value)
    assert "complete the upload yourself" in instruction
    if sys.platform == "darwin":
        assert "Command + Shift + G" in instruction
        assert any(button.label == "Reveal PDF in Finder" for button in app.button)
    elif sys.platform == "win32":
        assert any(button.label == "Show PDF in Explorer" for button in app.button)
    elif sys.platform.startswith("linux"):
        assert any(button.label == "Open Containing Folder" for button in app.button)
    store.close()


def test_browser_error_and_manual_boundaries_are_displayed_without_portal_access():
    app = AppTest.from_file("app.py").run(timeout=15)
    assert not app.exception
    assert any("OTP" in item.value and "manually" in item.value for item in app.info)
    assert any("No appointment date or centre availability is checked" in item.value for item in app.warning)
