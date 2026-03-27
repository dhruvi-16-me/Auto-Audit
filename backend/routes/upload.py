"""
POST /upload — Invoice audit endpoint (LangGraph-powered).

Triggers the full multi-agent pipeline:
  Intake → DuplicateCheck → Compliance → Investigator → Remediator → Auditor

Real-time progress is streamed to all connected WebSocket clients while the
graph runs. The endpoint returns the full structured audit result once the
pipeline completes.
"""
import logging
import time
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from graph.state import create_initial_state
from graph.workflow import audit_workflow
from services.websocket_manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["Invoice Upload"])

_ALLOWED_CONTENT_TYPES = {"application/pdf"}
_MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB


def _validate_file(file: UploadFile) -> None:
    ct = (file.content_type or "").lower()
    if ct not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported content type '{ct}'. Only PDF files are accepted."
            ),
        )


@router.post(
    "",
    summary="Upload an invoice PDF for autonomous multi-agent audit",
    response_description="Full audit report with pipeline trace, violations, and remediation",
)
async def upload_invoice(
    file: UploadFile = File(..., description="Invoice PDF (max 10 MB)"),
) -> JSONResponse:
    """
    Upload an invoice PDF and run the full AutoAudit multi-agent pipeline.

    The pipeline runs as a compiled LangGraph StateGraph:
    1. **Intake** — extracts and structures invoice data via LLM
    2. **DuplicateCheck** — compares against ChromaDB vector store
    3. **Compliance** — checks GST rates and total limits
    4. **Investigator** — LLM root-cause analysis (skipped if compliant)
    5. **Remediator** — auto-fix with rollback (skipped if compliant)
    6. **Auditor** — compiles metrics and closes the audit trail

    Real-time log events are broadcast to all connected WebSocket clients
    at `ws://host/ws` throughout execution.
    """
    _validate_file(file)

    pdf_bytes = await file.read()
    if len(pdf_bytes) > _MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"File too large. Maximum allowed size is "
                f"{_MAX_FILE_BYTES // (1024 * 1024)} MB."
            ),
        )
    if not pdf_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    await ws_manager.broadcast_log(
        "System", "info",
        f"Received '{file.filename}' ({len(pdf_bytes) // 1024} KB) — "
        f"starting multi-agent audit pipeline…"
    )

    wall_start = time.perf_counter()

    # ── Run LangGraph pipeline ────────────────────────────────────────────────
    try:
        initial_state = create_initial_state(pdf_bytes, file.filename or "upload.pdf")
        final_state = await audit_workflow.ainvoke(initial_state)
    except Exception as exc:
        logger.exception("Pipeline raised an unhandled exception: %s", exc)
        await ws_manager.broadcast_log("System", "error", f"Pipeline aborted: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audit pipeline failed: {exc}",
        )

    wall_ms = round((time.perf_counter() - wall_start) * 1000, 1)

    # ── Merge per-stage timings ───────────────────────────────────────────────
    stage_timings: dict[str, Any] = {}
    for node_timings in (final_state.get("stage_timings") or {}).items():
        stage_timings[node_timings[0]] = node_timings[1]

    # ── Build response ────────────────────────────────────────────────────────
    compliance_result = {
        "is_compliant": len(final_state.get("violations", [])) == 0,
        "violation_count": len(final_state.get("violations", [])),
        "violations": final_state.get("violations", []),
    }

    pipeline_errors = final_state.get("errors", [])

    response_body: dict[str, Any] = {
        "status": "success" if not pipeline_errors else "partial",
        "filename": file.filename,
        "pipeline_duration_ms": wall_ms,
        "stage_timings_ms": stage_timings,
        "duplicate_detected": final_state.get("duplicate_detected", False),
        "duplicate_info": final_state.get("duplicate_info"),
        "audit_report": final_state.get("audit_report", {}),
        "raw_invoice": final_state.get("invoice", {}),
        "compliance": compliance_result,
        "investigations": final_state.get("investigations", []),
        "pipeline_logs": final_state.get("logs", []),
        "pipeline_errors": pipeline_errors,
    }

    return JSONResponse(
        content=response_body,
        status_code=status.HTTP_200_OK,
    )
