"""Local Streamlit dashboard for IVAC Webfile preparation and review."""

from datetime import date
import hashlib

import streamlit as st
from dotenv import load_dotenv

from config.readiness import MAX_APPLICANTS, OFFICIAL_FAQ_URL, webfile_age_status
from models.applicant import ManualConfirmations
from modules.data_export import serialize_reviewed_applicants
from modules.data_validator import extract_fields, validate_account_profile, validate_applicant
from modules.ocr_reader import OCRProcessingError, OCRUnavailable, apply_ocr_results, get_ocr_languages, get_ocr_status, run_local_ocr
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
reviewed_applicants = []
reviewed_field_count = 0
reviewable_field_count = 0

for index in range(int(applicant_count)):
    role = "Primary applicant" if index == 0 else f"Secondary applicant {index}"
    with st.expander(role, expanded=index == 0):
        upload = st.file_uploader(f"Upload {role.lower()} Webfile (PDF)", type=["pdf"], key=f"webfile_{index}", help="PDF only; maximum 15 MB. Files are not saved to disk.")
        if upload is None:
            st.session_state.pop(f"ocr_results_{index}", None)
        webfile_ok = False
        field_review_complete = False
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
                    fingerprint = hashlib.sha256(upload.getvalue()).hexdigest()
                    ocr_cache_key = f"ocr_results_{index}"
                    cached_ocr = st.session_state.get(ocr_cache_key)
                    if cached_ocr and cached_ocr.get("fingerprint") == fingerprint:
                        extraction = apply_ocr_results(extraction, cached_ocr.get("pages", {}))
                    elif cached_ocr:
                        del st.session_state[ocr_cache_key]

                    pages_needing_ocr = tuple(page.page_number for page in extraction.pages if not page.text.strip() and not (page.ocr_text or "").strip())
                    if pages_needing_ocr:
                        ocr_ready, ocr_message = get_ocr_status()
                        st.warning("This PDF has page(s) without selectable text (" + ", ".join(map(str, pages_needing_ocr)) + "). Optional OCR runs locally and will be kept separate from original PDF text.")
                        if not ocr_ready:
                            st.info(ocr_message)
                        else:
                            languages = get_ocr_languages()
                            if languages:
                                default_languages = ["eng"] if "eng" in languages else [languages[0]]
                                selected_languages = st.multiselect("Optional local OCR language(s)", languages, default=default_languages, key=f"ocr_language_{index}")
                                if st.button("Run local OCR on pages without text", key=f"run_ocr_{index}"):
                                    if not selected_languages:
                                        st.warning("Select at least one installed Tesseract language.")
                                    else:
                                        try:
                                            with st.spinner("Reading scanned pages locally…"):
                                                extraction = run_local_ocr(upload, extraction, language="+".join(selected_languages))
                                            page_results = {
                                                page.page_number: (page.ocr_text or "", page.ocr_confidence)
                                                for page in extraction.pages if page.ocr_text is not None
                                            }
                                            st.session_state[ocr_cache_key] = {"fingerprint": fingerprint, "pages": page_results}
                                        except (OCRUnavailable, OCRProcessingError) as exc:
                                            st.error(str(exc))
                            else:
                                st.info("Tesseract is installed, but it has no usable language models. Install language data and restart Streamlit.")

                    if not extraction.has_review_text:
                        st.warning("No selectable or OCR text was found. Review the original manually.")
                    else:
                        native_page_count = sum(1 for page in extraction.pages if page.text.strip())
                        ocr_page_count = sum(1 for page in extraction.pages if not page.text.strip() and (page.ocr_text or "").strip())
                        st.success(f"Read text from {native_page_count} page(s) using selectable text and {ocr_page_count} page(s) using OCR.")
                        if any(not page.text.strip() and not (page.ocr_text or "").strip() for page in extraction.pages):
                            st.warning("Some pages still have no text. Review those pages manually.")
                        with st.expander("Show page-by-page extracted text"):
                            for page in extraction.pages:
                                st.markdown(f"**Page {page.page_number}**")
                                if page.text.strip():
                                    st.caption("Original selectable PDF text")
                                    st.text(page.text)
                                elif page.ocr_text is not None:
                                    st.caption("OCR output (local Tesseract; original PDF text unchanged)")
                                    st.text(page.ocr_text or "OCR found no text.")
                                else:
                                    st.text("No selectable text on this page.")

                    # Always show a review card, including when a page is scanned
                    # and optional OCR is unavailable, so manual entry remains possible.
                    fields = extract_fields(extraction)
                    form_values = {}
                    confirmed_fields = []
                    for field in fields:
                        with st.container(border=True):
                            st.markdown(f"**{field.label}**")
                            st.caption(f"Method: {field.extraction_method} · Heuristic confidence: {field.confidence} · {field.status}")
                            if field.source_references:
                                for reference in field.source_references:
                                    st.caption(f"Source page {reference.page_number} · {reference.extraction_method} · confidence {reference.confidence}")
                                    st.code(reference.source_text, language=None)
                            else:
                                st.warning("Not detected in the configured labels. Review the original PDF manually.")
                            if field.status.startswith(("Ambiguous", "Conflicting", "Duplicate")):
                                st.warning("Multiple or repeated values need your review. Check each source reference before choosing.")
                            initial = field.value or ""
                            if field.status.startswith(("Ambiguous", "Conflicting", "Duplicate")):
                                initial = ""
                            form_values[field.key] = st.text_input("Reviewed value", value=initial, key=f"applicant_{index}_{field.key}", placeholder="Needs review" if not initial else "")
                            confirmed = st.checkbox("I verified this value against the original Webfile", key=f"confirm_{index}_{field.key}")
                            st.caption("Applicant verification: " + ("Confirmed by applicant" if confirmed else "Needs verification"))
                            manual_page = 0
                            if not field.source_references or field.status.startswith(("Ambiguous", "Conflicting", "Duplicate")):
                                manual_page = st.number_input(
                                    "Source page for manually entered/resolved value (0 = not recorded)",
                                    min_value=0,
                                    max_value=len(extraction.pages),
                                    value=field.source_page or 0,
                                    step=1,
                                    key=f"manual_page_{index}_{field.key}",
                                )
                            if form_values[field.key]:
                                reviewable_field_count += 1
                                if confirmed:
                                    reviewed_field_count += 1
                            confirmed_fields.append({
                                "key": field.key,
                                "label": field.label,
                                "value": form_values[field.key],
                                "source_pages": list(field.source_pages) if field.source_pages else ([int(manual_page)] if manual_page else []),
                                "extraction_method": field.extraction_method if field.value else ("Manual entry" if form_values[field.key] else "Not detected"),
                                "confidence": field.confidence,
                                "verification_status": "Confirmed by applicant" if confirmed else "Needs verification",
                            })
                    populated_fields = [item for item in confirmed_fields if item["value"]]
                    field_review_complete = bool(populated_fields) and all(item["verification_status"] == "Confirmed by applicant" for item in populated_fields)
                    applicant_model, validation_errors = validate_applicant(form_values)
                    has_extracted_identity = any(field.value for field in fields)
                    webfile_ok = (has_extracted_identity or field_review_complete) and applicant_model is not None and not validation_errors
                    for error in validation_errors:
                        st.warning(error)
                    if not fields or all(field.value is None for field in fields):
                        st.warning("No configured labels were recognized. Review the Webfile manually.")
                    st.caption("Read all displayed text as a proposed extraction; confirm every identity value yourself.")
                    populated_count = sum(1 for item in confirmed_fields if item["value"])
                    confirmed_count = sum(1 for item in confirmed_fields if item["value"] and item["verification_status"] == "Confirmed by applicant")
                    st.progress(confirmed_count / max(populated_count, 1), text=f"{confirmed_count} of {populated_count} populated fields verified")
                    reviewed_applicants.append({"applicant": role, "fields": confirmed_fields})

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
        applicant_records.append({
            "Applicant": role,
            "Webfile": "Uploaded" if upload else "Not uploaded",
            "Age check": "Within 30 days" if age_ok else "Needs review",
            "Status": "Fields verified" if upload and webfile_ok and field_review_complete and age_ok else ("Needs review" if upload else "Not started"),
        })

