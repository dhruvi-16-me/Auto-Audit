"""
Audit Trail Service
--------------------
Maintains a tamper-evident, in-memory log of every action taken on every
invoice throughout its lifecycle.

Each invoice has one AuditRecord containing:
  - The original extracted invoice data
  - A chronological list of events (intake, compliance findings, fixes, etc.)
  - Final audit status

In production this would be backed by a persistent store (Supabase, PostgreSQL,
or an append-only event log). The interface is kept storage-agnostic so swapping
backends only requires changing this module.
"""
import logging
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AuditRecord:
    """Immutable-style record for one invoice's full lifecycle."""

    def __init__(self, invoice_number: str, filename: str) -> None:
        self.invoice_number = invoice_number
        self.filename = filename
        self.created_at = datetime.utcnow().isoformat()
        self.events: list[dict[str, Any]] = []
        self.original_invoice: dict[str, Any] = {}
        self.final_invoice: dict[str, Any] = {}
        self.final_status: str = "PENDING"

    def add_event(
        self,
        stage: str,
        action: str,
        data: dict[str, Any],
        level: str = "info",
    ) -> None:
        self.events.append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "stage": stage,
                "action": action,
                "level": level,
                "data": data,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "invoice_number": self.invoice_number,
            "filename": self.filename,
            "created_at": self.created_at,
            "final_status": self.final_status,
            "original_invoice": self.original_invoice,
            "final_invoice": self.final_invoice,
            "event_count": len(self.events),
            "events": self.events,
        }


class AuditTrailService:
    """
    Central audit trail registry.

    Thread-safety note: FastAPI is async; all mutations happen in the same
    event loop, so a plain dict is safe here. For multi-process deployments
    use Redis or a DB with optimistic locking.
    """

    def __init__(self) -> None:
        self._records: dict[str, AuditRecord] = {}

    # ── Record lifecycle ──────────────────────────────────────────────────────

    def open_record(self, invoice_number: str, filename: str) -> AuditRecord:
        """Create or reset the record for an invoice."""
        record = AuditRecord(invoice_number, filename)
        self._records[invoice_number] = record
        logger.debug("Audit trail opened for invoice %s", invoice_number)
        return record

    def get_record(self, invoice_number: str) -> Optional[AuditRecord]:
        return self._records.get(invoice_number)

    def close_record(
        self,
        invoice_number: str,
        final_status: str,
        final_invoice: dict[str, Any],
    ) -> None:
        record = self._records.get(invoice_number)
        if record:
            record.final_status = final_status
            record.final_invoice = final_invoice
            record.add_event(
                stage="Auditor",
                action="audit_closed",
                level="success",
                data={"final_status": final_status},
            )

    # ── Convenience recorders ─────────────────────────────────────────────────

    def record_intake(
        self,
        invoice_number: str,
        invoice: dict[str, Any],
        filename: str,
    ) -> None:
        record = self._records.get(invoice_number) or self.open_record(
            invoice_number, filename
        )
        record.original_invoice = invoice
        record.add_event(
            stage="Intake",
            action="invoice_extracted",
            level="info",
            data={
                "vendor": invoice.get("vendor_name"),
                "total": invoice.get("total_amount"),
                "category": invoice.get("category"),
            },
        )

    def record_violations(
        self, invoice_number: str, violations: list[dict[str, Any]]
    ) -> None:
        record = self._records.get(invoice_number)
        if not record:
            return
        for v in violations:
            record.add_event(
                stage="Compliance",
                action="violation_found",
                level="warning",
                data={
                    "rule": v.get("rule"),
                    "severity": v.get("severity"),
                    "message": v.get("message"),
                },
            )

    def record_fix(
        self,
        invoice_number: str,
        rule: str,
        status: str,
        detail: str,
    ) -> None:
        record = self._records.get(invoice_number)
        if not record:
            return
        record.add_event(
            stage="Remediator",
            action="fix_applied" if status == "AUTO_FIXED" else "escalation",
            level="success" if status == "AUTO_FIXED" else "warning",
            data={"rule": rule, "status": status, "detail": detail},
        )

    def record_rollback(self, invoice_number: str, reason: str) -> None:
        record = self._records.get(invoice_number)
        if not record:
            return
        record.add_event(
            stage="Remediator",
            action="rollback",
            level="error",
            data={"reason": reason},
        )

    # ── Query interface ───────────────────────────────────────────────────────

    def list_all(self) -> list[dict[str, Any]]:
        return [
            {
                "invoice_number": r.invoice_number,
                "filename": r.filename,
                "created_at": r.created_at,
                "final_status": r.final_status,
                "event_count": len(r.events),
            }
            for r in self._records.values()
        ]

    def get_full_record(self, invoice_number: str) -> Optional[dict[str, Any]]:
        record = self._records.get(invoice_number)
        return record.to_dict() if record else None

    @property
    def total_records(self) -> int:
        return len(self._records)


# ─── Singleton ────────────────────────────────────────────────────────────────
audit_trail = AuditTrailService()
