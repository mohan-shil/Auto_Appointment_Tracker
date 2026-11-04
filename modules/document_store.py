"""Private, temporary local storage for unmodified applicant PDFs."""

import atexit
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
from typing import Dict, Optional
from uuid import uuid4


APPLICANT_SLOTS = 4
MAX_PDF_BYTES = 15 * 1024 * 1024
STALE_AFTER_SECONDS = 30 * 24 * 60 * 60
_ACTIVE_SESSION_DIRS = set()
_CLEANUP_REGISTERED = False


class DocumentStoreError(ValueError):
    """A safe message for an invalid or un-storable applicant document."""


@dataclass(frozen=True)
class SavedDocument:
    slot: int
    original_name: str
    size_bytes: int
    path: Path
    sha256: str


def default_cache_root() -> Path:
    """Return an application cache location outside the project checkout."""
    return Path(tempfile.gettempdir()) / "auto-appointment-tracker" / str(getattr(os, "getuid", lambda: "user")())


def _chmod(path: Path, mode: int) -> None:
    try:
        path.chmod(mode)
    except OSError as exc:
        if os.name == "posix":
            raise DocumentStoreError("Could not restrict access to the temporary document folder.") from exc


def _secure_directory(path: Path, mode: int) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True, mode=mode)
    except OSError as exc:
        raise DocumentStoreError("Could not create the private temporary document folder.") from exc
    _chmod(path, mode)
    if os.name == "posix" and path.stat().st_mode & 0o077:
        raise DocumentStoreError("The temporary document folder is accessible to other local users.")


def _pid_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False


def cleanup_stale_sessions(cache_root: Optional[Path] = None, stale_after_seconds: int = STALE_AFTER_SECONDS) -> int:
    """Remove abandoned sessions whose owning process is gone or metadata is stale."""
    root = Path(cache_root) if cache_root is not None else default_cache_root()
    if not root.exists():
        return 0
    now = time.time()
    removed = 0
    for candidate in root.iterdir():
        if not candidate.is_dir() or not candidate.name.startswith("session-"):
            continue
        if candidate.resolve() in _ACTIVE_SESSION_DIRS:
            continue
        marker = candidate / ".owner.json"
        try:
            metadata = json.loads(marker.read_text(encoding="utf-8"))
            pid = int(metadata.get("pid", -1))
            age = now - float(metadata.get("created_at", candidate.stat().st_mtime))
            abandoned = not _pid_is_running(pid)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            try:
                age = now - candidate.stat().st_mtime
            except OSError:
                continue
            abandoned = age >= stale_after_seconds
        if abandoned or age >= stale_after_seconds and not _pid_is_running(pid):
            shutil.rmtree(candidate, ignore_errors=True)
            if not candidate.exists():
                removed += 1
    return removed


def _cleanup_owned_sessions() -> None:
    for session_dir in tuple(_ACTIVE_SESSION_DIRS):
        shutil.rmtree(session_dir, ignore_errors=True)
        _ACTIVE_SESSION_DIRS.discard(session_dir)


def cleanup_current_process_sessions() -> None:
    """Remove all document sessions created by this process (also registered at exit)."""
    _cleanup_owned_sessions()


def _register_cleanup() -> None:
    global _CLEANUP_REGISTERED
    if not _CLEANUP_REGISTERED:
        atexit.register(_cleanup_owned_sessions)
        _CLEANUP_REGISTERED = True


