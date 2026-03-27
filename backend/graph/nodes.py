"""
LangGraph Node Functions
-------------------------
Each async function corresponds to one node in the audit pipeline graph.
Nodes:
  1. intake_node          — PDF text extraction + LLM parsing
  2. duplicate_check_node — ChromaDB similarity check (runs before compliance)
  3. compliance_node      — Rule-based GST / over-limit checks
  4. investigator_node    — LLM analysis of each violation
  5. remediator_node      — Auto-fix low-risk violations, rollback on failure
  6. auditor_node         — Compile metrics + close audit trail

Every node:
  · Emits real-time log events via ws_manager
  · Records events in the audit trail
  · Returns a partial AuditState dict (LangGraph merges it into the full state)
  · Catches exceptions, logs them, and adds them to state["errors"] so the
    pipeline can continue rather than crash the whole request
"""
import logging
import time
from typing import Any

from agents.auditor_agent import run_audit
from agents.compliance_agent import run_compliance
from agents.intake_agent import run_intake
from agents.investigator_agent import run_investigation
from agents.remediator_agent import run_remediation
from graph.state import AuditState, make_log
from services.audit_trail import audit_trail
from services.duplicate_detector import duplicate_detector
from services.websocket_manager import ws_manager

logger = logging.getLogger(__name__)


# ─── Helper ───────────────────────────────────────────────────────────────────

async def _log(agent: str, level: str, msg: str) -> dict[str, Any]:
    """Broadcast a WS log AND return a LogEntry dict for state accumulation."""
    await ws_manager.broadcast_log(agent, level, msg)
    return make_log(agent, level, msg)


# ─── Node 1: Intake ───────────────────────────────────────────────────────────

async def intake_node(state: AuditState) -> dict[str, Any]:
    """
    Extracts text from the PDF via PyMuPDF, then calls the Groq LLM to return
    a structured invoice dictionary. Retried automatically by the LLM service.
    """
    t0 = time.perf_counter()
    logs = [await _log("Intake", "info", "Pipeline started — dispatching intake agent…")]

    try:
        logs.append(await _log("Intake", "info", "Opening PDF stream and extracting raw text…"))
        invoice: dict[str, Any] = await run_intake(state["pdf_bytes"])

        inv_num = invoice.get("invoice_number", "N/A")
        vendor = invoice.get("vendor_name", "N/A")
        total = invoice.get("total_amount", 0)
        logs.append(await _log(
            "Intake", "success",
            f"Invoice parsed — #{inv_num} | {vendor} | ₹{total:,.2f}"
        ))

        audit_trail.record_intake(str(inv_num), invoice, state["filename"])

        elapsed = round((time.perf_counter() - t0) * 1000, 1)
        await ws_manager.broadcast_event(
            "stage_complete",
            {"stage": "intake", "duration_ms": elapsed},
        )

        return {
            "invoice": invoice,
            "logs": logs,
            "stage_timings": {"intake_ms": elapsed},
        }

    except (ValueError, RuntimeError) as exc:
        err_msg = f"Intake failed: {exc}"
        logs.append(await _log("Intake", "error", err_msg))
        logger.error(err_msg)
        return {
            "invoice": {},
            "logs": logs,
            "errors": [err_msg],
            "stage_timings": {"intake_ms": round((time.perf_counter() - t0) * 1000, 1)},
        }


# ─── Node 2: Duplicate Check ──────────────────────────────────────────────────

async def duplicate_check_node(state: AuditState) -> dict[str, Any]:
    """
    Checks the extracted invoice against the ChromaDB store.
    Flags duplicates so the caller can short-circuit the pipeline.
    Does NOT abort — the upstream graph route decides what to do.
    """
    if not state.get("invoice"):
        return {"logs": [make_log("DuplicateChecker", "info", "Skipped — no invoice data.")]}

    t0 = time.perf_counter()
    logs = [await _log("DuplicateChecker", "info", "Checking for duplicate submissions…")]

    is_dup, dup_info = duplicate_detector.check_duplicate(state["invoice"])

    elapsed = round((time.perf_counter() - t0) * 1000, 1)

    if is_dup:
        logs.append(await _log(
            "DuplicateChecker", "warning",
            f"Duplicate detected! Matched invoice {dup_info.get('matched_id')} "
            f"(similarity {dup_info.get('similarity', 0):.2%})"
        ))
        await ws_manager.broadcast_event(
            "duplicate_detected",
            {"matched_id": dup_info.get("matched_id"), "similarity": dup_info.get("similarity")},
        )
        record = audit_trail.get_record(str(state["invoice"].get("invoice_number", "UNKNOWN")))
        if record:
            record.add_event(
                stage="DuplicateChecker",
                action="duplicate_flagged",
                level="warning",
                data=dup_info or {},
            )
    else:
        logs.append(await _log("DuplicateChecker", "success", "No duplicate found — proceeding."))

    return {
        "duplicate_detected": is_dup,
        "duplicate_info": dup_info,
        "logs": logs,
        "stage_timings": {"duplicate_check_ms": elapsed},
    }


