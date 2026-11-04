"""Local Webfile manager and manual IVAC browser assistant."""

import sys

import streamlit as st

from modules.browser import BrowserLaunchError, BrowserSession, open_official_site
from modules.document_store import APPLICANT_SLOTS, DocumentStoreError, LocalDocumentStore, cleanup_stale_sessions
from modules.workflow import APPOINTMENT_WORKFLOW

APPLICANT_LABELS = (
    "Primary applicant",
    "Secondary applicant 1",
    "Secondary applicant 2",
    "Secondary applicant 3",
)
MAX_FILE_MB = 15

st.set_page_config(page_title="Auto Appointment Tracker", page_icon="🗂️", layout="wide")
st.title("Auto Appointment Tracker")
st.caption("Prepare original Webfile PDFs locally, then complete every IVAC website action yourself.")


def get_document_store() -> LocalDocumentStore:
    store = st.session_state.get("document_store")
    if not isinstance(store, LocalDocumentStore) or not store.session_dir.exists():
        cleanup_stale_sessions()
        store = LocalDocumentStore()
        st.session_state["document_store"] = store
    return store


try:
    document_store = get_document_store()
except (DocumentStoreError, OSError):
    st.error("Private temporary storage could not be prepared. Check local disk space and folder permissions, then restart the app.")
    st.stop()
if "secondary_enabled" not in st.session_state:
    st.session_state["secondary_enabled"] = {1: False, 2: False, 3: False}
if "upload_generations" not in st.session_state:
    st.session_state["upload_generations"] = {slot: 0 for slot in range(APPLICANT_SLOTS)}

st.header("A. Applicant Documents")
st.write("Keep up to four original Webfile PDFs in this temporary local session. The app does not read or preview their contents.")

document_columns = st.columns(2)
for slot, applicant_label in enumerate(APPLICANT_LABELS):
    with document_columns[slot % 2].container(border=True):
        st.subheader(applicant_label)
        if slot > 0 and not st.session_state["secondary_enabled"][slot]:
            st.caption("Optional applicant slot")
            if st.button(f"Add {applicant_label}", key=f"add_applicant_{slot}"):
                st.session_state["secondary_enabled"][slot] = True
                st.rerun()
            continue

        widget_generation = st.session_state["upload_generations"][slot]
        upload = st.file_uploader(
            "Upload original Webfile PDF" if slot == 0 else "Upload secondary Webfile PDF",
            type=["pdf"],
            accept_multiple_files=False,
            key=f"applicant_pdf_{slot}_{widget_generation}",
            help=f"PDF only · maximum {MAX_FILE_MB} MB · saved temporarily on this device.",
        )
        if upload is not None:
            if upload.size > MAX_FILE_MB * 1024 * 1024:
                st.error(f"The PDF exceeds the {MAX_FILE_MB} MB file limit.")
            else:
                try:
                    document_store.save(slot, upload.name, upload.getvalue())
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.success("PDF saved locally without modification.")

        saved = document_store.documents.get(slot)
        if saved:
            file_available = saved.path.is_file()
            st.text(f"Original filename: {saved.original_name}")
            storage_status = "Available in temporary local storage" if file_available else "Missing from temporary local storage"
            st.caption(f"Size: {saved.size_bytes / (1024 * 1024):.2f} MB · Status: {storage_status}")
            st.caption("Saved file path:")
            st.code(str(saved.path), language=None)
            reveal_label = None
            if not file_available:
                st.error("The saved PDF is missing. Upload it again before continuing.")
            elif sys.platform == "darwin":
                st.info("To upload this saved copy in Chromium, open the IVAC file picker and use Command + Shift + G, then enter the displayed file path. Select the correct PDF and complete the upload yourself.")
                reveal_label = "Reveal PDF in Finder"
            elif sys.platform == "win32":
                st.info("To upload this saved copy in Chromium, open the IVAC file picker, navigate to the displayed file path, and select the correct PDF yourself.")
                reveal_label = "Show PDF in Explorer"
            elif sys.platform.startswith("linux"):
                st.info("To upload this saved copy in Chromium, open the IVAC file picker, navigate to the displayed file path, and select the correct PDF yourself.")
                reveal_label = "Open Containing Folder"
            else:
                st.info("To upload this saved copy in Chromium, use the displayed path in the IVAC file picker and select the correct PDF yourself.")
                reveal_label = None
                st.caption("Automatic file reveal is not supported on this operating system.")
            if reveal_label and st.button(reveal_label, key=f"reveal_pdf_{slot}"):
                try:
                    reveal_message = document_store.reveal(slot)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.success(reveal_message)
        elif slot == 0:
            st.warning("Primary Webfile required before opening the IVAC website.")
        else:
            st.caption("No PDF uploaded for this optional applicant.")
        if slot > 0 and st.button(f"Remove {applicant_label}", key=f"remove_applicant_{slot}"):
            try:
                document_store.remove(slot)
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.session_state["secondary_enabled"][slot] = False
                st.session_state["upload_generations"][slot] += 1
                st.rerun()

