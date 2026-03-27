"""
Demo Endpoints — failure simulation for frontend testing.
----------------------------------------------------------
These endpoints simulate specific failure modes WITHOUT touching real PDFs
or the LLM API. They inject pre-scripted log sequences into the WebSocket
broadcast so the frontend Agent Log panel shows realistic behaviour.

Endpoints:
  POST /demo/ocr-failure    → corrupted / image-only PDF
  POST /demo/api-timeout    → Groq LLM takes too long
  POST /demo/bad-fix        → high-risk violations force escalation

  GET  /demo/audit-trail           → list all audit trail records
  GET  /demo/audit-trail/{inv_num} → full record for one invoice
  GET  /demo/stats                 → system health / counters
"""
import asyncio
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from services.audit_trail import audit_trail
from services.duplicate_detector import duplicate_detector
from services.websocket_manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/demo", tags=["Demo & Diagnostics"])


# ─── Helper: replay a log sequence over WebSocket ────────────────────────────

async def _play_logs(
    sequence: list[tuple[str, str, str, float]],
) -> None:
    """
    Broadcast a scripted log sequence with realistic delays.

    Args:
        sequence: list of (agent, level, message, delay_seconds)
    """
    for agent, level, message, delay in sequence:
        await ws_manager.broadcast_log(agent, level, message)
        if delay > 0:
            await asyncio.sleep(delay)


# ─── Scenario: OCR failure ────────────────────────────────────────────────────

@router.post(
    "/ocr-failure",
    summary="Simulate a corrupted / image-only PDF that yields no text",
)
async def demo_ocr_failure() -> JSONResponse:
    """
    Demonstrates what happens when PyMuPDF cannot extract text from the
    uploaded PDF (e.g. scanned image without OCR layer).
    """
    sequence: list[tuple[str, str, str, float]] = [
        ("System",  "info",    "Demo scenario: OCR / text-extraction failure", 0.2),
        ("Intake",  "info",    "Opening PDF stream…",                          0.4),
        ("Intake",  "info",    "Analysing document structure…",                0.5),
        ("Intake",  "warning", "No machine-readable text layer found.",        0.4),
        ("Intake",  "warning", "Document appears to be image-only or corrupted.", 0.4),
        ("Intake",  "error",   "Text extraction returned null — aborting.",    0.3),
        ("System",  "error",   "PIPELINE ABORTED: OCR / text-extraction failure.", 0.0),
    ]

    await _play_logs(sequence)
    await ws_manager.broadcast_event(
        "pipeline_done",
        {"audit_status": "ABORTED", "error": "ocr_failure"},
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "scenario": "ocr_failure",
            "status": "error",
            "error_code": "TEXT_EXTRACTION_NULL",
            "message": (
                "The PDF contains no machine-readable text. "
                "Please apply OCR (e.g. Adobe Acrobat, Tesseract) and re-upload."
            ),
            "recovery_steps": [
                "Run the PDF through an OCR tool.",
                "Ensure the document is not password-protected.",
                "Try exporting from the source application as a text-based PDF.",
            ],
            "simulated_at": datetime.utcnow().isoformat(),
        },
    )


# ─── Scenario: API / LLM timeout ─────────────────────────────────────────────

@router.post(
    "/api-timeout",
    summary="Simulate a Groq LLM API timeout during invoice parsing",
)
async def demo_api_timeout() -> JSONResponse:
    """
    Demonstrates the retry + eventual failure behaviour when the Groq
    LLM API does not respond within the timeout window.
    Shows all 3 tenacity retry attempts with exponential back-off.
    """
    sequence: list[tuple[str, str, str, float]] = [
        ("System",  "info",    "Demo scenario: LLM API timeout",                    0.2),
        ("Intake",  "success", "PDF text extracted (2 341 characters).",            0.4),
        ("Intake",  "info",    "Dispatching LLM request to Groq (llama3-70b-8192)…", 0.5),
        ("Intake",  "warning", "LLM response pending… (5 000 ms elapsed)",          0.8),
        ("Intake",  "warning", "Attempt 1/3 timed out. Retrying in 2 s…",           0.9),
        ("Intake",  "warning", "LLM response pending… (9 000 ms elapsed)",          0.8),
        ("Intake",  "warning", "Attempt 2/3 timed out. Retrying in 4 s…",           0.9),
        ("Intake",  "warning", "LLM response pending… (17 000 ms elapsed)",         0.8),
        ("Intake",  "error",   "Attempt 3/3 failed. All retries exhausted.",        0.4),
        ("System",  "error",   "PIPELINE ABORTED: Groq API timeout (502 Bad Gateway).", 0.0),
    ]

    await _play_logs(sequence)
    await ws_manager.broadcast_event(
        "pipeline_done",
        {"audit_status": "ABORTED", "error": "api_timeout"},
    )

    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={
            "scenario": "api_timeout",
            "status": "error",
            "error_code": "LLM_TIMEOUT_ALL_RETRIES",
            "message": (
                "The Groq LLM API did not respond after 3 attempts "
                "(2 s / 4 s / 8 s back-off)."
            ),
            "retry_attempts": 3,
            "recovery_steps": [
                "Verify GROQ_API_KEY is valid and not rate-limited.",
                "Check Groq service status at status.groq.com.",
                "Retry the upload in a few minutes.",
            ],
            "simulated_at": datetime.utcnow().isoformat(),
        },
    )