# ─── Node 3: Compliance ───────────────────────────────────────────────────────

async def compliance_node(state: AuditState) -> dict[str, Any]:
    """
    Runs rule-based compliance checks:
      - GST rate validation for electronics (must be 18%)
      - Invoice total over-limit check (> ₹3,00,000)
    """
    if not state.get("invoice"):
        return {"logs": [make_log("Compliance", "info", "Skipped — no invoice data.")]}

    t0 = time.perf_counter()
    logs = [await _log("Compliance", "info", "Running compliance scanner…")]

    try:
        logs.append(await _log("Compliance", "info", "Checking GST rates against category rules…"))
        logs.append(await _log("Compliance", "info", "Validating invoice total against ₹3,00,000 limit…"))

        result = run_compliance(state["invoice"])
        violations = result.get("violations", [])
        count = len(violations)

        if count == 0:
            logs.append(await _log("Compliance", "success", "Invoice is fully compliant — no violations found."))
        else:
            for v in violations:
                logs.append(await _log(
                    "Compliance", "warning",
                    f"[{v['rule']}] {v['severity']} — {v['message']}"
                ))
            audit_trail.record_violations(
                str(state["invoice"].get("invoice_number", "UNKNOWN")),
                violations,
            )

        elapsed = round((time.perf_counter() - t0) * 1000, 1)
        await ws_manager.broadcast_event(
            "stage_complete",
            {"stage": "compliance", "violations": count, "duration_ms": elapsed},
        )

        return {
            "violations": violations,
            "logs": logs,
            "stage_timings": {"compliance_ms": elapsed},
        }

    except Exception as exc:
        err_msg = f"Compliance check failed: {exc}"
        logs.append(await _log("Compliance", "error", err_msg))
        logger.error(err_msg)
        return {
            "violations": [],
            "logs": logs,
            "errors": [err_msg],
            "stage_timings": {"compliance_ms": round((time.perf_counter() - t0) * 1000, 1)},
        }


# ─── Node 4: Investigator ─────────────────────────────────────────────────────

async def investigator_node(state: AuditState) -> dict[str, Any]:
    """
    Sends each violation to the Groq LLM for root-cause analysis,
    risk scoring, and recommended action.
    """
    violations = state.get("violations", [])
    if not violations:
        log = await _log("Investigator", "info", "No violations to investigate — skipping.")
        return {"investigations": [], "logs": [log]}

    t0 = time.perf_counter()
    logs = [await _log(
        "Investigator", "info",
        f"Investigating {len(violations)} violation(s) with LLM…"
    )]

    try:
        logs.append(await _log("Investigator", "info", "Dispatching LLM for root-cause analysis…"))
        logs.append(await _log("Investigator", "info", "Calculating risk scores and confidence levels…"))

        investigated = await run_investigation(state["invoice"], violations)

        for inv in investigated:
            logs.append(await _log(
                "Investigator", "success" if inv.get("risk_score", 5) < 5 else "warning",
                f"[{inv['rule']}] risk={inv.get('risk_score')}/10 | "
                f"confidence={inv.get('confidence', 0):.0%} | action={inv.get('action')}"
            ))

        elapsed = round((time.perf_counter() - t0) * 1000, 1)
        await ws_manager.broadcast_event(
            "stage_complete",
            {"stage": "investigator", "investigated": len(investigated), "duration_ms": elapsed},
        )

        return {
            "investigations": investigated,
            "logs": logs,
            "stage_timings": {"investigation_ms": elapsed},
        }

    except Exception as exc:
        err_msg = f"Investigation failed: {exc}"
        logs.append(await _log("Investigator", "error", err_msg))
        logger.error(err_msg)
        # Fall back: pass violations through with safe defaults
        fallback = [
            {
                **v,
                "cause": "Investigation unavailable — manual review required.",
                "confidence": 0.0,
                "risk_score": 5,
                "action": "escalate",
            }
            for v in violations
        ]
        return {
            "investigations": fallback,
            "logs": logs,
            "errors": [err_msg],
            "stage_timings": {"investigation_ms": round((time.perf_counter() - t0) * 1000, 1)},
        }


# ─── Node 5: Remediator ───────────────────────────────────────────────────────

