from streamlit.testing.v1 import AppTest


def test_dashboard_starts_without_streamlit_exceptions():
    app = AppTest.from_file("app.py").run(timeout=15)
    assert not app.exception
    assert any("Auto Appointment Tracker" in item.value for item in app.title)


def test_dashboard_supports_four_applicants():
    app = AppTest.from_file("app.py").run(timeout=15)
    app.number_input[0].set_value(4).run(timeout=15)
    assert not app.exception
    assert app.number_input[0].value == 4


def test_dashboard_shows_browser_assistant_and_manual_action_guidance():
    app = AppTest.from_file("app.py").run(timeout=15)
    assert not app.exception
    assert any("IVAC Browser Assistant" in item.value for item in app.subheader)
    assert any(button.label == "Open IVAC Website" and button.disabled is False for button in app.button)
    assert any(button.label == "Close browser" and button.disabled is True for button in app.button)
    assert any("yourself" in item.value for item in app.warning)
