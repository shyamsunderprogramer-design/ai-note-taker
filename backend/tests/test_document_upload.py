"""Temporary documents must not collide or survive failed ingestion."""
import importlib
import io
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from lib.document_upload import InvalidDocumentName, staged_document


@pytest.mark.parametrize("filename", [
    None, "", " ", "../secret.txt", "folder/report.pdf", "folder\\report.pdf",
    "/absolute.txt", "report\x00.txt", "report\n.txt", "report.", "report.txt ",
    "C:report.txt", "CON.txt", "LPT1.txt", "a" * 256, "日" * 86 + ".txt",
])
def test_invalid_name_rejected_before_creating_files(tmp_path, filename):
    upload_root = tmp_path / "uploads"
    with pytest.raises(InvalidDocumentName), staged_document(io.BytesIO(b"document"), filename, upload_root):
        pytest.fail("Invalid filename was accepted")
    assert not upload_root.exists()


def test_same_names_use_private_directories_without_overwriting(tmp_path):
    existing = tmp_path / "résumé.txt"
    existing.write_text("existing upload")
    with staged_document(io.BytesIO(b"first"), existing.name, tmp_path) as first:
        with staged_document(io.BytesIO(b"second"), existing.name, tmp_path) as second:
            first, second = Path(first), Path(second)
            assert first != second
            assert first.name == second.name == existing.name
            assert first.read_bytes() == b"first"
            assert second.read_bytes() == b"second"
            if os.name == "posix":
                assert first.parent.stat().st_mode & 0o777 == 0o700
            second_dir = second.parent
        assert not second_dir.exists()
        assert first.read_bytes() == b"first"
        first_dir = first.parent
    assert not first_dir.exists()
    assert existing.read_text() == "existing upload"


class BrokenUpload(io.BytesIO):
    def read(self, size=-1):
        if self.tell():
            raise OSError("sensitive-document-marker")
        return super().read(2)


@pytest.mark.asyncio
@pytest.mark.parametrize("entry", ["routes.conversations", "core.main"])
@pytest.mark.parametrize("failure", [None, "copy", "store", "ingest"])
async def test_upload_route_cleans_every_outcome(monkeypatch, tmp_path, caplog, entry, failure):
    route = importlib.import_module(entry)
    document_store = importlib.import_module("document_store")
    monkeypatch.setattr(route, "UPLOAD_DIR", str(tmp_path))
    staged_paths = []

    def ingest(path):
        staged_paths.append(Path(path))
        assert Path(path).name == "document.txt"
        assert Path(path).read_bytes() == b"synthetic content"
        if failure == "ingest":
            raise RuntimeError("sensitive-document-marker")
        return {"status": "success", "doc_name": Path(path).name}

    def get_store():
        if failure == "store":
            raise RuntimeError("sensitive-document-marker")
        return SimpleNamespace(add_document=ingest)

    monkeypatch.setattr(document_store, "get_document_store", get_store)
    source = BrokenUpload(b"synthetic content") if failure == "copy" else io.BytesIO(b"synthetic content")
    uploaded = SimpleNamespace(filename="document.txt", file=source)
    result = await route.upload_document(uploaded, SimpleNamespace(id="synthetic-user"))
    if failure:
        assert result.status_code == 500
        assert "sensitive-document-marker" not in caplog.text
        assert b"sensitive-document-marker" not in result.body
    else:
        assert result == {"status": "success", "doc_name": "document.txt"}
    assert list(tmp_path.iterdir()) == []
    assert all(not path.parent.exists() for path in staged_paths)


@pytest.mark.asyncio
@pytest.mark.parametrize("entry", ["routes.conversations", "core.main"])
async def test_route_returns_validation_error_for_missing_filename(monkeypatch, tmp_path, entry):
    route = importlib.import_module(entry)
    monkeypatch.setattr(route, "UPLOAD_DIR", str(tmp_path))
    result = await route.upload_document(SimpleNamespace(filename=None, file=io.BytesIO(b"content")), None)
    assert result.status_code == 400
    assert not list(tmp_path.iterdir())
