"""
Auditor Agent
-------------
Produces a final audit summary from the outputs of all prior agents.
This is a pure-Python aggregation step — no LLM call required.
"""
import logging
from typing import Any

logger = logging.getLogger(__name__)


def run_audit(
    invoice: dict[str, Any],
    compliance_result: dict[str, Any],
    investigated_violations: list[dict[str, Any]],
    remediation_result: dict[str, Any],
) -> dict[str, Any]:
    """
    Compile the full audit report.

    Args:
        invoice:                  Original parsed invoice.
        compliance_result:        Output from the compliance agent.
        investigated_violations:  Enriched violations from the investigator agent.
        remediation_result:       Output from the remediator agent.

    Returns:
        A comprehensive audit dictionary suitable for the API response.
    """
    total_violations: int = compliance_result.get("violation_count", 0)
    fixed_count: int = remediation_result.get("fixed_count", 0)
    escalated_count: int = remediation_result.get("escalated_count", 0)

    # Fix rate is the fraction of violations that were automatically resolved
    fix_rate: float = (fixed_count / total_violations) if total_violations > 0 else 1.0

    # Determine overall audit status
    if total_violations == 0:
        audit_status = "CLEAN"
    elif escalated_count == 0:
        audit_status = "FIXED"
    elif fixed_count > 0:
        audit_status = "PARTIALLY_FIXED"
    else:
        audit_status = "ESCALATED"

    # Collect distinct severity levels from investigated violations
    severities = list({v.get("severity", "UNKNOWN") for v in investigated_violations})

    audit_report = {
        "audit_status": audit_status,
        "invoice_number": invoice.get("invoice_number", "N/A"),
        "vendor_name": invoice.get("vendor_name", "N/A"),
        "invoice_date": invoice.get("invoice_date", "N/A"),
        "total_amount": invoice.get("total_amount", 0),
        "currency": invoice.get("currency", "INR"),
        "metrics": {
            "total_processed": 1,          # One invoice per request
            "total_violations": total_violations,
            "fixed_count": fixed_count,
            "escalated_count": escalated_count,
            "fix_rate": round(fix_rate, 4),
        },
        "compliance_summary": {
            "is_compliant": compliance_result.get("is_compliant", True),
            "severity_levels_found": severities,
        },
        "remediation_summary": {
            "log": remediation_result.get("remediation_log", []),
            "updated_invoice": remediation_result.get("updated_invoice", invoice),
        },
    }

    logger.info(
        "Audit complete — status: %s | violations: %d | fixed: %d | escalated: %d",
        audit_status,
        total_violations,
        fixed_count,
        escalated_count,
    )

    return audit_report
