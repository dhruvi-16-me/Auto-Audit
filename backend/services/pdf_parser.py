"""
PDF parsing service using PyMuPDF (fitz).
Extracts raw text from each page of a PDF document.
"""
import fitz  # PyMuPDF
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_bytes: bytes) -> Optional[str]:
    """
    Extract all text from a PDF given its raw bytes.

    Args:
        pdf_bytes: Raw bytes of the PDF file.

    Returns:
        Concatenated text from all pages, or None if extraction fails.
    """
    if not pdf_bytes:
        logger.error("Received empty PDF bytes.")
        return None

    try:
        # Open PDF from in-memory bytes; stream= avoids writing a temp file
        doc: fitz.Document = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        logger.error("Failed to open PDF: %s", exc)
        return None

    pages_text: list[str] = []

    for page_index in range(len(doc)):
        try:
            page: fitz.Page = doc.load_page(page_index)
            text: str = page.get_text("text")  # plain-text extraction
            pages_text.append(text.strip())
        except Exception as exc:
            # Log but continue — a single bad page shouldn't abort the whole doc
            logger.warning("Could not extract text from page %d: %s", page_index, exc)

    doc.close()

    full_text = "\n\n".join(filter(None, pages_text))

    if not full_text.strip():
        logger.warning("PDF yielded no extractable text (may be image-only).")
        return None

    return full_text
