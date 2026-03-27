"""
Investigator Agent
------------------
Uses the LLM to deep-dive into each compliance violation and produce a
structured investigation report per violation.
"""
import json
import logging
import re
from typing import Any

from services.llm import groq_completion

logger = logging.getLogger(__name__)

_INVESTIGATION_PROMPT = """
You are a financial compliance investigator. Analyse the violation below and return ONLY valid JSON.

Invoice context:
{invoice_summary}

Violation:
{violation}

Return this exact JSON structure (no markdown, no explanation):
{{
  "cause": "<concise root-cause explanation>",
  "confidence": <float between 0.0 and 1.0>,
  "risk_score": <integer between 1 and 10>,
  "action": "<recommended action: e.g. auto_fix / escalate / review / reject>"
}}
"""


def _extract_json(raw: str) -> dict[str, Any]:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError("No JSON object found in investigator LLM response.")
    return json.loads(cleaned[start:end])


def _build_invoice_summary(invoice: dict[str, Any]) -> str:
    """Compact single-line summary to keep prompt tokens low."""
    return (
        f"Invoice #{invoice.get('invoice_number', 'N/A')} | "
        f"Vendor: {invoice.get('vendor_name', 'N/A')} | "
        f"Total: {invoice.get('currency', 'INR')} {invoice.get('total_amount', 0):,.2f} | "
        f"Category: {invoice.get('category', 'N/A')} | "
        f"Date: {invoice.get('invoice_date', 'N/A')}"
    )


async def run_investigation(
    invoice: dict[str, Any],
    violations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Investigate each violation independently via the LLM.

    Args:
        invoice:    Parsed invoice dict from the intake agent.
        violations: List of violation dicts from the compliance agent.

    Returns:
        List of enriched violation dicts, each augmented with:
          - cause
          - confidence
          - risk_score
          - action
    """
    if not violations:
        return []

    invoice_summary = _build_invoice_summary(invoice)
    investigated: list[dict[str, Any]] = []

    for violation in violations:
        try:
            prompt = _INVESTIGATION_PROMPT.format(
                invoice_summary=invoice_summary,
                violation=json.dumps(violation, indent=2),
            )
            raw = await groq_completion(prompt)
            analysis = _extract_json(raw)

            # Merge investigation findings into the violation record
            enriched = {
                **violation,
                "cause": analysis.get("cause", "Unknown"),
                "confidence": float(analysis.get("confidence", 0.5)),
                "risk_score": int(analysis.get("risk_score", 5)),
                "action": analysis.get("action", "review"),
            }
        except (json.JSONDecodeError, ValueError, RuntimeError) as exc:
            logger.error("Investigation failed for violation %s: %s", violation.get("rule"), exc)
            # Provide safe defaults so the pipeline can continue
            enriched = {
                **violation,
                "cause": "Investigation failed — manual review required.",
                "confidence": 0.0,
                "risk_score": 5,
                "action": "escalate",
            }

        investigated.append(enriched)
        logger.info(
            "Investigated violation '%s' → risk_score=%d, action=%s",
            enriched.get("rule"),
            enriched.get("risk_score"),
            enriched.get("action"),
        )

    return investigated