# ─── Scenario: Bad fix / forced escalation ────────────────────────────────────

@router.post(
    "/bad-fix",
    summary="Simulate high-risk violations that block auto-fix and force escalation",
)
async def demo_bad_fix() -> JSONResponse:
    """
    Demonstrates the remediator's risk-gating logic: when violations have a
    risk_score ≥ threshold (5), the agent refuses to auto-fix and escalates.
    Also shows a rollback event for illustration.
    """
    sequence: list[tuple[str, str, str, float]] = [
        ("System",       "info",    "Demo scenario: high-risk violations + rollback",                0.2),
        ("Intake",       "success", "Invoice parsed — ₹4,85,000 | Electronics | GST 5%",            0.4),
        ("DuplicateChecker", "success", "No duplicate found — proceeding.",                          0.3),
        ("Compliance",   "warning", "GST_MISMATCH: expected 18%, found 5% on 'MacBook Pro 16″'.",   0.4),
        ("Compliance",   "warning", "OVER_LIMIT: ₹4,85,000 exceeds ₹3,00,000 limit by ₹1,85,000.", 0.4),
        ("Investigator", "info",    "Analysing GST_MISMATCH — calling LLM…",                        0.5),
        ("Investigator", "warning", "GST_MISMATCH → risk_score: 8 / 10 (HIGH confidence: 91%)",     0.4),
        ("Investigator", "info",    "Analysing OVER_LIMIT — calling LLM…",                          0.5),
        ("Investigator", "warning", "OVER_LIMIT → risk_score: 9 / 10 (CRITICAL confidence: 96%)",  0.4),
        ("Remediator",   "info",    "Attempting auto-fix for GST_MISMATCH…",                        0.4),
        ("Remediator",   "warning", "risk_score 8 ≥ threshold 5 — auto-fix BLOCKED.",              0.3),
        ("Remediator",   "error",   "GST_MISMATCH ROLLED BACK — escalating to manual review.",      0.3),
        ("Remediator",   "warning", "OVER_LIMIT risk_score 9 ≥ threshold 5 — ESCALATED.",          0.3),
        ("Auditor",      "info",    "Compiling audit report…",                                       0.3),
        ("Auditor",      "warning", "Audit complete — ESCALATED | 2 violations | 0 fixed.",         0.0),
    ]

    await _play_logs(sequence)
    await ws_manager.broadcast_event(
        "pipeline_done",
        {"audit_status": "ESCALATED", "fixed": 0, "escalated": 2},
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "scenario": "bad_fix",
            "status": "escalated",
            "audit_status": "ESCALATED",
            "violations": [
                {
                    "rule": "GST_MISMATCH",
                    "severity": "HIGH",
                    "risk_score": 8,
                    "action": "escalate",
                    "status": "ROLLED_BACK",
                    "message": (
                        "GST rate 5% found on 'MacBook Pro 16\"'; "
                        "expected 18% for electronics."
                    ),
                },
                {
                    "rule": "OVER_LIMIT",
                    "severity": "CRITICAL",
                    "risk_score": 9,
                    "action": "escalate",
                    "status": "ESCALATED",
                    "message": "Invoice total ₹4,85,000 exceeds ₹3,00,000 limit.",
                },
            ],
            "message": (
                "Both violations carry risk scores above the auto-fix threshold. "
                "The remediator safely declined to auto-fix and escalated both "
                "violations for human review. No invoice data was modified."
            ),
            "simulated_at": datetime.utcnow().isoformat(),
        },
    )


# ─── Audit trail endpoints ────────────────────────────────────────────────────

@router.get(
    "/audit-trail",
    summary="List all audit trail records (most recent first)",
)
async def list_audit_trail() -> JSONResponse:
    records = list(reversed(audit_trail.list_all()))
    return JSONResponse(
        content={
            "total": len(records),
            "records": records,
        }
    )


@router.get(
    "/audit-trail/{invoice_number}",
    summary="Get the full audit trail for a specific invoice",
)
async def get_audit_trail(invoice_number: str) -> JSONResponse:
    record = audit_trail.get_full_record(invoice_number)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No audit trail found for invoice '{invoice_number}'.",
        )
    return JSONResponse(content=record)


# ─── System stats ─────────────────────────────────────────────────────────────

@router.get(
    "/stats",
    summary="Real-time system health and pipeline counters",
)
async def system_stats() -> JSONResponse:
    return JSONResponse(
        content={
            "websocket_connections": ws_manager.connection_count,
            "invoices_in_store": duplicate_detector.stored_count,
            "audit_trail_records": audit_trail.total_records,
            "duplicate_detector_ready": duplicate_detector.is_ready,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )
