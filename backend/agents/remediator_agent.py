"""
Remediator Agent — with rollback and post-fix validation.
----------------------------------------------------------
Strategy:
  1. Snapshot the invoice before any mutations.
  2. Apply fix(es) for low-risk violations (risk_score < threshold).
  3. Validate the patched invoice with _validate_post_fix().
  4. If validation fails → rollback to snapshot, escalate instead.
  5. Escalate high-risk violations without touching the invoice.
"""
import logging
from typing import Any

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ─── Validation ──────────────────────────────────────────────────────────────

class RemediationValidationError(Exception):
    """Raised when a post-fix validation check fails."""


def _validate_post_fix(
    original: dict[str, Any],
    patched: dict[str, Any],
    rule: str,
) -> None:
    """
    Structural sanity checks applied after each auto-fix.
    Raises RemediationValidationError if the patched invoice looks wrong.
    """
    orig_items = original.get("line_items", [])
    patch_items = patched.get("line_items", [])

    # 1. Must not lose line items
    if len(patch_items) != len(orig_items):
        raise RemediationValidationError(
            f"Line-item count changed after fix for rule '{rule}': "
            f"{len(orig_items)} → {len(patch_items)}"
        )

    if rule == "GST_MISMATCH":
        # 2. Every fixed item's GST must be within [0, 28]
        for idx, item in enumerate(patch_items):
            gst = float(item.get("gst_rate", -1))
            if not (0 <= gst <= 28):
                raise RemediationValidationError(
                    f"Item {idx}: GST rate {gst}% is out of valid range [0, 28] "
                    f"after fix."
                )

        # 3. Amount must be non-negative
        for idx, item in enumerate(patch_items):
            amount = float(item.get("amount", -1))
            if amount < 0:
                raise RemediationValidationError(
                    f"Item {idx}: amount {amount} went negative after fix."
                )

    logger.debug("Post-fix validation passed for rule '%s'.", rule)


# ─── Fix handlers ─────────────────────────────────────────────────────────────

def _fix_gst_mismatch(
    invoice: dict[str, Any],
    violation: dict[str, Any],
) -> dict[str, Any]:
    """
    Correct the GST rate on the offending line item and recalculate its amount.
    Returns a DEEP COPY of the invoice (original is not mutated).
    """
    invoice = dict(invoice)
    invoice["line_items"] = [dict(item) for item in invoice.get("line_items", [])]

    idx: int | None = violation.get("line_item_index")
    if idx is None or idx >= len(invoice["line_items"]):
        logger.warning("GST fix skipped — invalid line_item_index: %s", idx)
        return invoice

    item = invoice["line_items"][idx]
    original_gst = float(item.get("gst_rate", 0))
    correct_gst = settings.gst_rate_electronics

    # Recalculate item amount from unit economics
    base_amount = float(item.get("unit_price", 0)) * float(item.get("quantity", 1))
    corrected_amount = round(base_amount * (1 + correct_gst / 100), 2)

    item["gst_rate"] = correct_gst
    item["amount"] = corrected_amount

    logger.info(
        "GST fix applied on '%s': %.1f%% → %.1f%% (amount %.2f → %.2f)",
        item.get("description"),
        original_gst,
        correct_gst,
        base_amount,
        corrected_amount,
    )
    return invoice


# ─── Main entry point ─────────────────────────────────────────────────────────

def run_remediation(
    invoice: dict[str, Any],
    investigated_violations: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Process each investigated violation:
      - Auto-fix low-risk violations where a fix handler exists.
      - Validate after each fix; rollback to pre-fix snapshot on failure.
      - Escalate everything else for manual review.

    Args:
        invoice:                  Parsed invoice dict from the intake agent.
        investigated_violations:  Enriched violations from the investigator.

    Returns:
        {
          updated_invoice:  Invoice after all applicable auto-fixes.
          remediation_log:  Action record per violation.
          fixed_count:      Number of violations auto-fixed successfully.
          escalated_count:  Number of violations escalated (incl. rollbacks).
        }
    """
    remediation_log: list[dict[str, Any]] = []
    fixed_count = 0
    escalated_count = 0
    current_invoice = invoice  # Working copy; replaced after each successful fix

    for violation in investigated_violations:
        rule: str = violation.get("rule", "UNKNOWN")
        risk_score: int = int(violation.get("risk_score", 5))
        should_auto_fix = risk_score < settings.auto_fix_risk_threshold

        log_entry: dict[str, Any] = {
            "rule": rule,
            "risk_score": risk_score,
            "line_item_index": violation.get("line_item_index"),
        }

        if should_auto_fix and rule == "GST_MISMATCH":
            # ── Snapshot before mutation ──────────────────────────────────
            snapshot = current_invoice

            try:
                patched = _fix_gst_mismatch(current_invoice, violation)
                _validate_post_fix(snapshot, patched, rule)

                # Validation passed → accept the patch
                current_invoice = patched
                log_entry["status"] = "AUTO_FIXED"
                log_entry["detail"] = (
                    f"GST corrected to {settings.gst_rate_electronics}% on "
                    f"line item {violation.get('line_item_index')} (risk={risk_score})."
                )
                fixed_count += 1

            except RemediationValidationError as val_err:
                # Validation failed → rollback to snapshot
                current_invoice = snapshot
                log_entry["status"] = "ROLLED_BACK"
                log_entry["detail"] = (
                    f"Auto-fix validation failed for rule '{rule}' "
                    f"({val_err}). Invoice rolled back to original state."
                )
                log_entry["rollback_reason"] = str(val_err)
                escalated_count += 1
                logger.warning("Fix rolled back for %s: %s", rule, val_err)

            except Exception as exc:
                current_invoice = snapshot
                log_entry["status"] = "ROLLED_BACK"
                log_entry["detail"] = (
                    f"Unexpected error during fix of '{rule}': {exc}. "
                    f"Invoice rolled back."
                )
                escalated_count += 1
                logger.error("Unexpected remediator error for %s: %s", rule, exc)

        else:
            # ── Escalate ──────────────────────────────────────────────────
            reason = (
                f"risk_score {risk_score} ≥ threshold {settings.auto_fix_risk_threshold}"
                if not should_auto_fix
                else f"no auto-fix handler for rule '{rule}'"
            )
            log_entry["status"] = "ESCALATED"
            log_entry["detail"] = (
                f"Escalated for manual review ({reason}). "
                f"Cause: {violation.get('cause', 'N/A')}"
            )
            escalated_count += 1

        remediation_log.append(log_entry)

    return {
        "updated_invoice": current_invoice,
        "remediation_log": remediation_log,
        "fixed_count": fixed_count,
        "escalated_count": escalated_count,
    }