class LocalDocumentStore:
    """A session-scoped, permission-restricted store that never parses PDF data."""

    def __init__(self, cache_root: Optional[Path] = None, session_id: Optional[str] = None):
        self.cache_root = Path(cache_root) if cache_root is not None else default_cache_root()
        _secure_directory(self.cache_root, 0o700)
        cleanup_stale_sessions(self.cache_root)
        session_name = "session-" + (session_id or uuid4().hex)
        if Path(session_name).name != session_name or not session_name.startswith("session-"):
            raise DocumentStoreError("Invalid local session identifier.")
        self.session_dir = self.cache_root / session_name
        _secure_directory(self.session_dir, 0o700)
        self.documents: Dict[int, SavedDocument] = {}
        self._write_owner_marker()
        _ACTIVE_SESSION_DIRS.add(self.session_dir.resolve())
        _register_cleanup()

    def _write_owner_marker(self) -> None:
        marker = self.session_dir / ".owner.json"
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        try:
            fd = os.open(str(marker), flags, 0o600)
        except OSError as exc:
            raise DocumentStoreError("Could not initialize the private temporary session.") from exc
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump({"pid": os.getpid(), "created_at": time.time()}, stream)
                stream.flush()
                os.fsync(stream.fileno())
        finally:
            _chmod(marker, 0o600)

    def save(self, slot: int, filename: str, content: bytes) -> SavedDocument:
        """Store exact PDF bytes; replacing a slot removes its previous saved copy."""
        if not isinstance(slot, int) or isinstance(slot, bool) or not 0 <= slot < APPLICANT_SLOTS:
            raise DocumentStoreError("Choose one of the four applicant slots.")
        if not isinstance(filename, str) or Path(filename).suffix.casefold() != ".pdf":
            raise DocumentStoreError("Choose a PDF file for this applicant.")
        if not isinstance(content, bytes) or not content:
            raise DocumentStoreError("The selected PDF is empty.")
        if len(content) > MAX_PDF_BYTES:
            raise DocumentStoreError("The PDF exceeds the 15 MB file limit.")
        if b"%PDF-" not in content[:1024]:
            raise DocumentStoreError("The selected file does not have a valid PDF header.")

        digest = hashlib.sha256(content).hexdigest()
        previous = self.documents.get(slot)
        if previous and previous.sha256 == digest and previous.original_name == Path(filename).name:
            return previous

        safe_path = self.session_dir / (uuid4().hex + ".pdf")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        try:
            fd = os.open(str(safe_path), flags, 0o600)
        except OSError as exc:
            raise DocumentStoreError("Could not save the PDF in temporary storage. Check disk space and permissions.") from exc
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            _chmod(safe_path, 0o600)
        except Exception as exc:
            safe_path.unlink(missing_ok=True)
            if isinstance(exc, OSError):
                raise DocumentStoreError("Could not save the PDF in temporary storage. Check disk space and permissions.") from exc
            raise

        display_name = filename.replace("\\", "/").rsplit("/", 1)[-1]
        document = SavedDocument(slot, display_name, len(content), safe_path, digest)
        if previous:
            try:
                previous.path.unlink(missing_ok=True)
            except OSError as exc:
                safe_path.unlink(missing_ok=True)
                raise DocumentStoreError("The previous PDF could not be replaced. Check temporary storage permissions.") from exc
        self.documents[slot] = document
        return document

    def remove(self, slot: int) -> bool:
        """Remove one applicant file and forget its display metadata."""
        document = self.documents.get(slot)
        if document is None:
            return False
        try:
            document.path.unlink(missing_ok=True)
        except OSError as exc:
            raise DocumentStoreError("Could not remove the selected PDF from temporary storage.") from exc
        self.documents.pop(slot, None)
        return True

    def clear_all(self) -> int:
        """Unlink every stored PDF while retaining this session for future uploads."""
        count = len(self.documents)
        for candidate in self.session_dir.iterdir():
            if candidate.name == ".owner.json":
                continue
            if candidate.is_file() or candidate.is_symlink():
                try:
                    candidate.unlink(missing_ok=True)
                except OSError as exc:
                    raise DocumentStoreError("Some PDFs could not be removed from temporary storage.") from exc
        self.documents.clear()
        return count

    def close(self) -> None:
        """Delete this session's temporary files and release it from process cleanup."""
        try:
            shutil.rmtree(self.session_dir)
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise DocumentStoreError("Could not remove the temporary session folder. Check local permissions.") from exc
        _ACTIVE_SESSION_DIRS.discard(self.session_dir.resolve())
        self.documents.clear()