st.subheader("Applicant list")
st.dataframe(applicant_records, hide_index=True, width="stretch")
st.progress(reviewed_field_count / max(reviewable_field_count, 1), text=f"Document review progress: {reviewed_field_count} of {reviewable_field_count} populated fields verified")
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
profile_confirmed = st.checkbox("I reviewed the account-profile information against the primary Webfile", key="profile_confirmed")
profile_for_export = {"confirmed": profile_confirmed, "values": profile_values}
try:
    current_export_data = serialize_reviewed_applicants(reviewed_applicants, profile_for_export)
    current_export_signature = hashlib.sha256(current_export_data).hexdigest()
except ValueError:
    current_export_data = None
    current_export_signature = None
saved_export_signature = st.session_state.get("review_export_signature")
if saved_export_signature and saved_export_signature != current_export_signature:
    st.session_state.pop("review_export_json", None)
    st.session_state.pop("review_export_signature", None)

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

with st.expander("Optional JSON export of reviewed information"):
    st.warning("Sensitive personal information may be included. The export excludes original PDF content and is created only after your explicit confirmation.")
    export_confirmed = st.checkbox("I understand this download contains sensitive applicant data", key="export_confirmed")
    if st.button("Prepare reviewed applicant JSON", key="prepare_json_export"):
        if not export_confirmed:
            st.error("Confirm the sensitive-data warning before preparing an export.")
        else:
            try:
                st.session_state["review_export_json"] = serialize_reviewed_applicants(reviewed_applicants, profile_for_export)
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.session_state["review_export_signature"] = current_export_signature
    if st.session_state.get("review_export_json") and export_confirmed:
        st.download_button(
            "Download reviewed applicant JSON",
            data=st.session_state["review_export_json"],
            file_name="reviewed_applicant_information.json",
            mime="application/json",
        )

st.markdown(f"FAQ reference: [{OFFICIAL_FAQ_URL}]({OFFICIAL_FAQ_URL})")
st.warning("Applicants should carry out sign-up and booking themselves. Never share your password or OTP. This tool does not automate authentication, CAPTCHA, form submission, appointment polling/reservation, or payment.")
st.subheader("Appointment status")
st.info("Appointment status is not connected to the IVAC website. Check it yourself on the official portal.")
st.subheader("Activity logs")
st.caption("The app does not create an activity log or store applicant details after the session.")
st.caption("PDFs and extracted information are not written to disk by this application. Clearing the browser tab/session discards the in-memory state.")
