"""
AuditState — the shared state object that flows through every node
in the LangGraph multi-agent pipeline.

LangGraph reads field annotations to decide *how* to merge updates:
  - Plain fields        → last-write wins (each node can overwrite)
  - Annotated[list, operator.add] → reducer appends new items
"""
import operator
from datetime import datetime
from typing import Annotated, Any, Optional, TypedDict


# ─── Embedded sub-types ───────────────────────────────────────────────────────

class LogEntry(TypedDict):
    agent: str
    level: str      # "info" | "success" | "warning" | "error"
    message: str
    timestamp: str


# ─── Main pipeline state ──────────────────────────────────────────────────────

class AuditState(TypedDict):
    # ── Input ────────────────────────────────────────────────────────────────
    pdf_bytes: bytes          # raw PDF content (not serialised to disk)
    filename: str

    # ── Agent outputs ─────────────────────────────────────────────────────────
    invoice: dict[str, Any]                    # Intake result
    violations: list[dict[str, Any]]           # Compliance findings
    investigations: list[dict[str, Any]]       # Investigator enrichments
    remediation_result: dict[str, Any]         # Remediator output
    audit_report: dict[str, Any]               # Final auditor report

    # ── Accumulative fields (reducer = list append) ───────────────────────────
    logs: Annotated[list[LogEntry], operator.add]
    errors: Annotated[list[str], operator.add]

    # ── Retry bookkeeping (per-node retry count) ──────────────────────────────
    retry_counts: dict[str, int]

    # ── Timing ────────────────────────────────────────────────────────────────
    stage_timings: dict[str, float]     # ms per stage, merged by nodes
    started_at: str                     # ISO timestamp of pipeline start

    # ── Duplicate detection ───────────────────────────────────────────────────
    duplicate_detected: bool
    duplicate_info: Optional[dict[str, Any]]


# ─── Factory ─────────────────────────────────────────────────────────────────

def create_initial_state(pdf_bytes: bytes, filename: str) -> AuditState:
    """Build a fresh AuditState for a new pipeline run."""
    return AuditState(
        pdf_bytes=pdf_bytes,
        filename=filename,
        invoice={},
        violations=[],
        investigations=[],
        remediation_result={},
        audit_report={},
        logs=[],
        errors=[],
        retry_counts={},
        stage_timings={},
        started_at=datetime.utcnow().isoformat(),
        duplicate_detected=False,
        duplicate_info=None,
    )


# ─── Helper: build a log entry ────────────────────────────────────────────────

def make_log(agent: str, level: str, message: str) -> LogEntry:
    return LogEntry(
        agent=agent,
        level=level,
        message=message,
        timestamp=datetime.utcnow().isoformat(),
    )
