"""
PDF Processor — Extracts text from PDF books/materials for ingestion.

Uses a 3-tier fallback for maximum compatibility:
1. pdfplumber (best for structured/technical PDFs)
2. PyPDF2 (widely available fallback)
3. Raw binary decode (last resort)
"""

import os
import logging
from typing import List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("agents.ingestion.pdf_processor")


@dataclass
class PDFContent:
    """Extracted content from a single PDF file."""
    file_name: str
    file_path: str
    text: str
    page_count: int = 0
    extraction_method: str = ""
    error: str = ""

    @property
    def is_empty(self) -> bool:
        return len(self.text.strip()) < 50


class PDFProcessor:
    """Extract text from PDF files with multiple fallback strategies."""

    def extract_text(self, file_path: str) -> PDFContent:
        """Extract text from a single PDF file.

        Tries pdfplumber first, then PyPDF2, then raw decode.

        Args:
            file_path: Path to the PDF file

        Returns:
            PDFContent with extracted text and metadata
        """
        file_name = os.path.basename(file_path)
        content = PDFContent(file_name=file_name, file_path=file_path, text="")

        if not os.path.exists(file_path):
            content.error = f"File not found: {file_path}"
            return content

        # Tier 1: pdfplumber (best for technical PDFs with tables/diagrams)
        text, pages, method = self._extract_with_pdfplumber(file_path)
        if text and len(text.strip()) > 50:
            content.text = text
            content.page_count = pages
            content.extraction_method = method
            return content

        # Tier 2: PyPDF2 (widely available)
        text, pages, method = self._extract_with_pypdf2(file_path)
        if text and len(text.strip()) > 50:
            content.text = text
            content.page_count = pages
            content.extraction_method = method
            return content

        # Tier 3: Raw binary decode (for text-based PDFs)
        text, pages, method = self._extract_raw(file_path)
        if text and len(text.strip()) > 50:
            content.text = text
            content.page_count = pages
            content.extraction_method = method
            return content

        content.error = "All extraction methods failed or produced insufficient text"
        logger.warning(f"[PDFProcessor] Failed to extract meaningful text from {file_name}")
        return content

    def extract_from_directory(self, dir_path: str) -> List[PDFContent]:
        """Extract text from all PDF files in a directory.

        Args:
            dir_path: Path to directory containing PDF files

        Returns:
            List of PDFContent objects (one per PDF)
        """
        contents = []

        if not os.path.isdir(dir_path):
            logger.error(f"[PDFProcessor] Not a directory: {dir_path}")
            return contents

        pdf_files = sorted([
            f for f in os.listdir(dir_path)
            if f.lower().endswith(".pdf")
        ])

        logger.info(f"[PDFProcessor] Found {len(pdf_files)} PDF files in {dir_path}")

        for pdf_file in pdf_files:
            file_path = os.path.join(dir_path, pdf_file)
            try:
                content = self.extract_text(file_path)
                contents.append(content)
                if content.is_empty:
                    logger.warning(f"[PDFProcessor] Empty result: {pdf_file}")
                else:
                    logger.debug(f"[PDFProcessor] Extracted {len(content.text)} chars from {pdf_file} via {content.extraction_method}")
            except Exception as e:
                logger.error("[PDFProcessor] Error processing {pdf_file}: %s", str(e))
                contents.append(PDFContent(
                    file_name=pdf_file,
                    file_path=file_path,
                    text="",
                    error="An internal error occurred",
                ))

        successful = sum(1 for c in contents if not c.is_empty)
        logger.info(f"[PDFProcessor] Successfully extracted {successful}/{len(contents)} PDFs")
        return contents

    def _extract_with_pdfplumber(self, file_path: str) -> tuple:
        """Extract text using pdfplumber. Best for technical PDFs."""
        try:
            import pdfplumber

            text_parts = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)

            text = "\n\n".join(text_parts)
            return text, len(text_parts), "pdfplumber"
        except ImportError:
            return "", 0, ""
        except Exception as e:
            logger.debug("[PDFProcessor] pdfplumber failed: %s", str(e))
            return "", 0, ""

    def _extract_with_pypdf2(self, file_path: str) -> tuple:
        """Extract text using PyPDF2. Widely available fallback."""
        try:
            from PyPDF2 import PdfReader

            reader = PdfReader(file_path)
            text_parts = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

            text = "\n\n".join(text_parts)
            return text, len(reader.pages), "pypdf2"
        except ImportError:
            return "", 0, ""
        except Exception as e:
            logger.debug("[PDFProcessor] PyPDF2 failed: %s", str(e))
            return "", 0, ""

    def _extract_raw(self, file_path: str) -> tuple:
        """Last resort: decode PDF as raw text."""
        try:
            with open(file_path, "rb") as f:
                raw = f.read()

            # Try latin-1 decode (catches text streams in simple PDFs)
            text = raw.decode("latin-1", errors="ignore")

            # Filter to readable lines (ignore binary noise)
            lines = []
            for line in text.split("\n"):
                line = line.strip()
                # Skip lines that are mostly non-printable
                printable = sum(1 for c in line if c.isprintable())
                if len(line) > 10 and printable / len(line) > 0.8:
                    lines.append(line)

            return "\n".join(lines), 0, "raw_decode"
        except Exception as e:
            logger.debug("[PDFProcessor] Raw decode failed: %s", str(e))
            return "", 0, ""