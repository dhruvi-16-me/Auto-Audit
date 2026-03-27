"""
LangGraph Workflow
------------------
Builds and compiles the AutoAudit AI multi-agent pipeline as a directed
StateGraph. The graph is compiled once at module import time and reused
for every request.

Pipeline topology:
                       ┌──────────────────┐
                       │      START        │
                       └────────┬─────────┘
                                │
                          ┌─────▼──────┐
                          │   Intake   │  ← PDF parse + LLM extraction
                          └─────┬──────┘
                                │
                   ┌────────────▼──────────────┐
                   │   DuplicateCheck          │  ← ChromaDB similarity
                   └────────────┬──────────────┘
                                │
                   ┌────────────▼──────────────┐
                   │      Compliance           │  ← Rule-based checks
                   └────────────┬──────────────┘
                                │ (violations found?)
                   ╔════════════╩══════════════╗
                   ║  yes                  no  ║
          ┌────────▼────────┐       ┌──────────▼──────────┐
          │  Investigator   │       │      Auditor         │
          └────────┬────────┘       └──────────────────────┘
                   │
          ┌────────▼────────┐
          │   Remediator    │
          └────────┬────────┘
                   │
          ┌────────▼────────┐
          │     Auditor     │
          └────────┬────────┘
                   │
                   END
"""
import logging
from typing import Literal

from langgraph.graph import END, START, StateGraph

from graph.nodes import (
    auditor_node,
    compliance_node,
    duplicate_check_node,
    intake_node,
    investigator_node,
    remediator_node,
)
from graph.state import AuditState

logger = logging.getLogger(__name__)


# ─── Conditional routing function ────────────────────────────────────────────

def _route_after_compliance(
    state: AuditState,
) -> Literal["investigator", "auditor"]:
    """
    Skip investigation/remediation if the invoice is already compliant.
    This saves LLM calls when there is nothing to investigate.
    """
    has_violations = len(state.get("violations", [])) > 0
    return "investigator" if has_violations else "auditor"


# ─── Graph builder ────────────────────────────────────────────────────────────

def build_workflow():
    """
    Construct, wire, and compile the AutoAudit StateGraph.

    Returns:
        A compiled LangGraph runnable (supports `.ainvoke()`).
    """
    graph = StateGraph(AuditState)

    # Register nodes
    graph.add_node("intake",          intake_node)
    graph.add_node("duplicate_check", duplicate_check_node)
    graph.add_node("compliance",      compliance_node)
    graph.add_node("investigator",    investigator_node)
    graph.add_node("remediator",      remediator_node)
    graph.add_node("auditor",         auditor_node)

    # Entry point
    graph.add_edge(START, "intake")

    # Linear edges
    graph.add_edge("intake",          "duplicate_check")
    graph.add_edge("duplicate_check", "compliance")

    # Conditional branch: skip investigation when invoice is clean
    graph.add_conditional_edges(
        "compliance",
        _route_after_compliance,
        {
            "investigator": "investigator",
            "auditor":      "auditor",
        },
    )

    graph.add_edge("investigator", "remediator")
    graph.add_edge("remediator",   "auditor")
    graph.add_edge("auditor",      END)

    compiled = graph.compile()
    logger.info("AutoAudit LangGraph workflow compiled successfully.")
    return compiled


# ─── Module-level singleton ────────────────────────────────────────────────────
# Compiled once; all requests share this instance (thread-/coroutine-safe
# for read-only invocations because LangGraph creates a fresh state per run).
audit_workflow = build_workflow()
