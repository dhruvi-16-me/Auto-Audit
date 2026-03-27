"""
Compliance Agent
----------------
Applies rule-based checks against the parsed invoice data and returns a list
of structured violations.

Current rules:
  1. GST rate mismatch — electronics invoices must carry exactly 18% GST.
  2. Over-limit invoice — total amount must not exceed INR 3,00,000.
"""
import logging
from typing import Any

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _check_gst_mismatch(invoice: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Return violations where an electronics line item carries the wrong GST rate.
    Checks both the top-level category and individual line-item descriptions.
    """
    violations: list[dict[str, Any]] = []
    category: str = str(invoice.get("category", "")).lower()
    line_items: list[dict[str, Any]] = invoice.get("line_items", [])

    for idx, item in enumerate(line_items):
        item_desc = str(item.get("description", "")).lower()
        # Flag if the invoice category is electronics OR the item description
        # mentions electronics-related keywords
        is_electronics = (
            category == "electronics"
            or any(kw in item_desc for kw in ("electronic", "laptop", "mobile", "phone", "device", "tablet", "tv"))
        )

        if not is_electronics:
            continue

        gst_rate = float(item.get("gst_rate", 0))
        if gst_rate != settings.gst_rate_electronics:
            violations.append(
                {
                    "rule": "GST_MISMATCH",
                    "line_item_index": idx,
                    "description": item.get("description", ""),
                    "expected_gst": settings.gst_rate_electronics,
                    "actual_gst": gst_rate,
                    "severity": "HIGH" if abs(gst_rate - settings.gst_rate_electronics) > 5 else "MEDIUM",
                    "message": (
                        f"Line item '{item.get('description')}' is electronics "
                        f"but has GST {gst_rate}% instead of required {settings.gst_rate_electronics}%."
                    ),
                }
            )

    return violations


def _check_over_limit(invoice: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Return a violation if the invoice total exceeds the configured limit.
    """
    violations: list[dict[str, Any]] = []
    total = float(invoice.get("total_amount", 0))

    if total > settings.invoice_amount_limit:
        excess = total - settings.invoice_amount_limit
        violations.append(
            {
                "rule": "OVER_LIMIT",
                "line_item_index": None,
                "description": "Invoice total exceeds allowed limit",
                "limit": settings.invoice_amount_limit,
                "actual_amount": total,
                "excess_amount": round(excess, 2),
                "severity": "CRITICAL" if excess > 100000 else "HIGH",
                "message": (
                    f"Invoice total ₹{total:,.2f} exceeds the maximum allowed "
                    f"₹{settings.invoice_amount_limit:,.2f} by ₹{excess:,.2f}."
                ),
            }
        )

    return violations


def run_compliance(invoice: dict[str, Any]) -> dict[str, Any]:
    """
    Run all compliance checks and return a structured result.

    Args:
        invoice: Parsed invoice dictionary from the intake agent.

    Returns:
        Dictionary with:
          - violations: list of violation dicts
          - is_compliant: bool (True if zero violations)
          - violation_count: int
    """
    violations: list[dict[str, Any]] = []

    violations.extend(_check_gst_mismatch(invoice))
    violations.extend(_check_over_limit(invoice))

    result = {
        "is_compliant": len(violations) == 0,
        "violation_count": len(violations),
        "violations": violations,
    }

    if violations:
        logger.warning(
            "Compliance check found %d violation(s) for invoice %s.",
            len(violations),
            invoice.get("invoice_number", "N/A"),
        )
    else:
        logger.info("Invoice %s passed all compliance checks.", invoice.get("invoice_number", "N/A"))

    return result
