"""
Duplicate Invoice Detector
---------------------------
Uses ChromaDB as a local vector store to detect near-duplicate invoices.

Embedding strategy:
  A lightweight character n-gram embedding is used to avoid external model
  downloads. It produces good recall for duplicate invoices (same vendor,
  similar amounts, identical line items) without requiring sentence-transformers
  or an external API.

  Swap `_NgramEmbedding` for a real model (e.g. OpenAI / Groq embeddings) in
  production to get semantic-level similarity.

Similarity threshold: configurable via DUPLICATE_SIMILARITY_THRESHOLD (default 0.95).
  ChromaDB uses cosine distance [0, 1]: distance < (1 - threshold) → duplicate.
"""
import hashlib
import logging
import math
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ─── Attempt to import chromadb ───────────────────────────────────────────────
try:
    import chromadb
    from chromadb import Documents, EmbeddingFunction, Embeddings

    _CHROMADB_AVAILABLE = True
except ImportError:
    _CHROMADB_AVAILABLE = False
    logger.warning(
        "chromadb is not installed — duplicate detection will use hash-only mode."
    )


# ─── Custom lightweight embedding function ───────────────────────────────────

if _CHROMADB_AVAILABLE:

    class _NgramEmbedding(EmbeddingFunction):  # type: ignore[misc]
        """
        Character 2+3-gram TF-style embedding (256 dims, cosine-normalised).
        No model download needed. Effective for near-duplicate text detection.
        """

        DIMS = 256

        def __call__(self, input: Documents) -> Embeddings:  # type: ignore[override]
            result: Embeddings = []
            for text in input:
                vec = [0.0] * self.DIMS
                t = text.lower()
                # 2-grams
                for i in range(len(t) - 1):
                    h = int(hashlib.md5(t[i:i + 2].encode()).hexdigest(), 16)
                    vec[h % self.DIMS] += 1.0
                # 3-grams
                for i in range(len(t) - 2):
                    h = int(hashlib.md5(t[i:i + 3].encode()).hexdigest(), 16)
                    vec[idx] += 0.5
                # L2-normalise
                norm = math.sqrt(sum(v * v for v in vec))
                if norm > 0:
                    vec = [v / norm for v in vec]
                result.append(vec)
            return result


# ─── Detector ─────────────────────────────────────────────────────────────────

_SIMILARITY_THRESHOLD = 0.95  # cosine similarity; distance < 0.05 = duplicate


class DuplicateDetector:
    """
    Detects near-duplicate invoice submissions using a ChromaDB vector store.

    Each invoice is stored by its invoice_number as the document ID.
    The document text used for embedding is a canonical representation of the
    invoice: vendor + date + total + line item descriptions.
    """

    def __init__(self) -> None:
        self._ready = False
        self._client: Any = None
        self._collection: Any = None
        self._seen_ids: set[str] = set()  # Fallback for hash-only mode

    def initialise(self) -> None:
        """Lazy initialise ChromaDB. Called once at application startup."""
        if not _CHROMADB_AVAILABLE:
            logger.warning("Running in hash-only duplicate detection mode.")
            self._ready = False
            return

        try:
            self._client = chromadb.EphemeralClient()
            self._collection = self._client.get_or_create_collection(
                name="invoices",
                metadata={"hnsw:space": "cosine"},
                embedding_function=_NgramEmbedding(),
            )
            self._ready = True
            logger.info("ChromaDB duplicate detector initialised (in-memory).")
        except Exception as exc:
            logger.error("ChromaDB init failed: %s — falling back to hash mode.", exc)
            self._ready = False

    # ── Public interface ──────────────────────────────────────────────────────

    def _canonical_text(self, invoice: dict[str, Any]) -> str:
        """Build a stable string representation for embedding."""
        items = " | ".join(
            f"{it.get('description', '')} {it.get('quantity', 0)} {it.get('unit_price', 0)}"
            for it in invoice.get("line_items", [])
        )
        return (
            f"vendor:{invoice.get('vendor_name', '')} "
            f"date:{invoice.get('invoice_date', '')} "
            f"total:{invoice.get('total_amount', 0)} "
            f"items:{items}"
        )

    def check_duplicate(
        self, invoice: dict[str, Any]
    ) -> tuple[bool, Optional[dict[str, Any]]]:
        """
        Check whether a similar invoice already exists in the store.

        Returns:
            (is_duplicate, duplicate_info)
            duplicate_info is None when no duplicate is found.
        """
        invoice_number = str(invoice.get("invoice_number", "UNKNOWN"))

        # 1. Exact invoice-number match (always checked)
        if invoice_number in self._seen_ids:
            return True, {
                "reason": "exact_invoice_number",
                "matched_id": invoice_number,
                "similarity": 1.0,
                "detected_at": datetime.utcnow().isoformat(),
            }

        if not self._ready:
            # Hash-only mode — only exact ID checks
            return False, None

        # 2. Semantic / near-duplicate check via ChromaDB
        doc_text = self._canonical_text(invoice)
        try:
            existing_count = self._collection.count()
            if existing_count == 0:
                return False, None

            results = self._collection.query(
                query_texts=[doc_text],
                n_results=min(3, existing_count),
            )

            distances: list[float] = results["distances"][0]  # type: ignore[index]
            ids: list[str] = results["ids"][0]  # type: ignore[index]

            if not distances:
                return False, None

            best_distance = min(distances)
            best_id = ids[distances.index(best_distance)]
            similarity = round(1.0 - best_distance, 4)

            if similarity >= _SIMILARITY_THRESHOLD:
                return True, {
                    "reason": "content_similarity",
                    "matched_id": best_id,
                    "similarity": similarity,
                    "detected_at": datetime.utcnow().isoformat(),
                }
        except Exception as exc:
            logger.warning("ChromaDB query failed: %s", exc)

        return False, None

    def store_invoice(self, invoice: dict[str, Any]) -> None:
        """
        Persist an invoice's embedding so future submissions can be checked.
        Call this AFTER the audit completes (not before, to avoid self-match).
        """
        invoice_number = str(invoice.get("invoice_number", "UNKNOWN"))
        self._seen_ids.add(invoice_number)

        if not self._ready:
            return

        doc_text = self._canonical_text(invoice)
        try:
            # Upsert: re-processing the same invoice updates its record
            self._collection.upsert(
                documents=[doc_text],
                ids=[invoice_number],
                metadatas=[
                    {
                        "vendor_name": str(invoice.get("vendor_name", "")),
                        "invoice_date": str(invoice.get("invoice_date", "")),
                        "total_amount": float(invoice.get("total_amount", 0)),
                        "stored_at": datetime.utcnow().isoformat(),
                    }
                ],
            )
        except Exception as exc:
            logger.warning("ChromaDB upsert failed: %s", exc)

    @property
    def is_ready(self) -> bool:
        return self._ready

    @property
    def stored_count(self) -> int:
        if self._ready and self._collection is not None:
            return self._collection.count()
        return len(self._seen_ids)


# ─── Singleton ────────────────────────────────────────────────────────────────
duplicate_detector = DuplicateDetector()
