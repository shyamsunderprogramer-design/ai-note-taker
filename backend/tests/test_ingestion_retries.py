from pathlib import Path
from types import SimpleNamespace

import pytest

from modules.agents.ingestion import rag_loader
from modules.agents.ingestion.markdown_parser import ParsedQA
from modules.agents.ingestion.pdf_processor import PDFContent


@pytest.mark.parametrize("kind", ["qa", "pdf"])
@pytest.mark.parametrize("failure", ["exception", "error_response"])
def test_failed_import_can_retry_then_deduplicates(kind, failure):
    loader = rag_loader.RAGLoader()
    calls = []

    def add_document(path):
        calls.append(path)
        if len(calls) == 1:
            if failure == "exception":
                raise RuntimeError("synthetic ingestion failure")
            return {"status": "error"}
        return {"status": "success", "chunks": 2}

    loader._doc_store = SimpleNamespace(add_document=add_document)
    if kind == "qa":
        value = ParsedQA("What is CI/CD?", "Build, test, deploy.", 1, "CI/CD", "beginner", "source.md")
        load = lambda: loader.load_qa_pairs([value])
    else:
        value = PDFContent("notes.pdf", "unused.pdf", "Synthetic reference text. " * 5)
        load = lambda: loader.load_pdf_content([value])
    assert load().errors == 1
    second = load()
    assert second.loaded == 1
    assert second.chunks_created == 2
    assert load().skipped_duplicates == 1
    assert len(calls) == 2
    assert all(not Path(path).parent.exists() for path in calls)


@pytest.mark.parametrize("name", ["qa_CI/CD_1.txt", "../../outside.txt", "C:\\outside.txt", "CON", "résumé.txt", "参考" * 100 + ".txt"])
def test_staging_stays_inside_temp_directory_and_cleans_sidecars(name):
    loader = rag_loader.RAGLoader()
    paths = []

    def add_document(path):
        path = Path(path)
        paths.append(path)
        assert path.parent.name.startswith("ingestion_")
        assert path.suffix == ".txt"
        assert len(path.name.encode("utf-8")) < 255
        assert path.read_text() == "Synthetic document content"
        path.with_suffix(".sidecar").write_text("Synthetic derived content")
        return {"status": "success"}

    loader._doc_store = SimpleNamespace(add_document=add_document)
    assert loader._add_text_as_file("Synthetic document content", name) == {"status": "success"}
    assert len(paths) == 1
    assert not paths[0].parent.exists()


def test_cleanup_failure_is_reported_without_logging_source_data(monkeypatch, tmp_path, caplog):
    class FailingCleanup:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return str(tmp_path)

        def __exit__(self, *args):
            raise OSError("synthetic-private-source-text")

    monkeypatch.setattr(rag_loader.tempfile, "TemporaryDirectory", FailingCleanup)
    loader = rag_loader.RAGLoader()
    loader._doc_store = SimpleNamespace(add_document=lambda path: {"status": "success"})
    result = loader._add_text_as_file("synthetic-private-source-text", "private-title.txt")
    assert "error" in result
    assert "temporary cleanup failed" in caplog.text
    assert "synthetic-private-source-text" not in caplog.text
    assert "private-title" not in caplog.text
