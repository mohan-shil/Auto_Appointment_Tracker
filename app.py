"""Local Streamlit dashboard for IVAC Webfile preparation and review."""

from datetime import date

import streamlit as st
from dotenv import load_dotenv

from config.readiness import MAX_APPLICANTS, OFFICIAL_FAQ_URL, webfile_age_status
from models.applicant import ManualConfirmations
from modules.data_validator import extract_fields, validate_account_profile, validate_applicant
from modules.pdf_reader import PDFReadError, extract_pdf

load_dotenv()
st.set_page_config(page_title="Auto Appointment Tracker", page_icon="📄", layout="wide")
st.title("Auto Appointment Tracker")
st.caption("Local preparation and review for applicants. You personally complete all IVAC website actions.")

with st.sidebar:
    st.header("Overview")
    st.write("1. Add applicants  →  2. Review Webfiles  →  3. Complete readiness checklist")
    st.info("PDFs are processed in memory. No applicant information is sent to a third-party service.")

st.subheader("Applicant readiness")
applicant_count = st.number_input("Applicants in this booking group (1 primary + up to 3 secondary)", 1, MAX_APPLICANTS, 1)
applicant_records = []
all_webfiles_recent = True
all_webfiles_uploaded = True
any_uploaded_webfile = False
primary_webfile_ready = False

for index in range(int(applicant_count)):
    role = "Primary applicant" if index == 0 else f"Secondary applicant {index}"
    with st.expander(role, expanded=index == 0):
        upload = st.file_uploader(f"Upload {role.lower()} Webfile (PDF)", type=["pdf"], key=f"webfile_{index}", help="PDF only; maximum 15 MB. Files are not saved to disk.")
        webfile_ok = False
        if upload is not None:
            any_uploaded_webfile = True
            if upload.size > 15 * 1024 * 1024:
                st.error("File is over the 15 MB limit. Choose a smaller PDF.")
            else:
                try:
                    upload.seek(0)
                    extraction = extract_pdf(upload, upload.name)
                except PDFReadError as exc:
                    st.error(str(exc))
                except Exception:
                    st.error("The file could not be processed. Please choose the PDF again.")
                else:
                    if not extraction.has_text:
                        st.warning("No selectable text found; this may be a scanned PDF. Check the original manually.")
                    else:
                        st.success(f"Read selectable text on {len(extraction.pages)} page(s).")
                        if extraction.pages_without_text:
                            page_list = ", ".join(map(str, extraction.pages_without_text))
                            st.warning(f"No selectable text was found on page(s) {page_list}; these may be scanned pages. Review them manually.")
                        with st.expander("Show page-by-page extracted text"):
                            for page in extraction.pages:
                                st.markdown(f"**Page {page.page_number}**")
                                st.text(page.text or "No selectable text on this page.")
                        fields = extract_fields(extraction)
                        form_values = {}
                        field_sources = {}
                        for field in fields:
                            label = field.label
                            if field.source_pages:
                                label += " · page(s) " + ", ".join(map(str, field.source_pages))
                            if field.status.startswith("Ambiguous") or field.status.startswith("Duplicate"):
                                st.warning(f"{field.label}: {field.status}. Found: {field.value}")
                            initial = field.value or ""
                            if field.status.startswith(("Ambiguous", "Duplicate")):
                                initial = ""
                            form_values[field.key] = st.text_input(label, value=initial, key=f"applicant_{index}_{field.key}", placeholder="Needs review" if not initial else "")
                            field_sources[field.key] = field.source_pages or ((field.source_page,) if field.source_page else ())
                        applicant_model, validation_errors = validate_applicant(form_values)
                        webfile_ok = extraction.has_text and applicant_model is not None and not validation_errors
                        if validation_errors:
                            for error in validation_errors:
                                st.warning(error)
                        if not extraction.has_text:
                            st.info("Field extraction is unavailable. A person must inspect the original PDF.")
                        elif not fields or all(field.value is None for field in fields):
                            st.warning("No configured labels were recognized. Review the Webfile manually.")
                        else:
                            st.caption("Recognized values still require comparison with the original Webfile.")

        webfile_date = st.date_input(f"Date printed on {role.lower()} Webfile (read it from the document)", value=None, key=f"webfile_date_{index}", max_value=date.today())
        age_ok = False
        age_message = "Enter the date shown on the Webfile to check the 30-day guidance."
        if webfile_date:
            age_ok, age_message = webfile_age_status(webfile_date, date.today())
            (st.success if age_ok else st.warning)(age_message)
        if not age_ok:
            all_webfiles_recent = False
        if not upload or not webfile_ok:
            all_webfiles_uploaded = False
        if index == 0:
            primary_webfile_ready = bool(upload and webfile_ok)
        applicant_records.append({"Applicant": role, "Webfile": "Uploaded" if upload and webfile_ok else ("Needs review" if upload else "Not uploaded"), "Age check": "Within 30 days" if age_ok else "Needs review", "Status": "Ready for review" if upload and webfile_ok and age_ok else "Needs review"})

st.subheader("Applicant list")
st.dataframe(applicant_records, hide_index=True, width="stretch")
if applicant_count > MAX_APPLICANTS:
    st.error("IVAC FAQ limits one account to four applicants.")
elif not any_uploaded_webfile:
    st.info("No Webfiles uploaded yet. Upload the primary Webfile to begin review.")

