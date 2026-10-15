"""
Interview Data Ingestion — Loads interview Q&A and reference materials
into the Cognitive Graph and Document RAG from GitHub repositories.

Modules:
  - markdown_parser: Parse Q&A from DevOps-Interview-Questions1 Markdown files
  - pdf_processor: Extract text from PDF books/materials
  - graph_loader: Load Q&A into CognitiveGraph (Neo4j)
  - rag_loader: Load content into DocumentStore (RAG)
  - pipeline: Orchestrate the full ingestion pipeline
  - cli: Command-line entry point
"""

from modules.agents.ingestion.markdown_parser import MarkdownQAParser, ParsedQA
from modules.agents.ingestion.pdf_processor import PDFProcessor, PDFContent
from modules.agents.ingestion.graph_loader import GraphLoader, LoadStats as GraphLoadStats
from modules.agents.ingestion.rag_loader import RAGLoader, RAGLoadStats
from modules.agents.ingestion.pipeline import IngestionPipeline, IngestionStats

__all__ = [
    "MarkdownQAParser", "ParsedQA",
    "PDFProcessor", "PDFContent",
    "GraphLoader", "GraphLoadStats",
    "RAGLoader", "RAGLoadStats",
    "IngestionPipeline", "IngestionStats",
]