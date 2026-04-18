"""
document_store.py - Document Upload and RAG System for AI Note Taker

Features:
- Document upload (PDF, DOCX, TXT, MD)
- Text extraction and chunking
- Vector embeddings using Ollama (local) or sentence-transformers
- Similarity search for context retrieval
"""

import os
import json
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import numpy as np

logger = logging.getLogger("document_store")

# Storage paths
DATA_DIR = Path(os.path.dirname(__file__)) / "data"
DOCS_DIR = DATA_DIR / "documents"
VECTOR_DIR = DATA_DIR / "vectors"

# Ensure directories exist
DOCS_DIR.mkdir(parents=True, exist_ok=True)
VECTOR_DIR.mkdir(parents=True, exist_ok=True)

# Embedding configuration
EMBEDDING_MODEL = "nomic-embed-text"  # Default Ollama embedding model
CHUNK_SIZE = 512  # Characters per chunk
CHUNK_OVERLAP = 128  # Overlap between chunks
TOP_K_RESULTS = 5  # Number of relevant chunks to retrieve


class DocumentChunk:
    """Represents a chunk of a document with metadata."""
    def __init__(self, text: str, doc_id: str, doc_name: str, chunk_idx: int, embedding: Optional[List[float]] = None):
        self.text = text
        self.doc_id = doc_id
        self.doc_name = doc_name
        self.chunk_idx = chunk_idx
        self.embedding = embedding or []

    def to_dict(self) -> Dict:
        return {
            "text": self.text,
            "doc_id": self.doc_id,
            "doc_name": self.doc_name,
            "chunk_idx": self.chunk_idx,
            "embedding": self.embedding
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "DocumentChunk":
        return cls(
            text=data["text"],
            doc_id=data["doc_id"],
            doc_name=data["doc_name"],
            chunk_idx=data["chunk_idx"],
            embedding=data.get("embedding", [])
        )


class DocumentStore:
    """Manages document storage, embedding, and retrieval."""

    def __init__(self):
        self.chunks: List[DocumentChunk] = []
        self.embeddings_available = False
        self._load_existing_vectors()

    def _load_existing_vectors(self):
        """Load existing vector index from disk."""
        vector_file = VECTOR_DIR / "index.json"
        if vector_file.exists():
            try:
                with open(vector_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.chunks = [DocumentChunk.from_dict(c) for c in data.get("chunks", [])]
                    self.embeddings_available = len(self.chunks) > 0 and len(self.chunks[0].embedding) > 0
                    logger.info(f"Loaded {len(self.chunks)} document chunks from vector store")
            except Exception as e:
                logger.warning("Failed to load vector index: %s", str(e))

    def _save_vectors(self):
        """Save vector index to disk."""
        vector_file = VECTOR_DIR / "index.json"
        try:
            with open(vector_file, "w", encoding="utf-8") as f:
                json.dump({
                    "chunks": [c.to_dict() for c in self.chunks]
                }, f, indent=2)
            logger.info(f"Saved {len(self.chunks)} chunks to vector store")
        except Exception as e:
            logger.error("Failed to save vector index: %s", str(e))

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute hash of file for deduplication (non-cryptographic)."""
        hash_md5 = hashlib.md5()  # nosec B324 — used for deduplication, not security
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def _extract_text(self, file_path: Path) -> str:
        """Extract text from various file formats."""
        ext = file_path.suffix.lower()

        if ext == ".txt" or ext == ".md":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

        elif ext == ".pdf":
            try:
                import PyPDF2
                text = ""
                with open(file_path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                return text
            except Exception as e:
                logger.error("PDF extraction failed: %s", str(e))
                return ""

        elif ext == ".docx":
            try:
                import docx
                doc = docx.Document(file_path)
                return "\n".join([para.text for para in doc.paragraphs])
            except Exception as e:
                logger.error("DOCX extraction failed: %s", str(e))
                return ""

        elif ext == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return json.dumps(data, indent=2)

        else:
            logger.warning(f"Unsupported file format: {ext}")
            return ""

    def _chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks."""
        chunks = []
        start = 0

        while start < len(text):
            end = min(start + CHUNK_SIZE, len(text))

            # Try to break at a sentence or word boundary
            if end < len(text):
                # Look for sentence ending
                for i in range(end - 1, start + CHUNK_SIZE // 2, -1):
                    if text[i] in ".!?\n":
                        end = i + 1
                        break
                else:
                    # Look for word boundary
                    for i in range(end - 1, start + CHUNK_SIZE // 2, -1):
                        if text[i] == " ":
                            end = i
                            break

            chunks.append(text[start:end].strip())
            start = end - CHUNK_OVERLAP

        return [c for c in chunks if len(c) > 50]  # Filter very short chunks

    def _get_embedding_ollama(self, text: str) -> Optional[List[float]]:
        """Get embedding using Ollama's nomic-embed-text or similar model."""
        try:
            from lib.http_client import sync_client
            from config import OLLAMA_URL

            response = sync_client.post(
                f"{OLLAMA_URL}/api/embeddings",
                json={"model": EMBEDDING_MODEL, "prompt": text},
                timeout=15,
                skip_ssrf_check=True,  # internal Ollama service
            )

            if response.status_code == 200:
                return response.json().get("embedding", [])
            else:
                logger.warning(f"Ollama embedding failed: {response.status_code}")
                return None
        except Exception as e:
            logger.warning("Ollama embedding error: %s", str(e))
            return None

    def _get_embedding_local(self, text: str) -> Optional[List[float]]:
        """Fallback: Simple keyword-based embedding (not semantic, but works without Ollama)."""
        # This is a fallback that creates a sparse vector based on word frequencies
        words = text.lower().split()
        # Create a simple hash-based embedding (768 dimensions)
        embedding = [0.0] * 768
        for i, word in enumerate(words[:100]):  # Limit to first 100 words
            hash_val = hash(word) % 768
            embedding[hash_val] += 1.0
        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = [e / norm for e in embedding]
        return embedding

    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text, with fallback chain based on EMBEDDING_PROVIDER config."""
        import os
        provider = os.getenv("EMBEDDING_PROVIDER", "local")

        # Primary: sentence-transformers (local, no Ollama dependency)
        if provider in ("local", "hybrid"):
            try:
                from modules.ai.embedding_service import get_embedding_service, EMBEDDING_AVAILABLE
                if EMBEDDING_AVAILABLE:
                    service = get_embedding_service()
                    if service:
                        return service.embed(text)
            except Exception:
                pass  # nosec B110

            if provider == "local":
                # For local-only mode, skip Ollama and go straight to fallback
                return self._get_embedding_local(text)

        # Secondary: Ollama embedding API
        if provider in ("ollama", "hybrid"):
            embedding = self._get_embedding_ollama(text)
            if embedding:
                return embedding

        # Tertiary: hash-based fallback
        return self._get_embedding_local(text)

    def add_document(self, file_path: str) -> Dict:
        """Add a document to the store."""
        path = Path(file_path)
        if not path.exists():
            return {"error": "File not found"}

        # Compute file hash for deduplication
        file_hash = self._compute_file_hash(path)
        doc_id = file_hash[:16]

        # Check if already exists
        existing = [c for c in self.chunks if c.doc_id == doc_id]
        if existing:
            return {"status": "already_exists", "doc_id": doc_id, "chunks": len(existing)}

        # Extract text
        text = self._extract_text(path)
        if not text:
            return {"error": "Could not extract text from file"}

        # Chunk text
        chunks = self._chunk_text(text)
        if not chunks:
            return {"error": "No valid chunks created from document"}

        # Create document chunks with embeddings
        logger.info(f"Processing {path.name}: {len(chunks)} chunks")
        doc_chunks = []
        for idx, chunk_text in enumerate(chunks):
            embedding = self._get_embedding(chunk_text)
            chunk = DocumentChunk(
                text=chunk_text,
                doc_id=doc_id,
                doc_name=path.name,
                chunk_idx=idx,
                embedding=embedding
            )
            doc_chunks.append(chunk)

        # Add to store
        self.chunks.extend(doc_chunks)
        self.embeddings_available = True
        self._save_vectors()

        return {
            "status": "success",
            "doc_id": doc_id,
            "doc_name": path.name,
            "chunks": len(chunks),
            "total_chars": len(text)
        }

    def delete_document(self, doc_id: str) -> bool:
        """Remove a document from the store."""
        original_len = len(self.chunks)
        self.chunks = [c for c in self.chunks if c.doc_id != doc_id]
        deleted = len(self.chunks) < original_len
        if deleted:
            self._save_vectors()
        return deleted

    def list_documents(self) -> List[Dict]:
        """List all unique documents in the store."""
        docs = {}
        for chunk in self.chunks:
            if chunk.doc_id not in docs:
                docs[chunk.doc_id] = {
                    "id": chunk.doc_id,
                    "name": chunk.doc_name,
                    "chunks": 0
                }
            docs[chunk.doc_id]["chunks"] += 1
        return list(docs.values())

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not a or not b or len(a) != len(b):
            return 0.0
        a_norm = np.linalg.norm(a)
        b_norm = np.linalg.norm(b)
        if a_norm == 0 or b_norm == 0:
            return 0.0
        return float(np.dot(a, b) / (a_norm * b_norm))

    def retrieve_context(self, query: str, top_k: int = TOP_K_RESULTS) -> List[Dict]:
        """Retrieve relevant document chunks for a query."""
        if not self.chunks:
            return []

        # Get query embedding
        query_embedding = self._get_embedding(query)

        # Compute similarities
        similarities = []
        for chunk in self.chunks:
            if chunk.embedding:
                sim = self._cosine_similarity(query_embedding, chunk.embedding)
                similarities.append((sim, chunk))

        # Sort by similarity and return top_k
        similarities.sort(key=lambda x: x[0], reverse=True)
        results = []
        for sim, chunk in similarities[:top_k]:
            results.append({
                "text": chunk.text,
                "doc_name": chunk.doc_name,
                "doc_id": chunk.doc_id,
                "similarity": round(sim, 4)
            })

        return results

    def format_context_for_prompt(self, query: str, top_k: int = TOP_K_RESULTS) -> str:
        """Format retrieved context for inclusion in AI prompts."""
        results = self.retrieve_context(query, top_k)
        if not results:
            return ""

        context_parts = ["\n\n=== RELEVANT DOCUMENT CONTEXT ==="]
        for i, result in enumerate(results, 1):
            context_parts.append(f"\n[{i}] From {result['doc_name']} (relevance: {result['similarity']}):")
            context_parts.append(result['text'][:500])  # Limit to 500 chars per chunk
        context_parts.append("\n=== END CONTEXT ===\n")

        return "\n".join(context_parts)


# Global document store instance
doc_store = DocumentStore()


def get_document_store() -> DocumentStore:
    """Get the global document store instance."""
    return doc_store
