"use client";

import React, { useState } from "react";
import {
  ShieldCheck,
  ShieldAlert,
  Wrench,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Copy,
  CheckCheck,
  FileJson2,
  ReceiptText,
  Activity,
  Clock,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { AuditResponse, Violation, RemediationLogEntry } from "@/lib/types";

interface ResultsViewerProps {
  data: AuditResponse | null;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function severityBadgeVariant(
  sev?: string
): "critical" | "high" | "medium" | "low" | "neutral" {
  switch (sev?.toUpperCase()) {
    case "CRITICAL": return "critical";
    case "HIGH":     return "high";
    case "MEDIUM":   return "medium";
    case "LOW":      return "low";
    default:         return "neutral";
  }
}

function auditStatusConfig(status: string) {
  switch (status) {
    case "CLEAN":
      return { label: "Clean", color: "text-emerald-400", bg: "bg-emerald-500/10 border-emerald-500/30", icon: <ShieldCheck className="h-4 w-4" /> };
    case "FIXED":
      return { label: "Fixed", color: "text-blue-400",    bg: "bg-blue-500/10 border-blue-500/30",       icon: <Wrench className="h-4 w-4" /> };
    case "PARTIALLY_FIXED":
      return { label: "Partially Fixed", color: "text-amber-400", bg: "bg-amber-500/10 border-amber-500/30", icon: <AlertTriangle className="h-4 w-4" /> };
    case "ESCALATED":
      return { label: "Escalated", color: "text-red-400",  bg: "bg-red-500/10 border-red-500/30",         icon: <ShieldAlert className="h-4 w-4" /> };
    default:
      return { label: status, color: "text-[#8b9cc4]", bg: "bg-[#1a2340] border-[#1e2d4a]", icon: null };
  }
}

// ─── Copy-to-clipboard button ─────────────────────────────────────────────────

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Button variant="ghost" size="sm" onClick={copy} className="h-7 px-2">
      {copied ? (
        <CheckCheck className="h-3.5 w-3.5 text-emerald-400" />
      ) : (
        <Copy className="h-3.5 w-3.5" />
      )}
    </Button>
  );
}

// ─── Collapsible section ──────────────────────────────────────────────────────

