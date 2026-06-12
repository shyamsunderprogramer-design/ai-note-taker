"""
RAG Loader — Loads Q&A pairs and PDF content into the DocumentStore for
retrieval-augmented generation.

Each Q&A pair becomes a document with formatted text. PDF content is chunked
and embedded using the existing DocumentStore pipeline.
"""

import hashlib
import logging
import os
import tempfile
import time
from typing import List, Dict, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("agents.ingestion.rag_loader")

# Re-export for convenience
from modules.agents.ingestion.markdown_parser import ParsedQA
from modules.agents.ingestion.pdf_processor import PDFContent


@dataclass
class RAGLoadStats:
    """Statistics from a RAG loading operation."""
    total_items: int = 0
    loaded: int = 0
    skipped_duplicates: int = 0
    errors: int = 0
    chunks_created: int = 0
    elapsed_seconds: float = 0.0

    def to_dict(self) -> dict:
        return {
            "total_items": self.total_items,
            "loaded": self.loaded,
            "skipped_duplicates": self.skipped_duplicates,
            "errors": self.errors,
            "chunks_created": self.chunks_created,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
        }


class RAGLoader:
    """Load Q&A pairs and PDF content into DocumentStore (RAG)."""

    def __init__(self):
        self._doc_store = None
        self._loaded_hashes: set = set()

    @property
    def doc_store(self):
        """Lazy-load DocumentStore singleton."""
        if self._doc_store is None:
            try:
                from ai.document_store import doc_store
                self._doc_store = doc_store
            except ImportError:
                try:
                    from modules.platform.document_store import doc_store
                    self._doc_store = doc_store
                except ImportError:
                    from backend.modules.platform.document_store import doc_store
                    self._doc_store = doc_store
        return self._doc_store

    def load_qa_pairs(self, qa_pairs: list) -> RAGLoadStats:
        """Load Q&A pairs into the document store.

        Each Q&A pair is formatted as a single text document and added via
        the existing add_document() pipeline (chunk → embed → store).

        Args:
            qa_pairs: List of ParsedQA objects from markdown_parser

        Returns:
            RAGLoadStats with loading statistics
        """
        stats = RAGLoadStats(total_items=len(qa_pairs))
        start_time = time.time()

        for qa in qa_pairs:
            if not isinstance(qa, ParsedQA):
                stats.errors += 1
                continue

            # Dedup by hash of question text
            content_hash = self._content_hash(qa.full_text())
            if content_hash in self._loaded_hashes:
                stats.skipped_duplicates += 1
                continue
            self._loaded_hashes.add(content_hash)

            try:
                result = self._add_qa_document(qa)
                if result.get("status") == "success":
                    stats.loaded += 1
                    stats.chunks_created += result.get("chunks", 0)
                elif result.get("status") == "already_exists":
                    stats.skipped_duplicates += 1
                else:
                    stats.errors += 1
                    logger.debug(f"[RAGLoader] Failed to load Q#{qa.number}: {result}")
            except Exception as e:
                logger.error("[RAGLoader] Error loading Q#{qa.number} from {qa.category}: %s", str(e))
                stats.errors += 1

        stats.elapsed_seconds = time.time() - start_time
        logger.info(
            f"[RAGLoader] Done: {stats.loaded} loaded, "
            f"{stats.skipped_duplicates} dupes, {stats.errors} errors, "
            f"{stats.chunks_created} chunks in {stats.elapsed_seconds:.1f}s"
        )
        return stats

    def load_pdf_content(self, pdf_contents: list) -> RAGLoadStats:
        """Load PDF content into the document store.

        Each PDF is added as a document via the add_document() pipeline.

        Args:
            pdf_contents: List of PDFContent objects from pdf_processor

        Returns:
            RAGLoadStats with loading statistics
        """
        stats = RAGLoadStats(total_items=len(pdf_contents))
        start_time = time.time()

        for pdf in pdf_contents:
            if not isinstance(pdf, PDFContent):
                stats.errors += 1
                continue

            if pdf.is_empty:
                logger.warning(f"[RAGLoader] Skipping empty PDF: {pdf.file_name}")
                stats.skipped_duplicates += 1
                continue

            # Dedup by hash of extracted text
            content_hash = self._content_hash(pdf.text)
            if content_hash in self._loaded_hashes:
                stats.skipped_duplicates += 1
                continue
            self._loaded_hashes.add(content_hash)

            try:
                result = self._add_pdf_document(pdf)
                if result.get("status") == "success":
                    stats.loaded += 1
                    stats.chunks_created += result.get("chunks", 0)
                elif result.get("status") == "already_exists":
                    stats.skipped_duplicates += 1
                else:
                    stats.errors += 1
                    logger.debug(f"[RAGLoader] Failed to load PDF {pdf.file_name}: {result}")
            except Exception as e:
                logger.error("[RAGLoader] Error loading PDF {pdf.file_name}: %s", str(e))
                stats.errors += 1

        stats.elapsed_seconds = time.time() - start_time
        logger.info(
            f"[RAGLoader] PDF loading done: {stats.loaded} loaded, "
            f"{stats.skipped_duplicates} skipped, {stats.errors} errors, "
            f"{stats.chunks_created} chunks in {stats.elapsed_seconds:.1f}s"
        )
        return stats

    def _add_qa_document(self, qa) -> dict:
        """Add a Q&A pair as a temporary document to the DocumentStore.

        Creates a temporary .txt file with the formatted Q&A text and
        feeds it through the existing add_document() pipeline.
        """
        doc_name = f"qa_{qa.category}_{qa.number}.txt"
        content = qa.full_text()

        # Write to temp file and let add_document() handle it
        return self._add_text_as_file(content, doc_name)

    def _add_pdf_document(self, pdf_content) -> dict:
        """Add PDF content as a temporary document to the DocumentStore.

        Creates a temporary .txt file with the extracted text and
        feeds it through the existing add_document() pipeline.
        """
        doc_name = f"pdf_{pdf_content.file_name.replace('.pdf', '')}.txt"
        return self._add_text_as_file(pdf_content.text, doc_name)

    def _add_text_as_file(self, text: str, doc_name: str) -> dict:
        """Write text to a temp file and add via DocumentStore.add_document()."""
        ds = self.doc_store
        if ds is None:
            return {"error": "DocumentStore not available"}

        # Create a temp file with the content
        tmp_dir = tempfile.mkdtemp(prefix="ingestion_")
        tmp_path = os.path.join(tmp_dir, doc_name)

        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(text)

            result = ds.add_document(tmp_path)
            return result
        except Exception as e:
            logger.error("[RAGLoader] Error adding document {doc_name}: %s", str(e))
            return {"error": "An internal error occurred"}
        finally:
            # Clean up temp file (best-effort on Windows)
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                if os.path.isdir(tmp_dir):
                    os.rmdir(tmp_dir)
            except OSError:
                pass

    @staticmethod
    def _content_hash(text: str) -> str:
        """Generate hash of content for deduplication (non-cryptographic)."""
        normalized = " ".join(text.lower().strip().split())
        return hashlib.md5(normalized.encode()).hexdigest()[:16]  # nosec B324 — used for deduplication, not security

    def get_loaded_count(self) -> int:
        """Get the total number of items loaded in this session."""
        return len(self._loaded_hashes)