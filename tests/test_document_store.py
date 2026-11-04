import json
import os
from pathlib import Path
import stat

import pytest

from modules.document_store import APPLICANT_SLOTS, LocalDocumentStore, cleanup_current_process_sessions, cleanup_stale_sessions, default_cache_root


def pdf_bytes(marker=b"synthetic"):
    return b"%PDF-1.7\n% fictional test document " + marker + b"\n%%EOF\n"


def test_store_saves_original_bytes_outside_repository_and_shows_metadata(tmp_path):
    root = tmp_path / "application-cache"
    store = LocalDocumentStore(cache_root=root)
    raw = pdf_bytes()
    saved = store.save(0, "fictional-webfile.pdf", raw)
    assert saved.original_name == "fictional-webfile.pdf"
    assert saved.size_bytes == len(raw)
    assert saved.path.read_bytes() == raw
    assert saved.path.parent == store.session_dir
    assert ".git" not in saved.path.parts
    if os.name == "posix":
        assert stat.S_IMODE(root.stat().st_mode) == 0o700
        assert stat.S_IMODE(store.session_dir.stat().st_mode) == 0o700
        assert stat.S_IMODE(saved.path.stat().st_mode) == 0o600
        assert stat.S_IMODE((store.session_dir / ".owner.json").stat().st_mode) == 0o600
    store.close()
    assert not store.session_dir.exists()


def test_default_cache_is_outside_the_project_checkout():
    repository = Path.cwd().resolve()
    cache_path = default_cache_root().resolve()
    assert cache_path != repository
    assert repository not in cache_path.parents


@pytest.mark.parametrize("slot", [-1, APPLICANT_SLOTS, True, "0"])
def test_store_rejects_invalid_or_more_than_four_slots(tmp_path, slot):
    store = LocalDocumentStore(cache_root=tmp_path / "cache")
    with pytest.raises(ValueError, match="four applicant slots"):
        store.save(slot, "fictional.pdf", pdf_bytes())
    store.close()


@pytest.mark.parametrize("filename,content,message", [
    ("document.txt", pdf_bytes(), "PDF file"),
    ("fake.pdf", b"not a pdf", "PDF header"),
    ("empty.pdf", b"", "empty"),
    ("large.pdf", b"%PDF-1.7\n" + b"x" * (15 * 1024 * 1024), "15 MB"),
], ids=["non_pdf_extension", "invalid_header", "empty", "oversized"])
def test_store_rejects_non_pdf_empty_or_oversized_uploads(tmp_path, filename, content, message):
    store = LocalDocumentStore(cache_root=tmp_path / "cache")
    with pytest.raises(ValueError, match=message):
        store.save(0, filename, content)
    assert not store.documents
    assert not list(store.session_dir.glob("*.pdf"))
    store.close()


def test_replacing_and_removing_a_pdf_cleans_the_previous_copy(tmp_path):
    store = LocalDocumentStore(cache_root=tmp_path / "cache")
    first = store.save(0, "first.pdf", pdf_bytes(b"first"))
    replacement = store.save(0, "replacement.pdf", pdf_bytes(b"replacement"))
    assert replacement.path.exists()
    assert not first.path.exists()
    assert store.documents[0] == replacement
    assert store.remove(0)
    assert not replacement.path.exists()
    assert not store.remove(0)
    store.close()


def test_optional_secondary_slots_can_be_added_removed_and_clear_all_unlinks_files(tmp_path):
    store = LocalDocumentStore(cache_root=tmp_path / "cache")
    primary = store.save(0, "primary.pdf", pdf_bytes(b"primary"))
    secondary = store.save(3, "secondary.pdf", pdf_bytes(b"secondary"))
    assert set(store.documents) == {0, 3}
    assert store.remove(3)
    assert not secondary.path.exists()
    store.save(1, "secondary-one.pdf", pdf_bytes(b"secondary-one"))
    orphan = store.session_dir / "orphan.pdf"
    orphan.write_bytes(pdf_bytes(b"orphan"))
    assert store.clear_all() == 2
    assert not primary.path.exists()
    assert not orphan.exists()
    assert not store.documents
    assert store.session_dir.exists()
    store.close()


def test_stale_abandoned_session_is_cleaned_on_startup(tmp_path):
    root = tmp_path / "cache"
    stale = root / "session-abandoned"
    stale.mkdir(parents=True)
    (stale / ".owner.json").write_text(json.dumps({"pid": 0, "created_at": 1}), encoding="utf-8")
    (stale / "fictional.pdf").write_bytes(pdf_bytes())
    assert cleanup_stale_sessions(root) == 1
    assert not stale.exists()


def test_live_session_is_not_removed_by_stale_cleanup(tmp_path):
    store = LocalDocumentStore(cache_root=tmp_path / "cache")
    store.save(0, "primary.pdf", pdf_bytes())
    assert cleanup_stale_sessions(store.cache_root) == 0
    assert store.documents[0].path.exists()
    store.close()


def test_process_shutdown_cleanup_removes_all_owned_sessions(tmp_path):
    store = LocalDocumentStore(cache_root=tmp_path / "cache")
    store.save(0, "primary.pdf", pdf_bytes())
    session_dir = store.session_dir
    cleanup_current_process_sessions()
    assert not session_dir.exists()
