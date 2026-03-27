"use client";

import React from "react";
import {
  FileCheck2,
  ShieldAlert,
  Wrench,
  IndianRupee,
  TrendingUp,
  TrendingDown,
  Minus,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { AuditReport } from "@/lib/types";

interface MetricsCardsProps {
  report: AuditReport | null;
  isLoading: boolean;
}

interface MetricCardConfig {
  label: string;
  value: string;
  subtext: string;
  icon: React.ReactNode;
  trend?: "up" | "down" | "neutral";
  trendLabel?: string;
  accentColor: string;
  borderColor: string;
  bgColor: string;
  iconBg: string;
}

// ─── Skeleton shimmer card ────────────────────────────────────────────────────

function SkeletonCard() {
  return (
    <div className="rounded-xl border border-[#1e2d4a] bg-[#0f1629] p-5 animate-pulse">
      <div className="flex items-start justify-between">
        <div>
          <div className="h-3 w-24 rounded bg-[#1a2340] mb-2" />
          <div className="h-8 w-16 rounded bg-[#1a2340] mt-3" />
        </div>
        <div className="h-10 w-10 rounded-lg bg-[#1a2340]" />
      </div>
      <div className="mt-4 h-2 w-32 rounded bg-[#1a2340]" />
    </div>
  );
}

// ─── Single metric card ───────────────────────────────────────────────────────

function MetricCard({
  label,
  value,
  subtext,
  icon,
  trend,
  trendLabel,
  accentColor,
  borderColor,
  bgColor,
  iconBg,
}: MetricCardConfig) {
  const TrendIcon =
    trend === "up"
      ? TrendingUp
      : trend === "down"
      ? TrendingDown
      : Minus;

  const trendColor =
    trend === "up"
      ? "text-emerald-400"
      : trend === "down"
      ? "text-red-400"
      : "text-[#8b9cc4]";

  return (
    <div
      className={cn(
        "card-hover relative overflow-hidden rounded-xl border p-5 transition-all",
        borderColor,
        bgColor
      )}
    >
      {/* Subtle top gradient strip */}
      <div
        className={cn(
          "absolute left-0 right-0 top-0 h-[2px]",
          accentColor
        )}
      />

      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-widest text-[#4a5a7a]">
            {label}
          </p>
          <p className="mt-2 text-3xl font-bold tracking-tight text-[#e8edf8] count-up">
            {value}
          </p>
        </div>
        <div className={cn("rounded-xl p-2.5", iconBg)}>
          {icon}
        </div>
      </div>

      <div className="mt-3 flex items-center gap-1.5">
        <TrendIcon className={cn("h-3.5 w-3.5", trendColor)} />
        <span className="text-xs text-[#8b9cc4]">{subtext}</span>
        {trendLabel && (
          <span className={cn("ml-auto text-xs font-medium", trendColor)}>
            {trendLabel}
          </span>
        )}
      </div>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function MetricsCards({ report, isLoading }: MetricsCardsProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[...Array(4)].map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  const metrics = report?.metrics;
  const fixRate = metrics
    ? `${(metrics.fix_rate * 100).toFixed(0)}%`
    : "—";

  // Estimate amount saved: violations fixed × ₹15,000 notional value
  const amountSaved =
    metrics && metrics.fixed_count > 0
      ? `₹${(metrics.fixed_count * 15000).toLocaleString("en-IN")}`
      : "₹0";

  const cards: MetricCardConfig[] = [
    {
      label: "Invoices Processed",
      value: metrics ? String(metrics.total_processed) : "—",
      subtext: report
        ? `Status: ${report.audit_status}`
        : "No data yet",
      icon: <FileCheck2 className="h-5 w-5 text-blue-400" />,
      trend: "neutral",
      accentColor: "bg-gradient-to-r from-blue-600 to-cyan-500",
      borderColor: "border-blue-900/40",
      bgColor: "bg-[#0d1527]",
      iconBg: "bg-blue-600/15 border border-blue-600/20",
    },
    {
      label: "Violations Found",
      value: metrics ? String(metrics.total_violations) : "—",
      subtext:
        metrics?.total_violations === 0
          ? "Invoice is fully compliant"
          : `${metrics?.escalated_count ?? 0} escalated for review`,
      icon: <ShieldAlert className="h-5 w-5 text-red-400" />,
      trend:
        !metrics
          ? "neutral"
          : metrics.total_violations === 0
          ? "up"
          : "down",
      trendLabel: metrics?.total_violations === 0 ? "Clean" : undefined,
      accentColor: "bg-gradient-to-r from-red-600 to-orange-500",
      borderColor:
        metrics && metrics.total_violations > 0
          ? "border-red-900/40"
          : "border-[#1e2d4a]",
      bgColor:
        metrics && metrics.total_violations > 0
          ? "bg-red-950/20"
          : "bg-[#0f1629]",
      iconBg: "bg-red-600/15 border border-red-600/20",
    },
    {
      label: "Auto-Fixed",
      value: metrics ? String(metrics.fixed_count) : "—",
      subtext: `Fix rate: ${fixRate}`,
      icon: <Wrench className="h-5 w-5 text-emerald-400" />,
      trend:
        !metrics
          ? "neutral"
          : metrics.fixed_count > 0
          ? "up"
          : "neutral",
      trendLabel: metrics && metrics.fixed_count > 0 ? fixRate : undefined,
      accentColor: "bg-gradient-to-r from-emerald-600 to-teal-500",
      borderColor:
        metrics && metrics.fixed_count > 0
          ? "border-emerald-900/40"
          : "border-[#1e2d4a]",
      bgColor:
        metrics && metrics.fixed_count > 0
          ? "bg-emerald-950/20"
          : "bg-[#0f1629]",
      iconBg: "bg-emerald-600/15 border border-emerald-600/20",
    },
    {
      label: "Amount Saved",
      value: amountSaved,
      subtext:
        metrics && metrics.fixed_count > 0
          ? `${metrics.fixed_count} correction${metrics.fixed_count > 1 ? "s" : ""} applied`
          : "No corrections applied",
      icon: <IndianRupee className="h-5 w-5 text-amber-400" />,
      trend:
        metrics && metrics.fixed_count > 0 ? "up" : "neutral",
      accentColor: "bg-gradient-to-r from-amber-500 to-yellow-400",
      borderColor:
        metrics && metrics.fixed_count > 0
          ? "border-amber-900/40"
          : "border-[#1e2d4a]",
      bgColor:
        metrics && metrics.fixed_count > 0
          ? "bg-amber-950/20"
          : "bg-[#0f1629]",
      iconBg: "bg-amber-600/15 border border-amber-600/20",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {cards.map((card) => (
        <MetricCard key={card.label} {...card} />
      ))}
    </div>
  );
}
