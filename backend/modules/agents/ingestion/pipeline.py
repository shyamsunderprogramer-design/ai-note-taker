"""
Ingestion Pipeline — Orchestrates the full data ingestion from GitHub repos
to Cognitive Graph and Document RAG.

Supports:
- Local directory ingestion
- GitHub repo cloning + ingestion
- Graph-only or RAG-only modes
- Dry run (parse but don't load)
"""

import logging
import os
import shutil
import subprocess  # nosec B404
import tempfile
import time
from typing import List, Optional
from dataclasses import dataclass, field

from agents.ingestion.markdown_parser import MarkdownQAParser
from agents.ingestion.pdf_processor import PDFProcessor
from agents.ingestion.graph_loader import GraphLoader
from agents.ingestion.rag_loader import RAGLoader

logger = logging.getLogger("agents.ingestion.pipeline")


@dataclass
class IngestionStats:
    """Statistics from a full ingestion run."""
    repos_processed: int = 0
    qa_pairs_found: int = 0
    qa_pairs_loaded_graph: int = 0
    qa_pairs_loaded_rag: int = 0
    qa_pairs_cached: int = 0
    pdfs_processed: int = 0
    pdfs_loaded_rag: int = 0
    graph_nodes_created: int = 0
    rag_chunks_created: int = 0
    errors: List[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0

    def to_dict(self) -> dict:
        return {
            "repos_processed": self.repos_processed,
            "qa_pairs_found": self.qa_pairs_found,
            "qa_pairs_loaded_graph": self.qa_pairs_loaded_graph,
            "qa_pairs_loaded_rag": self.qa_pairs_loaded_rag,
            "qa_pairs_cached": self.qa_pairs_cached,
            "pdfs_processed": self.pdfs_processed,
            "pdfs_loaded_rag": self.pdfs_loaded_rag,
            "graph_nodes_created": self.graph_nodes_created,
            "rag_chunks_created": self.rag_chunks_created,
            "errors": self.errors,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
        }


class IngestionPipeline:
    """Orchestrate the full ingestion from repos to data stores."""

    def __init__(self):
        self.markdown_parser = MarkdownQAParser()
        self.pdf_processor = PDFProcessor()
        self.graph_loader = GraphLoader()
        self.rag_loader = RAGLoader()

    def ingest_from_local(
        self,
        repo_paths: List[str],
        mode: str = "full",
        dry_run: bool = False,
    ) -> IngestionStats:
        """Ingest from locally cloned repos.

        Args:
            repo_paths: List of paths to cloned repo directories
            mode: "full", "graph_only", or "rag_only"
            dry_run: If True, parse but don't load into data stores

        Returns:
            IngestionStats with results
        """
        stats = IngestionStats()
        start_time = time.time()

        for repo_path in repo_paths:
            if not os.path.isdir(repo_path):
                stats.errors.append(f"Not a directory: {repo_path}")
                continue

            logger.info(f"[Pipeline] Processing repo: {repo_path}")
            repo_type = MarkdownQAParser.detect_repo_type(repo_path)
            logger.info(f"[Pipeline] Detected repo type: {repo_type}")

            if repo_type == "qa_markdown":
                qa_pairs = self.markdown_parser.parse_repo(repo_path)
                stats.qa_pairs_found += len(qa_pairs)
                logger.info(f"[Pipeline] Parsed {len(qa_pairs)} Q&A pairs")

                if dry_run:
                    logger.info("[Pipeline] Dry run — skipping data store loading")
                    for qa in qa_pairs[:3]:
                        logger.info(f"  Sample: Q#{qa.number} [{qa.difficulty}] {qa.question[:80]}...")
                    if len(qa_pairs) > 3:
                        logger.info(f"  ... and {len(qa_pairs) - 3} more")
                else:
                    self._load_qa_pairs(qa_pairs, mode, stats)

            elif repo_type == "pdf_books":
                pdf_contents = self.pdf_processor.extract_from_directory(repo_path)
                stats.pdfs_processed += len(pdf_contents)
                successful = sum(1 for p in pdf_contents if not p.is_empty)
                logger.info(f"[Pipeline] Extracted {successful}/{len(pdf_contents)} PDFs")

                if dry_run:
                    logger.info("[Pipeline] Dry run — skipping data store loading")
                    for pdf in pdf_contents[:3]:
                        if not pdf.is_empty:
                            logger.info(f"  Sample: {pdf.file_name} ({len(pdf.text)} chars via {pdf.extraction_method})")
                else:
                    self._load_pdf_content(pdf_contents, mode, stats)

            else:
                # Unknown type — try both markdown and PDF
                logger.warning(f"[Pipeline] Unknown repo type for {repo_path}, trying both")
                qa_pairs = self.markdown_parser.parse_repo(repo_path)
                stats.qa_pairs_found += len(qa_pairs)

                pdf_contents = self.pdf_processor.extract_from_directory(repo_path)
                stats.pdfs_processed += len(pdf_contents)

                if not dry_run:
                    if qa_pairs:
                        self._load_qa_pairs(qa_pairs, mode, stats)
                    if pdf_contents:
                        self._load_pdf_content(pdf_contents, mode, stats)

            stats.repos_processed += 1

        stats.elapsed_seconds = time.time() - start_time
        logger.info(
            f"[Pipeline] Complete: {stats.repos_processed} repos, "
            f"{stats.qa_pairs_found} Q&A found, "
            f"{stats.qa_pairs_loaded_graph} loaded to graph, "
            f"{stats.qa_pairs_loaded_rag} loaded to RAG, "
            f"{stats.pdfs_processed} PDFs processed, "
            f"{len(stats.errors)} errors in {stats.elapsed_seconds:.1f}s"
        )
        return stats

    def ingest_from_github(
        self,
        repo_urls: List[str],
        clone_dir: str = None,
        mode: str = "full",
        dry_run: bool = False,
    ) -> IngestionStats:
        """Clone repos from GitHub and ingest.

        Args:
            repo_urls: List of GitHub repo URLs or "owner/repo" strings
            clone_dir: Directory to clone repos into (default: temp dir)
            mode: "full", "graph_only", or "rag_only"
            dry_run: If True, parse but don't load

        Returns:
            IngestionStats with results
        """
        stats = IngestionStats()
        temp_dir = None
        local_paths = []

        # Create clone directory
        if clone_dir:
            os.makedirs(clone_dir, exist_ok=True)
        else:
            temp_dir = tempfile.mkdtemp(prefix="ingestion_clone_")
            clone_dir = temp_dir

        try:
            for repo_url in repo_urls:
                # Normalize URL
                if not repo_url.startswith("http"):
                    repo_url = f"https://github.com/{repo_url}"

                # Extract repo name for local directory
                repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
                local_path = os.path.join(clone_dir, repo_name)

                logger.info(f"[Pipeline] Cloning {repo_url} to {local_path}")

                try:
                    result = subprocess.run(  # nosec B603
                        ["git", "clone", "--depth", "1", "--filter=blob:none", repo_url, local_path],
                        capture_output=True,
                        text=True,
                        timeout=300,
                    )
                    if result.returncode != 0:
                        # If clone failed because dir already exists, try to use it
                        if os.path.isdir(local_path):
                            logger.warning(f"[Pipeline] Using existing directory: {local_path}")
                        else:
                            stats.errors.append(f"Clone failed for {repo_url}: {result.stderr}")
                            continue
                except subprocess.TimeoutExpired:
                    stats.errors.append(f"Clone timeout for {repo_url}")
                    continue
                except FileNotFoundError:
                    stats.errors.append("git not found — install git or use local paths")
                    break

                local_paths.append(local_path)

            if local_paths:
                stats = self.ingest_from_local(local_paths, mode=mode, dry_run=dry_run)

        finally:
            # Clean up temp directory (best-effort on Windows)
            if temp_dir and os.path.isdir(temp_dir):
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception:
                    pass  # nosec B110

        return stats

    def _load_qa_pairs(self, qa_pairs: list, mode: str, stats: IngestionStats):
        """Load Q&A pairs into the appropriate data stores."""
        if mode in ("full", "graph_only"):
            graph_stats = self.graph_loader.load_qa_pairs(qa_pairs)
            stats.qa_pairs_loaded_graph += graph_stats.loaded
            stats.qa_pairs_cached += graph_stats.cached
            stats.graph_nodes_created += graph_stats.nodes_created
            for i in range(graph_stats.errors):
                stats.errors.append(f"Graph loader error (Q&A batch)")

        if mode in ("full", "rag_only"):
            rag_stats = self.rag_loader.load_qa_pairs(qa_pairs)
            stats.qa_pairs_loaded_rag += rag_stats.loaded
            stats.rag_chunks_created += rag_stats.chunks_created
            for i in range(rag_stats.errors):
                stats.errors.append(f"RAG loader error (Q&A batch)")

    def _load_pdf_content(self, pdf_contents: list, mode: str, stats: IngestionStats):
        """Load PDF content into the appropriate data stores."""
        # PDFs go into RAG only (they're not Q&A format for the graph)
        if mode in ("full", "rag_only"):
            rag_stats = self.rag_loader.load_pdf_content(pdf_contents)
            stats.pdfs_loaded_rag += rag_stats.loaded
            stats.rag_chunks_created += rag_stats.chunks_created
            for i in range(rag_stats.errors):
                stats.errors.append(f"RAG loader error (PDF batch)")