function Section({
  title,
  children,
  defaultOpen = true,
  badge,
}: {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
  badge?: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-lg border border-[#1e2d4a] overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-[#151d35] transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-[#e8edf8]">{title}</span>
          {badge}
        </div>
        {open ? (
          <ChevronDown className="h-4 w-4 text-[#4a5a7a]" />
        ) : (
          <ChevronRight className="h-4 w-4 text-[#4a5a7a]" />
        )}
      </button>
      {open && <div className="border-t border-[#1e2d4a]">{children}</div>}
    </div>
  );
}

// ─── Violation card ───────────────────────────────────────────────────────────

function ViolationCard({ v, index }: { v: Violation; index: number }) {
  const [open, setOpen] = useState(true);

  return (
    <div
      className={cn(
        "rounded-lg border transition-all",
        v.severity === "CRITICAL"
          ? "border-red-500/40 bg-red-950/20"
          : v.severity === "HIGH"
          ? "border-orange-500/30 bg-orange-950/10"
          : "border-amber-500/30 bg-amber-950/10"
      )}
    >
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-start gap-3 p-4 text-left"
      >
        <div className="mt-0.5 flex-shrink-0 rounded-full border border-red-500/30 bg-red-500/10 p-1.5">
          <ShieldAlert className="h-3.5 w-3.5 text-red-400" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={severityBadgeVariant(v.severity)}>
              {v.severity}
            </Badge>
            <Badge variant="neutral" className="font-mono text-[10px]">
              {v.rule}
            </Badge>
            {v.risk_score !== undefined && (
              <Badge
                variant={v.risk_score >= 7 ? "critical" : v.risk_score >= 4 ? "high" : "success"}
              >
                Risk {v.risk_score}/10
              </Badge>
            )}
          </div>
          <p className="mt-1.5 text-sm text-[#8b9cc4]">{v.message}</p>
        </div>
        <div className="flex-shrink-0 text-[#4a5a7a]">
          {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </div>
      </button>

      {open && (
        <div className="border-t border-[#1e2d4a]/60 px-4 pb-4 pt-3 grid grid-cols-2 gap-3 text-xs">
          {v.cause && (
            <div className="col-span-2">
              <p className="text-[#4a5a7a] uppercase tracking-wider text-[10px] mb-1">
                Root Cause
              </p>
              <p className="text-[#8b9cc4]">{v.cause}</p>
            </div>
          )}
          {v.action && (
            <div>
              <p className="text-[#4a5a7a] uppercase tracking-wider text-[10px] mb-1">
                Action
              </p>
              <span
                className={cn("rounded px-2 py-0.5 font-mono", {
                  "bg-emerald-500/10 text-emerald-400": v.action === "auto_fix",
                  "bg-red-500/10 text-red-400": v.action === "escalate",
                  "bg-amber-500/10 text-amber-400": v.action === "review",
                })}
              >
                {v.action}
              </span>
            </div>
          )}
          {v.confidence !== undefined && (
            <div>
              <p className="text-[#4a5a7a] uppercase tracking-wider text-[10px] mb-1">
                Confidence
              </p>
              <div className="flex items-center gap-2">
                <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[#1a2340]">
                  <div
                    className="h-full rounded-full bg-blue-500"
                    style={{ width: `${(v.confidence * 100).toFixed(0)}%` }}
                  />
                </div>
                <span className="text-[#8b9cc4]">
                  {(v.confidence * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          )}
          {v.expected_gst !== undefined && (
            <div>
              <p className="text-[#4a5a7a] uppercase tracking-wider text-[10px] mb-1">
                Expected GST
              </p>
              <span className="text-emerald-400">{v.expected_gst}%</span>
            </div>
          )}
          {v.actual_gst !== undefined && (
            <div>
              <p className="text-[#4a5a7a] uppercase tracking-wider text-[10px] mb-1">
                Actual GST
              </p>
              <span className="text-red-400">{v.actual_gst}%</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Remediation log card ─────────────────────────────────────────────────────

function RemediationCard({ entry }: { entry: RemediationLogEntry }) {
  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-lg border p-3.5",
        entry.status === "AUTO_FIXED"
          ? "border-emerald-500/30 bg-emerald-950/15"
          : "border-red-500/30 bg-red-950/15"
      )}
    >
      <div
        className={cn(
          "mt-0.5 flex-shrink-0 rounded-full p-1.5",
          entry.status === "AUTO_FIXED"
            ? "border border-emerald-500/30 bg-emerald-500/10"
            : "border border-red-500/30 bg-red-500/10"
        )}
      >
        {entry.status === "AUTO_FIXED" ? (
          <Wrench className="h-3.5 w-3.5 text-emerald-400" />
        ) : (
          <AlertTriangle className="h-3.5 w-3.5 text-red-400" />
        )}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2 mb-1">
          <Badge
            variant={entry.status === "AUTO_FIXED" ? "success" : "critical"}
          >
            {entry.status === "AUTO_FIXED" ? "Auto-Fixed" : "Escalated"}
          </Badge>
          <Badge variant="neutral" className="font-mono text-[10px]">
            {entry.rule}
          </Badge>
          <span className="text-xs text-[#4a5a7a]">Risk {entry.risk_score}/10</span>
        </div>
        <p className="text-xs text-[#8b9cc4]">{entry.detail}</p>
      </div>
    </div>
  );
}

// ─── JSON viewer with syntax highlighting ────────────────────────────────────

function JsonViewer({ data }: { data: unknown }) {
  const json = JSON.stringify(data, null, 2);

  // Simple token coloriser for JSON
  const highlighted = json
    .replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, (match) => {
      if (/^"/.test(match)) {
        if (/:$/.test(match)) {
          return `<span class="text-blue-300">${match}</span>`;
        }
        return `<span class="text-amber-300">${match}</span>`;
      }
      if (/true|false/.test(match)) {
        return `<span class="text-purple-400">${match}</span>`;
      }
      if (/null/.test(match)) {
        return `<span class="text-red-400">${match}</span>`;
      }
      return `<span class="text-emerald-400">${match}</span>`;
    });

  return (
    <div className="relative">
      <pre
        className="text-xs leading-relaxed text-[#8b9cc4] whitespace-pre-wrap break-all"
        dangerouslySetInnerHTML={{ __html: highlighted }}
      />
    </div>
  );
}

// ─── Pipeline timing bar ──────────────────────────────────────────────────────

function TimingBar({ timings, total }: { timings: Record<string, number>; total: number }) {
  const colors = ["bg-cyan-500", "bg-amber-500", "bg-purple-500", "bg-emerald-500", "bg-blue-500"];
  const entries = Object.entries(timings);
  return (
    <div className="space-y-2 p-4">
      <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-[#0a0f1e]">
        {entries.map(([key, ms], i) => (
          <div
            key={key}
            className={cn("h-full", colors[i % colors.length])}
            style={{ width: `${(ms / total) * 100}%` }}
          />
        ))}
      </div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {entries.map(([key, ms], i) => (
          <div key={key} className="flex items-center gap-1.5">
            <span className={cn("h-2 w-2 flex-shrink-0 rounded-full", colors[i % colors.length])} />
            <span className="text-xs text-[#8b9cc4] truncate capitalize">
              {key.replace("_ms", "")}
            </span>
            <span className="ml-auto text-xs font-mono text-[#4a5a7a]">{ms}ms</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function ResultsViewer({ data }: ResultsViewerProps) {
  if (!data) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 rounded-xl border border-[#1e2d4a] bg-[#0f1629] py-20 text-center">
        <div className="rounded-full border border-[#1e2d4a] bg-[#0a0f1e] p-4">
          <FileJson2 className="h-8 w-8 text-[#4a5a7a]" />
        </div>
        <div>
          <p className="text-sm font-medium text-[#8b9cc4]">No results yet</p>
          <p className="mt-1 text-xs text-[#4a5a7a]">
            Upload an invoice PDF to see the full audit report
          </p>
        </div>
      </div>
    );
  }

  const { audit_report, compliance, investigations, raw_invoice, stage_timings_ms, pipeline_duration_ms } = data;
  const statusConfig = auditStatusConfig(audit_report.audit_status);

  return (
    <div className="flex flex-col gap-4">
      {/* Status banner */}
      <div
        className={cn(
          "flex items-center justify-between rounded-xl border px-4 py-3",
          statusConfig.bg
        )}
      >
        <div className="flex items-center gap-3">
          <span className={statusConfig.color}>{statusConfig.icon}</span>
          <div>
            <p className={cn("font-semibold", statusConfig.color)}>
              Audit Status: {statusConfig.label}
            </p>
            <p className="text-xs text-[#8b9cc4]">
              {audit_report.vendor_name} · Invoice #{audit_report.invoice_number} · {audit_report.invoice_date}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-[#4a5a7a]">
          <Clock className="h-3.5 w-3.5" />
          {pipeline_duration_ms}ms total
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="violations">
        <TabsList className="w-full justify-start">
          <TabsTrigger value="violations" className="gap-1.5">
            <ShieldAlert className="h-3.5 w-3.5" />
            Violations
            {compliance.violation_count > 0 && (
              <span className="ml-1 rounded-full bg-red-500/20 px-1.5 py-0.5 text-[10px] text-red-400">
                {compliance.violation_count}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="remediation" className="gap-1.5">
            <Wrench className="h-3.5 w-3.5" />
            Remediation
          </TabsTrigger>
          <TabsTrigger value="invoice" className="gap-1.5">
            <ReceiptText className="h-3.5 w-3.5" />
            Invoice
          </TabsTrigger>
          <TabsTrigger value="pipeline" className="gap-1.5">
            <Activity className="h-3.5 w-3.5" />
            Pipeline
          </TabsTrigger>
          <TabsTrigger value="raw" className="gap-1.5">
            <FileJson2 className="h-3.5 w-3.5" />
            Raw JSON
          </TabsTrigger>
        </TabsList>

        {/* ── Violations ── */}
        <TabsContent value="violations">
          <ScrollArea className="max-h-[480px]">
            <div className="flex flex-col gap-3 pr-2">
              {investigations.length === 0 ? (
                <div className="flex items-center gap-3 rounded-xl border border-emerald-500/30 bg-emerald-950/20 px-4 py-5">
                  <ShieldCheck className="h-5 w-5 text-emerald-400 flex-shrink-0" />
                  <div>
                    <p className="text-sm font-medium text-emerald-400">
                      No violations detected
                    </p>
                    <p className="text-xs text-[#8b9cc4] mt-0.5">
                      This invoice passed all compliance checks.
                    </p>
                  </div>
                </div>
              ) : (
                investigations.map((v, i) => (
                  <ViolationCard key={i} v={v} index={i} />
                ))
              )}
            </div>
          </ScrollArea>
        </TabsContent>

        {/* ── Remediation ── */}
        <TabsContent value="remediation">
          <ScrollArea className="max-h-[480px]">
            <div className="flex flex-col gap-3 pr-2">
              {audit_report.remediation_summary.log.length === 0 ? (
                <div className="rounded-xl border border-[#1e2d4a] bg-[#0f1629] px-4 py-8 text-center text-sm text-[#8b9cc4]">
                  No remediation actions taken.
                </div>
              ) : (
                audit_report.remediation_summary.log.map((entry, i) => (
                  <RemediationCard key={i} entry={entry} />
                ))
              )}
            </div>
          </ScrollArea>
        </TabsContent>

        {/* ── Invoice detail ── */}
        <TabsContent value="invoice">
          <ScrollArea className="max-h-[480px]">
            <div className="flex flex-col gap-3 pr-2">
              <Section title="Invoice Details">
                <div className="grid grid-cols-2 gap-px bg-[#1e2d4a]">
                  {[
                    ["Invoice #", raw_invoice.invoice_number],
                    ["Vendor", raw_invoice.vendor_name],
                    ["Date", raw_invoice.invoice_date],
                    ["Category", raw_invoice.category],
                    ["Total Amount", `${raw_invoice.currency} ${raw_invoice.total_amount?.toLocaleString("en-IN")}`],
                    ["GST Total", `${raw_invoice.currency} ${raw_invoice.gst_total?.toLocaleString("en-IN")}`],
                  ].map(([label, value]) => (
                    <div key={label} className="bg-[#0f1629] px-4 py-3">
                      <p className="text-[10px] uppercase tracking-widest text-[#4a5a7a]">{label}</p>
                      <p className="mt-0.5 text-sm text-[#e8edf8]">{value ?? "—"}</p>
                    </div>
                  ))}
                </div>
              </Section>

              <Section title="Line Items" badge={
                <Badge variant="neutral">{raw_invoice.line_items?.length ?? 0}</Badge>
              }>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-[#1e2d4a] bg-[#0a0f1e]">
                        {["Description", "Qty", "Unit Price", "GST %", "Amount"].map((h) => (
                          <th key={h} className="px-4 py-2 text-left font-medium text-[#4a5a7a] uppercase tracking-wider">
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {(raw_invoice.line_items ?? []).map((item, i) => (
                        <tr key={i} className="border-b border-[#1e2d4a] hover:bg-[#151d35]">
                          <td className="px-4 py-2.5 text-[#e8edf8]">{item.description}</td>
                          <td className="px-4 py-2.5 text-[#8b9cc4]">{item.quantity}</td>
                          <td className="px-4 py-2.5 text-[#8b9cc4]">
                            ₹{item.unit_price?.toLocaleString("en-IN")}
                          </td>
                          <td className={cn("px-4 py-2.5 font-mono",
                            item.gst_rate === 18 ? "text-emerald-400" : "text-red-400"
                          )}>
                            {item.gst_rate}%
                          </td>
                          <td className="px-4 py-2.5 text-[#e8edf8] font-medium">
                            ₹{item.amount?.toLocaleString("en-IN")}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Section>
            </div>
          </ScrollArea>
        </TabsContent>

        {/* ── Pipeline timing ── */}
        <TabsContent value="pipeline">
          <div className="rounded-xl border border-[#1e2d4a] bg-[#0f1629]">
            <div className="border-b border-[#1e2d4a] px-4 py-3">
              <p className="text-sm font-semibold text-[#e8edf8]">
                Stage Execution Times
              </p>
              <p className="text-xs text-[#4a5a7a] mt-0.5">
                Total pipeline: {pipeline_duration_ms}ms
              </p>
            </div>
            <TimingBar timings={stage_timings_ms} total={pipeline_duration_ms} />
          </div>
        </TabsContent>

        {/* ── Raw JSON ── */}
        <TabsContent value="raw">
          <div className="rounded-xl border border-[#1e2d4a] bg-[#0a0f1e] overflow-hidden">
            <div className="flex items-center justify-between border-b border-[#1e2d4a] px-4 py-2.5">
              <span className="text-xs font-medium text-[#8b9cc4]">
                audit_response.json
              </span>
              <CopyButton text={JSON.stringify(data, null, 2)} />
            </div>
            <ScrollArea className="max-h-[420px]">
              <div className="p-4">
                <JsonViewer data={data} />
              </div>
            </ScrollArea>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