async def remediator_node(state: AuditState) -> dict[str, Any]:
    """
    Applies auto-fixes for low-risk violations.
    Includes a full rollback mechanism if post-fix validation fails.
    """
    investigations = state.get("investigations", [])
    if not investigations:
        log = await _log("Remediator", "info", "No violations to remediate — skipping.")
        return {
            "remediation_result": {
                "updated_invoice": state.get("invoice", {}),
                "remediation_log": [],
                "fixed_count": 0,
                "escalated_count": 0,
            },
            "logs": [log],
        }

    t0 = time.perf_counter()
    logs = [await _log("Remediator", "info", "Applying remediation strategy…")]

    try:
        result = run_remediation(state["invoice"], investigations)

        for entry in result.get("remediation_log", []):
            lvl = "success" if entry["status"] == "AUTO_FIXED" else "warning"
            logs.append(await _log("Remediator", lvl, f"[{entry['rule']}] {entry['status']}: {entry['detail']}"))
            audit_trail.record_fix(
                str(state["invoice"].get("invoice_number", "UNKNOWN")),
                entry["rule"],
                entry["status"],
                entry["detail"],
            )

        fixed = result.get("fixed_count", 0)
        escalated = result.get("escalated_count", 0)
        logs.append(await _log(
            "Remediator", "success",
            f"Remediation complete — {fixed} fixed, {escalated} escalated."
        ))

        elapsed = round((time.perf_counter() - t0) * 1000, 1)
        await ws_manager.broadcast_event(
            "stage_complete",
            {"stage": "remediator", "fixed": fixed, "escalated": escalated, "duration_ms": elapsed},
        )

        return {
            "remediation_result": result,
            "logs": logs,
            "stage_timings": {"remediation_ms": elapsed},
        }

    except Exception as exc:
        err_msg = f"Remediator error — rolling back to original invoice: {exc}"
        logs.append(await _log("Remediator", "error", err_msg))
        logger.error(err_msg)

        inv_num = str(state["invoice"].get("invoice_number", "UNKNOWN"))
        audit_trail.record_rollback(inv_num, str(exc))

        return {
            "remediation_result": {
                "updated_invoice": state.get("invoice", {}),
                "remediation_log": [{"status": "ROLLBACK", "detail": str(exc)}],
                "fixed_count": 0,
                "escalated_count": len(investigations),
            },
            "logs": logs,
            "errors": [err_msg],
            "stage_timings": {"remediation_ms": round((time.perf_counter() - t0) * 1000, 1)},
        }


# ─── Node 6: Auditor ─────────────────────────────────────────────────────────

async def auditor_node(state: AuditState) -> dict[str, Any]:
    """
    Compiles the final audit report, stores the invoice embedding for future
    duplicate detection, and closes the audit trail record.
    """
    t0 = time.perf_counter()
    logs = [await _log("Auditor", "info", "Compiling final audit report…")]

    try:
        invoice = state.get("invoice", {})
        compliance_result = {
            "is_compliant": len(state.get("violations", [])) == 0,
            "violation_count": len(state.get("violations", [])),
            "violations": state.get("violations", []),
        }
        remediation_result = state.get("remediation_result", {
            "updated_invoice": invoice,
            "remediation_log": [],
            "fixed_count": 0,
            "escalated_count": 0,
        })

        report = run_audit(
            invoice,
            compliance_result,
            state.get("investigations", []),
            remediation_result,
        )

        # Store embedding AFTER audit, so the current invoice can be used as
        # a reference for future duplicate checks
        if invoice:
            duplicate_detector.store_invoice(invoice)

        # Close the audit trail
        inv_num = str(invoice.get("invoice_number", "UNKNOWN"))
        audit_trail.close_record(
            inv_num,
            report["audit_status"],
            remediation_result.get("updated_invoice", invoice),
        )

        logs.append(await _log(
            "Auditor", "success",
            f"Audit complete — status: {report['audit_status']} | "
            f"violations: {report['metrics']['total_violations']} | "
            f"fixed: {report['metrics']['fixed_count']}"
        ))

        elapsed = round((time.perf_counter() - t0) * 1000, 1)
        await ws_manager.broadcast_event(
            "pipeline_done",
            {
                "audit_status": report["audit_status"],
                "invoice_number": inv_num,
                "duration_ms": elapsed,
            },
        )

        return {
            "audit_report": report,
            "logs": logs,
            "stage_timings": {"audit_ms": elapsed},
        }

    except Exception as exc:
        err_msg = f"Auditor failed: {exc}"
        logs.append(await _log("Auditor", "error", err_msg))
        logger.error(err_msg)
        return {
            "audit_report": {},
            "logs": logs,
            "errors": [err_msg],
            "stage_timings": {"audit_ms": round((time.perf_counter() - t0) * 1000, 1)},
        }
