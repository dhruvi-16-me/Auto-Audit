"""
Intake Agent
------------
Accepts raw PDF bytes, extracts text via the PDF parser, then asks the LLM
to return a structured JSON representation of the invoice.
"""
import json
import logging
import re
from typing import Any

from services.pdf_parser import extract_text_from_pdf
from services.llm import groq_completion

logger = logging.getLogger(__name__)

# Prompt template — keep it tight so the LLM stays on task
_INTAKE_PROMPT = """
You are an expert invoice parser. Extract the following fields from the invoice text below and return ONLY valid JSON — no explanation, no markdown fences.

Required fields:
{{
  "invoice_number": "<string>",
  "vendor_name": "<string>",
  "invoice_date": "<YYYY-MM-DD or original string>",
  "total_amount": <float>,
  "currency": "<string, default INR>",
  "line_items": [
    {{
      "description": "<string>",
      "quantity": <float>,
      "unit_price": <float>,
      "gst_rate": <float>,
      "amount": <float>
    }}
  ],
  "gst_total": <float>,
  "category": "<string, e.g. electronics / services / raw_materials>"
}}

Invoice text:
---
{invoice_text}
---
"""


def _extract_json_from_response(raw: str) -> dict[str, Any]:
    """
    Robustly pull a JSON object out of the LLM response.
    The model sometimes wraps output in markdown code fences.
    """
    # Strip markdown fences if present
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()

    # Find the first {...} block
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError("No JSON object found in LLM response.")

    return json.loads(cleaned[start:end])


async def run_intake(pdf_bytes: bytes) -> dict[str, Any]:
    """
    Full intake pipeline:
      1. Extract text from PDF.
      2. Send to LLM for structured parsing.
      3. Return the parsed invoice dict.

    Args:
        pdf_bytes: Raw bytes of the uploaded PDF.

    Returns:
        Parsed invoice data as a dictionary.

    Raises:
        ValueError: If text cannot be extracted or JSON parsing fails.
        RuntimeError: If the LLM call fails.
    """
    # Step 1 — PDF text extraction
    text = extract_text_from_pdf(pdf_bytes)
    if not text:
        raise ValueError("Could not extract text from the uploaded PDF.")

    logger.info("Extracted %d characters from PDF.", len(text))

    # Step 2 — LLM structured extraction
    prompt = _INTAKE_PROMPT.format(invoice_text=text[:6000])  # cap to avoid token overflow
    raw_response = await groq_completion(prompt)

    # Step 3 — Parse JSON safely
    try:
        invoice_data = _extract_json_from_response(raw_response)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.error("Failed to parse LLM response as JSON: %s\nRaw: %s", exc, raw_response[:500])
        raise ValueError(f"LLM returned invalid JSON during intake: {exc}") from exc

    logger.info("Intake complete. Invoice number: %s", invoice_data.get("invoice_number", "N/A"))
    return invoice_data