st.subheader("IVAC account profile — enter manually")
st.caption("IVAC sign-up information is separate from Webfile extraction. The FAQ says profile details should match the primary Webfile. Do not expect email, mobile, or NID/citizenship number to appear in a Webfile.")
with st.expander("Review account profile fields", expanded=False):
    profile_col1, profile_col2 = st.columns(2)
    profile_values = {
        "given_name": profile_col1.text_input("Given name", key="profile_given_name"),
        "surname": profile_col2.text_input("Surname", key="profile_surname"),
        "passport_number": profile_col1.text_input("Passport number", key="profile_passport"),
        "nid_or_citizenship_number": profile_col2.text_input("NID / citizenship number", key="profile_nid"),
        "mobile_number": profile_col1.text_input("Mobile number", key="profile_mobile"),
        "email": profile_col2.text_input("Email", key="profile_email"),
        "date_of_birth": profile_col1.text_input("Date of birth (YYYY-MM-DD or DD/MM/YYYY)", key="profile_dob"),
    }
    profile_model, profile_errors = validate_account_profile(profile_values)
    profile_required = ("given_name", "surname", "passport_number", "nid_or_citizenship_number", "date_of_birth", "mobile_number", "email")
    missing_profile = [key.replace("_", " ").title() for key in profile_required if not profile_values.get(key)]
    if missing_profile:
        st.warning("Missing profile information to review: " + ", ".join(missing_profile))
    for error in profile_errors:
        st.warning(error)
    if profile_model is not None and not profile_errors:
        st.success("Profile field formats look acceptable. Compare them with the primary Webfile yourself.")
    st.caption("Profile requirements and matching rules are based on the linked FAQ. This tool does not log in or modify your account.")
profile_ready = not missing_profile and not profile_errors
st.caption(f"Account profile information: {len(profile_required) - len(missing_profile)} of {len(profile_required)} fields entered" + ("; format review needed." if profile_errors else "."))

st.subheader("Booking preparation checklist")
st.caption("Manually mark each item after you have completed it. A checked item is your confirmation, not a website status or a guarantee of slot availability.")
checklist = [
    ("primary_webfile", "Primary applicant Webfile uploaded and reviewed"),
    ("secondary_webfiles", "Secondary applicant Webfiles uploaded, if applicable"),
    ("max_applicants", "Applicant group contains no more than four applicants"),
    ("webfile_age", "Every Webfile date checked; each is no older than 30 days"),
    ("consistency", "Applicant details checked for consistency with the primary Webfile"),
    ("originals", "Confirmed that all Webfiles are original and unmodified"),
    ("centre", "Ready to select an eligible IVAC centre personally"),
    ("appointment_date", "Ready to select an available appointment date personally"),
    ("payment_invoice", "Ready to complete payment personally and confirm/download the invoice"),
]
completed = []
for key, label in checklist:
    completed.append(st.checkbox(label, key=f"check_{key}"))
completed_count = sum(completed)
manual_confirmations = ManualConfirmations(
    webfiles_unmodified=st.session_state.get("check_originals"),
    applicant_details_consistent=st.session_state.get("check_consistency"),
    centre_selection_reviewed=st.session_state.get("check_centre"),
    appointment_date_reviewed=st.session_state.get("check_appointment_date"),
    payment_and_invoice_reviewed=st.session_state.get("check_payment_invoice"),
)
st.progress(completed_count / len(checklist), text=f"Preparation checklist: {completed_count} of {len(checklist)} items confirmed")
manual_confirmation_values = manual_confirmations.model_dump().values()
manual_confirmations_complete = all(value is True for value in manual_confirmation_values)
if completed_count == len(checklist) and applicant_count <= MAX_APPLICANTS and all_webfiles_recent and all_webfiles_uploaded and profile_ready and manual_confirmations_complete:
    st.success("Preparation checklist complete. This does not mean a slot exists or that an appointment is booked.")
elif completed_count == len(checklist):
    st.warning("Applicant readiness: Needs review. Confirm each uploaded Webfile, its age, and the manually entered account profile.")
else:
    st.info("Applicant readiness: Needs preparation")
if st.session_state.get("check_primary_webfile") and not primary_webfile_ready:
    st.warning("Checklist says the primary Webfile is uploaded, but no file is currently selected.")
if st.session_state.get("check_secondary_webfiles") and int(applicant_count) == 1:
    st.info("No secondary applicants are configured; the secondary Webfile checklist item is not applicable.")
if completed_count == len(checklist) and not all_webfiles_uploaded:
    st.warning("Checklist is complete, but each listed applicant still needs a readable Webfile before applicant readiness can be shown.")
if st.session_state.get("check_webfile_age") and not all_webfiles_recent:
    st.warning("Checklist says the age check is complete, but one or more dates are missing or outside the 30-day limit.")

st.markdown(f"FAQ reference: [{OFFICIAL_FAQ_URL}]({OFFICIAL_FAQ_URL})")
st.warning("Applicants should carry out sign-up and booking themselves. Never share your password or OTP. This tool does not automate authentication, CAPTCHA, form submission, appointment polling/reservation, or payment.")
st.subheader("Appointment status")
st.info("Appointment status is not connected to the IVAC website. Check it yourself on the official portal.")
st.subheader("Activity logs")
st.caption("The app does not create an activity log or store applicant details after the session.")
st.caption("PDFs and extracted information are not written to disk by this application. Clearing the browser tab/session discards the in-memory state.")
