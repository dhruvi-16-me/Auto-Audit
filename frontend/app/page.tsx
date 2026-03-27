"use client";

import React, { useCallback, useRef, useState } from "react";
import {
  ShieldCheck,
  Cpu,
  LayoutDashboard,
  GitBranch,
  ExternalLink,
  AlertCircle,
  X,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import FileUpload from "@/components/FileUpload";
import AgentLog from "@/components/AgentLog";
import MetricsCards from "@/components/MetricsCards";
import ResultsViewer from "@/components/ResultsViewer";
import ErrorDemo from "@/components/ErrorDemo";
import type { AgentLogEntry, AuditResponse } from "@/lib/types";

// ─── Unique log entry ID generator ───────────────────────────────────────────

let _logId = 0;
const nextId = () => `log-${++_logId}`;

// ─── Toast notification ───────────────────────────────────────────────────────

interface ToastProps {
  message: string;
  onClose: () => void;
}

function Toast({ message, onClose }: ToastProps) {
  return (
    <div className="fade-in-up flex items-start gap-3 rounded-xl border border-red-500/30 bg-red-950/30 px-4 py-3 shadow-2xl backdrop-blur-sm max-w-sm">
      <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-red-400" />
      <p className="flex-1 text-sm text-red-300">{message}</p>
      <button
        onClick={onClose}
        className="flex-shrink-0 text-red-500 hover:text-red-300 transition-colors"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

// ─── Sidebar nav link ─────────────────────────────────────────────────────────

function NavLink({
  icon,
  label,
  active = false,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-all",
        active
          ? "bg-blue-600/15 text-blue-400 border border-blue-600/25"
          : "text-[#4a5a7a] hover:bg-[#151d35] hover:text-[#8b9cc4]"
      )}
    >
      {icon}
      <span className="font-medium">{label}</span>
      {active && <ChevronRight className="ml-auto h-3.5 w-3.5 opacity-60" />}
    </button>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function Home() {
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<AuditResponse | null>(null);
  const [logEntries, setLogEntries] = useState<AgentLogEntry[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const addLogEntry = useCallback((entry: Omit<AgentLogEntry, "id">) => {
    setLogEntries((prev) => [
      ...prev,
      { ...entry, id: nextId() },
    ]);
  }, []);

  const showError = (msg: string) => {
    setErrorMsg(msg);
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setErrorMsg(null), 6000);
  };

  const handleUploadStart = () => {
    setIsLoading(true);
    setResult(null);
    setErrorMsg(null);
  };

  const handleResult = (data: AuditResponse) => {
    setResult(data);
    setIsLoading(false);
    addLogEntry({
      agent: "System",
      level: "success",
      message: `Audit complete — ${data.audit_report.audit_status} | ${data.audit_report.metrics.total_violations} violation(s)`,
      timestamp: new Date().toISOString(),
    });
  };

  const handleError = (msg: string) => {
    setIsLoading(false);
    showError(msg);
  };

  const clearLogs = () => setLogEntries([]);

  const auditStatus = result?.audit_report.audit_status;

  return (
    <div className="flex h-screen overflow-hidden bg-[#0a0f1e]">
      {/* ── Sidebar ─────────────────────────────────────────────────────── */}
      <aside className="flex w-56 flex-shrink-0 flex-col border-r border-[#1e2d4a] bg-[#0d1322]">
        {/* Logo */}
        <div className="flex items-center gap-2.5 border-b border-[#1e2d4a] px-4 py-5">
          <div className="relative">
            <div className="absolute inset-0 rounded-lg bg-blue-500/30 blur-md" />
            <div className="relative rounded-lg border border-blue-600/40 bg-blue-600/20 p-2">
              <ShieldCheck className="h-5 w-5 text-blue-400" />
            </div>
          </div>
          <div>
            <p className="text-sm font-bold text-[#e8edf8] leading-none">
              AutoAudit
            </p>
            <p className="text-[10px] text-blue-400 mt-0.5 font-medium tracking-wider uppercase">
              AI Compliance
            </p>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 space-y-1 overflow-y-auto p-3">
          <div className="mb-2">
            <p className="px-3 py-1 text-[10px] font-semibold uppercase tracking-widest text-[#2a3f6a]">
              Main
            </p>
            <NavLink
              icon={<LayoutDashboard className="h-4 w-4" />}
              label="Dashboard"
              active
            />
            <NavLink
              icon={<Cpu className="h-4 w-4" />}
              label="Agent Lab"
              onClick={() =>
                document
                  .getElementById("error-lab")
                  ?.scrollIntoView({ behavior: "smooth" })
              }
            />
          </div>
        </nav>

        {/* Status badge */}
        <div className="border-t border-[#1e2d4a] p-3">
          {auditStatus ? (
            <div
              className={cn(
                "rounded-lg border px-3 py-2.5 text-center",
                auditStatus === "CLEAN" || auditStatus === "FIXED"
                  ? "border-emerald-600/30 bg-emerald-600/10"
                  : auditStatus === "ESCALATED"
                  ? "border-red-600/30 bg-red-600/10"
                  : "border-amber-600/30 bg-amber-600/10"
              )}
            >
              <p className="text-[10px] uppercase tracking-widest text-[#4a5a7a]">
                Last Audit
              </p>
              <p
                className={cn("mt-0.5 text-sm font-bold", {
                  "text-emerald-400":
                    auditStatus === "CLEAN" || auditStatus === "FIXED",
                  "text-red-400": auditStatus === "ESCALATED",
                  "text-amber-400": auditStatus === "PARTIALLY_FIXED",
                })}
              >
                {auditStatus}
              </p>
            </div>
          ) : (
            <div className="rounded-lg border border-[#1e2d4a] bg-[#0a0f1e] px-3 py-2.5 text-center">
              <p className="text-[10px] uppercase tracking-widest text-[#2a3f6a]">
                No audit yet
              </p>
              <p className="mt-0.5 text-xs text-[#4a5a7a]">Upload to begin</p>
            </div>
          )}

          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="mt-2 flex items-center gap-2 rounded-lg px-3 py-2 text-xs text-[#4a5a7a] hover:bg-[#151d35] hover:text-[#8b9cc4] transition-colors"
          >
            <ExternalLink className="h-3.5 w-3.5" />
            API Docs
          </a>
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 rounded-lg px-3 py-2 text-xs text-[#4a5a7a] hover:bg-[#151d35] hover:text-[#8b9cc4] transition-colors"
          >
            <GitBranch className="h-3.5 w-3.5" />
            GitHub
          </a>
        </div>
      </aside>

      {/* ── Main content ─────────────────────────────────────────────────── */}
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex flex-shrink-0 items-center justify-between border-b border-[#1e2d4a] bg-[#0d1322] px-6 py-3.5">
          <div>
            <h1 className="text-base font-bold text-[#e8edf8]">
              Invoice Audit Dashboard
            </h1>
            <p className="text-xs text-[#4a5a7a]">
              AI-powered compliance · Investigation · Auto-remediation
            </p>
          </div>

          {/* Live indicator */}
          <div className="flex items-center gap-2 rounded-full border border-[#1e2d4a] bg-[#0a0f1e] px-3 py-1.5">
            <span
              className={cn("h-2 w-2 rounded-full flex-shrink-0", {
                "bg-emerald-400 pulse-dot": isLoading,
                "bg-blue-400": !isLoading && result,
                "bg-[#2a3f6a]": !isLoading && !result,
              })}
            />
            <span className="text-xs text-[#8b9cc4]">
              {isLoading
                ? "Pipeline running…"
                : result
                ? "Audit complete"
                : "Idle"}
            </span>
          </div>
        </header>

        {/* Scrollable body */}
        <main className="flex-1 overflow-y-auto p-6">
          <div className="mx-auto max-w-7xl space-y-6">
            {/* ── Row 1: Metrics ── */}
            <MetricsCards report={result?.audit_report ?? null} isLoading={isLoading} />

            {/* ── Row 2: Upload + Agent Log ── */}
            <div className="grid gap-5 lg:grid-cols-2">
              {/* Upload panel */}
              <div className="rounded-xl border border-[#1e2d4a] bg-[#0f1629] p-5">
                <div className="mb-4 flex items-center gap-2.5">
                  <div className="rounded-lg border border-blue-600/30 bg-blue-600/10 p-1.5">
                    <ShieldCheck className="h-4 w-4 text-blue-400" />
                  </div>
                  <div>
                    <h2 className="text-sm font-semibold text-[#e8edf8]">
                      Upload Invoice
                    </h2>
                    <p className="text-xs text-[#4a5a7a]">
                      PDF · max 10 MB
                    </p>
                  </div>
                </div>
                <FileUpload
                  onUploadStart={handleUploadStart}
                  onLogEntry={addLogEntry}
                  onResult={handleResult}
                  onError={handleError}
                  isLoading={isLoading}
                />
              </div>

              {/* Agent log panel */}
              <div className="min-h-[340px]">
                <AgentLog
                  entries={logEntries}
                  isLoading={isLoading}
                  onClear={clearLogs}
                />
              </div>
            </div>

            {/* ── Row 3: Results ── */}
            <div className="rounded-xl border border-[#1e2d4a] bg-[#0f1629] p-5">
              <div className="mb-4 flex items-center gap-2.5">
                <div className="rounded-lg border border-purple-600/30 bg-purple-600/10 p-1.5">
                  <Cpu className="h-4 w-4 text-purple-400" />
                </div>
                <div>
                  <h2 className="text-sm font-semibold text-[#e8edf8]">
                    Audit Results
                  </h2>
                  <p className="text-xs text-[#4a5a7a]">
                    Violations · remediation · invoice detail · raw JSON
                  </p>
                </div>
              </div>
              <ResultsViewer data={result} />
            </div>

            {/* ── Row 4: Error simulation lab ── */}
            <div id="error-lab">
              <ErrorDemo onLogEntry={addLogEntry} />
            </div>

            {/* Footer */}
            <div className="border-t border-[#1e2d4a] pt-4 text-center text-xs text-[#2a3f6a]">
              AutoAudit AI · Built with Next.js 14 + FastAPI + Groq LLaMA 3 ·
              GST compliance engine v1.0
            </div>
          </div>
        </main>
      </div>

      {/* ── Toast ──────────────────────────────────────────────────────────── */}
      {errorMsg && (
        <div className="fixed bottom-6 right-6 z-50">
          <Toast message={errorMsg} onClose={() => setErrorMsg(null)} />
        </div>
      )}
    </div>
  );
}
