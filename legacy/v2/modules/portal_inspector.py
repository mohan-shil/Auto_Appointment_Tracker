"""Privacy-minimizing, read-only inspection of the app-owned IVAC browser page."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import uuid
from urllib.parse import urlsplit

from modules.browser import BrowserSession

OFFICIAL_HOST = "appointment.ivacbd.com"
DEFAULT_EXPORT_DIR = Path.home() / "Documents" / "IVAC-Inspection"
_SAFE_WORDS = set("ivac appointment application applicant applicants visa webfile passport login log in sign up signup register account profile dashboard home public landing page otp email mobile phone password submit continue next back cancel close open upload file files choose select centre center location date calendar payment pay invoice confirm confirmation help faq notice important welcome required optional primary secondary name number reference details information document documents application status search verify verification select an option please enter your details sign in available unavailable amount total fee transaction receipt logout log out menu navigation contact support terms privacy english বাংলা online booking official visa application system appointment management system".split())
_SENSITIVE = re.compile(r"(?:[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|\+?\d[\d\s().-]{7,}\d|\b(?:passport|webfile|file|application|reference|visa)\s*(?:no\.?|number|#|:)?\s*[A-Z0-9-]{5,}\b)", re.I)
_SAFE_PATH = re.compile(r"^/[A-Za-z0-9/_-]*$")


class InspectionError(RuntimeError):
    """A safe error suitable for display in the local dashboard."""


def _safe_label(value):
    """Keep only short generic interface language; omit unrecognized/dynamic text."""
    if not isinstance(value, str):
        return "[omitted]"
    value = " ".join(value.split())[:160]
    if not value or _SENSITIVE.search(value) or any(ch.isdigit() for ch in value):
        return "[omitted]"
    words = re.findall(r"[A-Za-zÀ-ÿ]+", value.casefold())
    if not words or any(word not in _SAFE_WORDS for word in words):
        return "[omitted]"
    return value


def sanitize_destination(destination):
    """Return an official-host path only; discard query, fragment and unsafe paths."""
    try:
        parsed = urlsplit(destination or "")
        if parsed.scheme and parsed.hostname != OFFICIAL_HOST:
            return "[external destination omitted]"
        path = parsed.path or "/"
        if parsed.scheme and parsed.hostname != OFFICIAL_HOST:
            return "[external destination omitted]"
        if not _SAFE_PATH.fullmatch(path) or any(part.casefold() not in _SAFE_WORDS for part in path.split("/") if part):
            return "/[dynamic path omitted]"
        return path
    except (TypeError, ValueError):
        return "[destination omitted]"


_EXTRACT_SCRIPT = r"""() => {
 const visible = e => { const s=getComputedStyle(e), r=e.getBoundingClientRect();
   return s.display!=='none' && s.visibility!=='hidden' && Number(s.opacity)!==0 && r.width>0 && r.height>0; };
 const txt = e => (e.innerText || e.getAttribute('aria-label') || e.getAttribute('title') || '').trim();
 const nodes = (selector, fn) => Array.from(document.querySelectorAll(selector)).filter(visible).map(fn);
 const labelFor = e => { let l=e.labels && e.labels.length ? e.labels[0] : e.closest('label');
   return l ? txt(l) : (e.getAttribute('aria-label') || e.getAttribute('title') || ''); };
 const controls = nodes('input,textarea,select,button,[role="button"]', e => ({
   label: labelFor(e), type: e.tagName==='INPUT' ? (e.getAttribute('type') || 'text') : e.tagName.toLowerCase(),
   required: e.required === true || e.getAttribute('aria-required')==='true', disabled: e.disabled === true || e.getAttribute('aria-disabled')==='true',
   options: e.tagName==='SELECT' ? Array.from(e.options).filter(o=>!o.disabled).map(o=>o.textContent.trim()) : [],
   accept: e.type==='file' ? (e.getAttribute('accept') || '') : '',
   button: (e.tagName==='BUTTON' || e.getAttribute('role')==='button') ? txt(e) : ''
 }));
 return {
   title: document.title,
   headings: nodes('h1,h2,h3,h4,h5,h6,[role="heading"]', txt),
   buttons: controls.map(c=>c.button).filter(Boolean),
   links: nodes('a[href]', e=>({label:txt(e), destination:e.href})),
   controls: controls.filter(c=>c.type!=='button' && c.type!=='[role="button"]'),
   dialogs: nodes('[role="dialog"],dialog[open]', e=>({title:txt(e.querySelector('h1,h2,h3,[role="heading"]') || e), buttons:Array.from(e.querySelectorAll('button,[role="button"]')).filter(visible).map(txt)})),
   navigation: nodes('nav,[role="navigation"]', e=>Array.from(e.querySelectorAll('a,[role="link"]')).filter(visible).map(txt)),
   captcha_present: nodes('iframe, [class*="captcha" i], [id*="captcha" i], [data-sitekey]', e=>({tag:e.tagName, title:e.getAttribute('title')||'', aria:e.getAttribute('aria-label')||'', marker:(e.getAttribute('class')||'')+' '+(e.id||'')})).some(e=>/captcha|recaptcha|hcaptcha/i.test([e.tag,e.title,e.aria,e.marker].join(' ')))
 };
}"""


def _safe_structure(raw):
    title = _safe_label(raw.get("title", ""))
    try:
        url = urlsplit(raw.get("url", ""))
    except ValueError as exc:
        raise InspectionError("The current page URL could not be safely inspected.") from exc
    if url.scheme != "https" or url.hostname != OFFICIAL_HOST:
        raise InspectionError("Inspection is limited to the official IVAC appointment website.")
    path = url.path or "/"
    if not _SAFE_PATH.fullmatch(path) or any(part.casefold() not in _SAFE_WORDS for part in path.split("/") if part):
        path = "/[dynamic path omitted]"
    def labels(items):
        return [_safe_label(item) for item in items]
    links = [{"label": _safe_label(item.get("label", "")), "destination": sanitize_destination(item.get("destination"))} for item in raw.get("links", [])]
    controls = []
    for item in raw.get("controls", []):
        kind = str(item.get("type", "control")).lower()
        if kind == "password" or kind in {"hidden", "file"}:
            # File controls are represented only by their generic label/accepted type.
            if kind != "file":
                continue
        accepted = str(item.get("accept", "")) if kind == "file" else ""
        if accepted and not re.fullmatch(r"[A-Za-z0-9.*+/-]{1,100}(?:,[A-Za-z0-9.*+/-]{1,100})*", accepted):
            accepted = "[omitted]"
        controls.append({"label": _safe_label(item.get("label", "")), "type": kind[:24], "required": bool(item.get("required")), "disabled": bool(item.get("disabled")), "options": labels(item.get("options", [])) if kind == "select" else [], "accepted_file_types": accepted if kind == "file" else ""})
    dialogs = [{"title": _safe_label(d.get("title", "")), "buttons": labels(d.get("buttons", []))} for d in raw.get("dialogs", [])]
    navigation = [labels(group) for group in raw.get("navigation", [])]
    return {"title": title, "hostname": OFFICIAL_HOST, "pathname": path, "headings": labels(raw.get("headings", [])), "buttons": labels(raw.get("buttons", [])), "links": links, "form_controls": controls, "dialogs": dialogs, "navigation": navigation, "captcha_widget_present": bool(raw.get("captcha_present", False))}


def capture_portal_page(session, page_name="Other", timeout_ms=10000):
    """Read visible DOM structure from a valid, app-owned session without interactions."""
    if not isinstance(session, BrowserSession) or not session.is_open:
        raise InspectionError("The application-launched browser session is missing or closed.")
    try:
        current_url = session.page.url
        current = urlsplit(current_url)
        if current.scheme != "https" or current.hostname != OFFICIAL_HOST:
            raise InspectionError("Inspection is limited to the official IVAC appointment website.")
        if hasattr(session.page, "wait_for_load_state"):
            session.page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
        current_url = session.page.url
        current = urlsplit(current_url)
        if current.scheme != "https" or current.hostname != OFFICIAL_HOST:
            raise InspectionError("Inspection is limited to the official IVAC appointment website.")
        raw = session.page.evaluate(_EXTRACT_SCRIPT)
        raw["url"] = current_url
    except InspectionError:
        raise
    except Exception as exc:
        msg = str(exc).casefold()
        if "timeout" in msg:
            raise InspectionError("The page did not finish loading in time. Navigate manually, then try capture again.") from exc
        raise InspectionError("The current page could not be inspected. Check that the browser is still open and try again.") from exc
    if not isinstance(raw, dict):
        raise InspectionError("The page returned an unexpected structure; no report was saved.")
    try:
        structure = _safe_structure(raw)
    except InspectionError:
        raise
    except Exception as exc:
        raise InspectionError("The page returned an unexpected structure; no report was saved.") from exc
    has_visible_text = structure.get("title") not in (None, "", "[omitted]")
    has_visible_text = has_visible_text or any(
        value not in (None, "", "[omitted]")
        for key in ("headings", "buttons")
        for value in structure.get(key, [])
    )
    has_visible_text = has_visible_text or any(
        item.get("label") not in ("", "[omitted]") for item in structure.get("links", [])
    )
    has_visible_text = has_visible_text or any(
        item.get("label") not in ("", "[omitted]") for item in structure.get("form_controls", [])
    )
    has_visible_text = has_visible_text or bool(structure.get("dialogs") or structure.get("navigation"))
    if not has_visible_text:
        raise InspectionError("No visible page structure was found; no report was saved.")
    return {"page_name": _safe_label(page_name), "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "page": structure}


def export_inspection_reports(reports, export_dir=DEFAULT_EXPORT_DIR):
    """Write allowlisted inspection data to a private file outside the repository."""
    try:
        target = Path(export_dir).expanduser().resolve()
        if target == Path.cwd() or Path.cwd() in target.parents:
            raise InspectionError("Choose an export folder outside the project repository.")
        target.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            target.chmod(0o700)
        except OSError:
            pass
        name = f"ivac-inspection-{uuid.uuid4().hex}.json"
        path = target / name
        payload = json.dumps(list(reports), ensure_ascii=False, indent=2)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(payload)
        return path
    except InspectionError:
        raise
    except (OSError, TypeError, ValueError) as exc:
        raise InspectionError("The inspection report could not be exported. Check the folder and its permissions.") from exc


def clear_exported_reports(paths):
    """Remove only report files created and tracked by this app session."""
    removed = 0
    for value in paths:
        try:
            path = Path(value).resolve()
            if path.parent == DEFAULT_EXPORT_DIR.resolve() and path.name.startswith("ivac-inspection-") and path.suffix == ".json":
                path.unlink(missing_ok=True)
                removed += 1
        except OSError:
            continue
    return removed
