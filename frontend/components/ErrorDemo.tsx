"use client";

import React, { useState } from "react";
import {
  FlaskConical,
  ScanLine,
  Timer,
  Wrench,
  XCircle,
  ChevronDown,
  ChevronRight,
  RefreshCw,
  CheckCircle2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { AgentLogEntry } from "@/lib/types";

interface ErrorDemoProps {
  onLogEntry: (entry: Omit<AgentLogEntry, "id">) => void;
}

// ─── Scenario definitions ─────────────────────────────────────────────────────

interface Scenario {
  id: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  badgeVariant: "critical" | "high" | "medium";
  badgeLabel: string;
  logs: Array<Omit<AgentLogEntry, "id">>;
  outcome: { title: string; detail: string; type: "error" | "warning" | "info" };
}

const SCENARIOS: Scenario[] = [
  {
    id: "ocr_failure",
    label: "OCR / PDF Failure",
    description:
      "Simulates a corrupted or image-only PDF where text extraction fails entirely.",
    icon: <ScanLine className="h-5 w-5 text-red-400" />,
    badgeVariant: "critical",
    badgeLabel: "Fatal",
    logs: [
      { agent: "System",  level: "info",    message: "Pipeline started. Dispatching intake agent…",              timestamp: "" },
      { agent: "Intake",  level: "info",    message: "Opening PDF stream…",                                      timestamp: "" },
      { agent: "Intake",  level: "warning", message: "No extractable text found — document may be image-only.", timestamp: "" },
      { agent: "Intake",  level: "error",   message: "Text extraction returned null. Aborting pipeline.",        timestamp: "" },
      { agent: "System",  level: "error",   message: "PIPELINE ABORTED: OCR/text extraction failure.",          timestamp: "" },
    ],
    outcome: {
      title: "OCR Failure",
      detail:
        "The uploaded PDF contains no machine-readable text. Please re-scan the document with OCR enabled, or use a text-based PDF.",
      type: "error",
    },
  },
  {
    id: "api_timeout",
    label: "API Timeout",
    description:
      "Simulates the Groq LLM API taking too long to respond, triggering a gateway timeout.",
    icon: <Timer className="h-5 w-5 text-amber-400" />,
    badgeVariant: "high",
    badgeLabel: "Timeout",
    logs: [
      { agent: "System",       level: "info",    message: "Pipeline started.",                                                     timestamp: "" },
      { agent: "Intake",       level: "success", message: "PDF text extracted (2,341 chars).",                                     timestamp: "" },
      { agent: "Intake",       level: "info",    message: "Dispatching LLM request to Groq (llama3-70b-8192)…",                  timestamp: "" },
      { agent: "Intake",       level: "warning", message: "LLM response pending… (5 000ms elapsed)",                              timestamp: "" },
      { agent: "Intake",       level: "warning", message: "LLM response pending… (10 000ms elapsed)",                             timestamp: "" },
      { agent: "Intake",       level: "error",   message: "Request timed out after 15 000ms.",                                    timestamp: "" },
      { agent: "Investigator", level: "error",   message: "Dependency failed — investigation skipped.",                           timestamp: "" },
      { agent: "System",       level: "error",   message: "PIPELINE ABORTED: Groq API timeout (502 Bad Gateway).",               timestamp: "" },
    ],
    outcome: {
      title: "LLM API Timeout",
      detail:
        "The Groq LLM did not respond within the timeout window. This may be a transient service issue. Retry in a moment or check your GROQ_API_KEY.",
      type: "error",
    },
  },
  {
    id: "bad_fix",
    label: "Bad Auto-Fix",
    description:
      "Simulates a GST correction where the risk score is high, blocking auto-fix and forcing escalation.",
    icon: <Wrench className="h-5 w-5 text-orange-400" />,
    badgeVariant: "medium",
    badgeLabel: "Escalated",
    logs: [
      { agent: "System",       level: "info",    message: "Pipeline started.",                                                        timestamp: "" },
      { agent: "Intake",       level: "success", message: "Invoice parsed — ₹4,85,000 | Electronics | GST 5%.",                     timestamp: "" },
      { agent: "Compliance",   level: "warning", message: "GST_MISMATCH detected: expected 18%, found 5% on 'MacBook Pro 16\"'.",    timestamp: "" },
      { agent: "Compliance",   level: "warning", message: "OVER_LIMIT: Invoice total ₹4,85,000 exceeds ₹3,00,000 limit.",           timestamp: "" },
      { agent: "Investigator", level: "info",    message: "Analysing GST_MISMATCH — risk_score: 8 (HIGH).",                         timestamp: "" },
      { agent: "Investigator", level: "info",    message: "Analysing OVER_LIMIT — risk_score: 9 (CRITICAL).",                       timestamp: "" },
      { agent: "Remediator",   level: "warning", message: "GST_MISMATCH risk=8 ≥ threshold 5 → ESCALATED.",                        timestamp: "" },
      { agent: "Remediator",   level: "warning", message: "OVER_LIMIT risk=9 ≥ threshold 5 → ESCALATED.",                          timestamp: "" },
      { agent: "Auditor",      level: "info",    message: "Audit complete — status: ESCALATED | 2 violations | 0 auto-fixed.",      timestamp: "" },
    ],
    outcome: {
      title: "Auto-Fix Blocked — Manual Review Required",
      detail:
        "Both violations carry a risk score ≥ 5. The remediator safely declined to auto-fix and escalated both for human review. No data was altered.",
      type: "warning",
    },
  },
];

// ─── Individual scenario card ─────────────────────────────────────────────────

function ScenarioCard({
  scenario,
  onSimulate,
}: {
  scenario: Scenario;
  onSimulate: (s: Scenario) => void;
}) {
  const [open, setOpen] = useState(false);
  const [ran, setRan] = useState(false);

  const handleSimulate = () => {
    onSimulate(scenario);
    setRan(true);
    setTimeout(() => setRan(false), 3000);
  };

  return (
    <div className="rounded-xl border border-[#1e2d4a] bg-[#0f1629] overflow-hidden">
      <div className="flex items-start gap-3 p-4">
        <div className="mt-0.5 rounded-lg border border-[#1e2d4a] bg-[#0a0f1e] p-2 flex-shrink-0">
          {scenario.icon}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <span className="text-sm font-semibold text-[#e8edf8]">
              {scenario.label}
            </span>
            <Badge variant={scenario.badgeVariant}>{scenario.badgeLabel}</Badge>
          </div>
          <p className="text-xs text-[#8b9cc4] leading-relaxed">
            {scenario.description}
          </p>
        </div>
      </div>

      {/* Collapsible outcome preview */}
      <div className="border-t border-[#1e2d4a]">
        <button
          onClick={() => setOpen((o) => !o)}
          className="flex w-full items-center gap-2 px-4 py-2 text-left hover:bg-[#151d35] transition-colors"
        >
          {open ? (
            <ChevronDown className="h-3.5 w-3.5 text-[#4a5a7a]" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 text-[#4a5a7a]" />
          )}
          <span className="text-xs text-[#4a5a7a]">Preview outcome</span>
        </button>

        {open && (
          <div
            className={cn(
              "mx-4 mb-3 rounded-lg border px-3 py-2.5",
              scenario.outcome.type === "error"
                ? "border-red-500/30 bg-red-950/15"
                : scenario.outcome.type === "warning"
                ? "border-amber-500/30 bg-amber-950/15"
                : "border-blue-500/30 bg-blue-950/15"
            )}
          >
            <p
              className={cn("text-xs font-semibold mb-0.5", {
                "text-red-400": scenario.outcome.type === "error",
                "text-amber-400": scenario.outcome.type === "warning",
                "text-blue-400": scenario.outcome.type === "info",
              })}
            >
              {scenario.outcome.title}
            </p>
            <p className="text-xs text-[#8b9cc4]">{scenario.outcome.detail}</p>
          </div>
        )}
      </div>

      {/* Action */}
      <div className="border-t border-[#1e2d4a] px-4 py-3">
        <Button
          variant={
            scenario.outcome.type === "error"
              ? "destructive"
              : scenario.outcome.type === "warning"
              ? "warning"
              : "outline"
          }
          size="sm"
          className="w-full"
          onClick={handleSimulate}
        >
          {ran ? (
            <>
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
              Simulated — check Agent Log
            </>
          ) : (
            <>
              <RefreshCw className="h-3.5 w-3.5" />
              Simulate Scenario
            </>
          )}
        </Button>
      </div>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function ErrorDemo({ onLogEntry }: ErrorDemoProps) {
  const [expanded, setExpanded] = useState(true);

  const handleSimulate = (scenario: Scenario) => {
    scenario.logs.forEach((log, i) => {
      setTimeout(() => {
        onLogEntry({ ...log, timestamp: new Date().toISOString() });
      }, i * 600);
    });
  };

  return (
    <div className="rounded-xl border border-[#1e2d4a] bg-[#0f1629] overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpanded((e) => !e)}
        className="flex w-full items-center justify-between px-5 py-4 hover:bg-[#151d35] transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="rounded-lg border border-amber-600/30 bg-amber-600/10 p-2">
            <FlaskConical className="h-4 w-4 text-amber-400" />
          </div>
          <div className="text-left">
            <h3 className="text-sm font-semibold text-[#e8edf8]">
              Error Simulation Lab
            </h3>
            <p className="text-xs text-[#4a5a7a]">
              Simulate OCR failures, API timeouts, and escalation scenarios
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="medium">Demo</Badge>
          {expanded ? (
            <ChevronDown className="h-4 w-4 text-[#4a5a7a]" />
          ) : (
            <ChevronRight className="h-4 w-4 text-[#4a5a7a]" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="border-t border-[#1e2d4a] p-4">
          {/* Warning notice */}
          <div className="mb-4 flex items-start gap-2.5 rounded-lg border border-[#1e2d4a] bg-[#0a0f1e] px-3.5 py-3">
            <XCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-[#4a5a7a]" />
            <p className="text-xs text-[#4a5a7a]">
              These are <strong className="text-[#8b9cc4]">frontend-only simulations</strong> —
              no real API calls are made. Log entries are injected into the Agent
              Activity panel to demonstrate how the system handles each failure mode.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            {SCENARIOS.map((scenario) => (
              <ScenarioCard
                key={scenario.id}
                scenario={scenario}
                onSimulate={handleSimulate}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