clear_col, storage_col = st.columns([1, 2])
if clear_col.button("Clear All Files", type="secondary", key="clear_all_files"):
    try:
        document_store.clear_all()
        document_store.close()
    except ValueError as exc:
        st.error(str(exc))
    else:
        for slot in range(APPLICANT_SLOTS):
            st.session_state["upload_generations"][slot] += 1
        st.session_state["last_clear_status"] = "All saved PDF files and the previous temporary session folder were removed."
        st.rerun()
storage_col.caption(st.session_state.get("last_clear_status", "Temporary file storage is active for this app session."))

primary_ready = 0 in document_store.documents
secondary_count = sum(1 for slot in (1, 2, 3) if slot in document_store.documents)
uploaded_count = len(document_store.documents)
st.progress(uploaded_count / APPLICANT_SLOTS, text=f"{uploaded_count} of {APPLICANT_SLOTS} applicant PDF slots filled · {secondary_count} secondary file(s)")

st.header("B. IVAC Browser Assistant")
st.write("Open the official portal in a separate visible Chromium window. The applicant controls that window directly.")
browser_session = st.session_state.get("ivac_browser_session")
browser_active = isinstance(browser_session, BrowserSession) and not browser_session.closed
browser_open = browser_active and browser_session.is_open
if browser_open:
    st.success("Browser status: Visible Chromium window is open. The app does not read the current page or login state.")
elif browser_active:
    st.warning("Browser status: The Chromium page appears closed. Close the browser session to clean up its resources.")
else:
    st.info("Browser status: Not open.")

browser_col, browser_status_col = st.columns([1, 2])
if browser_col.button("Open Browser", type="primary", disabled=not primary_ready or browser_active, key="open_ivac_browser"):
    try:
        st.session_state["ivac_browser_session"] = open_official_site()
        st.session_state.pop("browser_error", None)
        st.rerun()
    except BrowserLaunchError as exc:
        st.session_state["browser_error"] = str(exc)
if browser_col.button("Close Browser", disabled=not browser_active, key="close_ivac_browser"):
    try:
        browser_session.close()
    except Exception:
        st.session_state["browser_error"] = "The browser did not close cleanly. Close its Chromium window manually."
    st.session_state.pop("ivac_browser_session", None)
    st.rerun()
if not primary_ready:
    browser_status_col.warning("Upload the primary Webfile PDF before opening the official website.")
if st.session_state.get("browser_error"):
    st.error(st.session_state["browser_error"])
st.caption("First use may require Chromium setup: `python -m playwright install chromium`.")
st.info("Sign in manually. Enter credentials and email/mobile OTPs only on the official IVAC site. Do not share them with agents or intermediaries.")

st.header("C. Appointment Workflow")
st.caption("Mark steps as you complete them yourself. These checkboxes do not interact with or read the IVAC website.")
workflow_columns = st.columns(3)
workflow_done = []
for index, step in enumerate(APPOINTMENT_WORKFLOW):
    workflow_done.append(workflow_columns[index % 3].checkbox(step, key=f"workflow_step_{index}"))
workflow_completed = sum(workflow_done)
st.progress(workflow_completed / len(APPOINTMENT_WORKFLOW), text=f"Applicant-marked workflow progress: {workflow_completed} of {len(APPOINTMENT_WORKFLOW)} steps")
st.warning("No appointment date or centre availability is checked by this app. Follow the order and instructions shown by the live IVAC portal; the published FAQ describes centre selection before the date calendar. All login, OTP, CAPTCHA, uploads, selections, submissions and payment remain manual.")

st.header("D. Session & Storage Management")
st.write("PDFs are kept in a private temporary application folder outside the Git repository, under a random session directory. The app retains the original bytes and does not extract, display, log, or transmit applicant information.")
st.write(f"Storage status: **{uploaded_count} PDF(s)** in the current session. Folder permissions are restricted to the current local account where the operating system supports POSIX permissions.")
st.write("Use **Clear All Files** to remove the saved PDFs now. Closing this dashboard tab does not immediately notify Streamlit, so it does not trigger immediate cleanup. Files are removed when the Streamlit process exits normally; abandoned session folders are removed the next time the app starts. A crash or forced shutdown may leave temporary files until that next startup cleanup.")
st.caption("Clear removes the local files by unlinking them; it is not a forensic secure-erase guarantee. Never save passwords, OTPs, or credentials in this app.")

st.markdown("Official portal: [appointment.ivacbd.com](https://appointment.ivacbd.com/) · [IVAC Appointment FAQ](https://www.ivacbd.com/faq/appointment-management-system)")
