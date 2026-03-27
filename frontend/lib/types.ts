// ─── Invoice & Pipeline Types ────────────────────────────────────────────────

export interface LineItem {
  description: string;
  quantity: number;
  unit_price: number;
  gst_rate: number;
  amount: number;
}

export interface Invoice {
  invoice_number: string;
  vendor_name: string;
  invoice_date: string;
  total_amount: number;
  currency: string;
  line_items: LineItem[];
  gst_total: number;
  category: string;
}

export interface Violation {
  rule: string;
  line_item_index: number | null;
  description: string;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  message: string;
  // Investigator fields
  cause?: string;
  confidence?: number;
  risk_score?: number;
  action?: string;
  // Extra rule-specific fields
  expected_gst?: number;
  actual_gst?: number;
  limit?: number;
  actual_amount?: number;
  excess_amount?: number;
}

export interface ComplianceResult {
  is_compliant: boolean;
  violation_count: number;
  violations: Violation[];
}

export interface RemediationLogEntry {
  rule: string;
  risk_score: number;
  line_item_index: number | null;
  status: "AUTO_FIXED" | "ESCALATED";
  detail: string;
}

export interface AuditMetrics {
  total_processed: number;
  total_violations: number;
  fixed_count: number;
  escalated_count: number;
  fix_rate: number;
}

export interface AuditReport {
  audit_status: "CLEAN" | "FIXED" | "PARTIALLY_FIXED" | "ESCALATED";
  invoice_number: string;
  vendor_name: string;
  invoice_date: string;
  total_amount: number;
  currency: string;
  metrics: AuditMetrics;
  compliance_summary: {
    is_compliant: boolean;
    severity_levels_found: string[];
  };
  remediation_summary: {
    log: RemediationLogEntry[];
    updated_invoice: Invoice;
  };
}

export interface AuditResponse {
  status: "success" | "error";
  filename: string;
  pipeline_duration_ms: number;
  stage_timings_ms: Record<string, number>;
  audit_report: AuditReport;
  raw_invoice: Invoice;
  compliance: ComplianceResult;
  investigations: Violation[];
}

// ─── Agent Log ───────────────────────────────────────────────────────────────

export type AgentName =
  | "Intake"
  | "Compliance"
  | "Investigator"
  | "Remediator"
  | "Auditor"
  | "System";

export type LogLevel = "info" | "success" | "warning" | "error";

export interface AgentLogEntry {
  id: string;
  agent: AgentName;
  level: LogLevel;
  message: string;
  timestamp: string;
}
