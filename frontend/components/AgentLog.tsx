"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  Terminal,
  Wifi,
  WifiOff,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Info,
  Bot,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import type { AgentLogEntry, AgentName, LogLevel } from "@/lib/types";

interface AgentLogProps {
  entries: AgentLogEntry[];
  isLoading: boolean;
  onClear: () => void;
}

// ─── Visual config per agent ─────────────────────────────────────────────────

const AGENT_COLORS: Record<AgentName, string> = {
  System:       "text-[#8b9cc4]",
  Intake:       "text-cyan-400",
  Compliance:   "text-amber-400",
  Investigator: "text-purple-400",
  Remediator:   "text-emerald-400",
  Auditor:      "text-blue-400",
};

const AGENT_BG: Record<AgentName, string> = {
  System:       "bg-[#1a2340]",
  Intake:       "bg-cyan-500/10",
  Compliance:   "bg-amber-500/10",
  Investigator: "bg-purple-500/10",
  Remediator:   "bg-emerald-500/10",
  Auditor:      "bg-blue-500/10",
};

const LEVEL_ICON: Record<LogLevel, React.ReactNode> = {
  info:    <Info className="h-3 w-3 text-[#8b9cc4]" />,
  success: <CheckCircle2 className="h-3 w-3 text-emerald-400" />,
  warning: <AlertTriangle className="h-3 w-3 text-amber-400" />,
  error:   <XCircle className="h-3 w-3 text-red-400" />,
};

const LEVEL_ROW: Record<LogLevel, string> = {
  info:    "",
  success: "bg-emerald-500/5",
  warning: "bg-amber-500/5",
  error:   "bg-red-500/10 border-l-2 border-red-500/50",
};

// ─── WebSocket connection status ─────────────────────────────────────────────

type WsStatus = "connecting" | "connected" | "disconnected";

function useWebSocket(url: string, onMessage: (msg: string) => void) {
  const [status, setStatus] = useState<WsStatus>("disconnected");
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    setStatus("connecting");
    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => setStatus("connected");
      ws.onmessage = (e) => onMessage(e.data as string);
      ws.onerror = () => setStatus("disconnected");
      ws.onclose = () => setStatus("disconnected");

      return () => {
        ws.close();
        wsRef.current = null;
      };
    } catch {
      // WebSocket not available in this environment (e.g. backend not running)
      setStatus("disconnected");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url]);

  return status;
}

// ─── Component ───────────────────────────────────────────────────────────────

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws";

export default function AgentLog({ entries, isLoading, onClear }: AgentLogProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const wsStatus = useWebSocket(WS_URL, () => {
    // Real WebSocket messages from backend would be processed here
  });

  // Auto-scroll to bottom on new entries
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries]);

  const formatTime = (iso: string) => {
    try {
      return new Date(iso).toLocaleTimeString("en-IN", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
      });
    } catch {
      return "--:--:--";
    }
  };

  return (
    <div className="flex h-full flex-col rounded-xl border border-[#1e2d4a] bg-[#0f1629] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#1e2d4a] px-4 py-3">
        <div className="flex items-center gap-2.5">
          <div className="rounded-lg border border-[#1e2d4a] bg-[#0a0f1e] p-1.5">
            <Terminal className="h-4 w-4 text-blue-400" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-[#e8edf8]">Agent Activity</h3>
            <p className="text-xs text-[#4a5a7a]">Real-time pipeline log</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* WebSocket status pill */}
          <div
            className={cn(
              "flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium border",
              wsStatus === "connected"
                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                : wsStatus === "connecting"
                ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
                : "bg-[#0a0f1e] text-[#4a5a7a] border-[#1e2d4a]"
            )}
          >
            {wsStatus === "connected" ? (
              <Wifi className="h-3 w-3" />
            ) : (
              <WifiOff className="h-3 w-3" />
            )}
            {wsStatus === "connected"
              ? "WS Live"
              : wsStatus === "connecting"
              ? "Connecting…"
              : "WS Offline"}
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={onClear}
            disabled={entries.length === 0}
            className="h-7 px-2 text-xs"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {/* Log body */}
      <ScrollArea className="flex-1">
        <div className="p-3 font-mono text-xs">
          {entries.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-3 py-12 text-center">
              <div className="rounded-full border border-[#1e2d4a] bg-[#0a0f1e] p-3">
                <Bot className="h-6 w-6 text-[#4a5a7a]" />
              </div>
              <p className="text-[#4a5a7a]">
                Upload an invoice to start the pipeline
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-0.5">
              {entries.map((entry) => (
                <div
                  key={entry.id}
                  className={cn(
                    "fade-in-up flex items-start gap-2 rounded-md px-2 py-1.5",
                    LEVEL_ROW[entry.level]
                  )}
                >
                  {/* Timestamp */}
                  <span className="flex-shrink-0 text-[#4a5a7a] w-[64px]">
                    {formatTime(entry.timestamp)}
                  </span>

                  {/* Level icon */}
                  <span className="mt-0.5 flex-shrink-0">
                    {LEVEL_ICON[entry.level]}
                  </span>

                  {/* Agent badge */}
                  <span
                    className={cn(
                      "flex-shrink-0 rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider",
                      AGENT_COLORS[entry.agent],
                      AGENT_BG[entry.agent]
                    )}
                  >
                    {entry.agent}
                  </span>

                  {/* Message */}
                  <span className="text-[#8b9cc4] leading-relaxed">
                    {entry.message}
                  </span>
                </div>
              ))}

              {/* Blinking cursor when loading */}
              {isLoading && (
                <div className="flex items-center gap-2 px-2 py-1.5">
                  <span className="w-[64px] text-[#4a5a7a]">
                    {new Date().toLocaleTimeString("en-IN", {
                      hour: "2-digit",
                      minute: "2-digit",
                      second: "2-digit",
                      hour12: false,
                    })}
                  </span>
                  <span className="flex items-center gap-1 text-blue-400">
                    <span
                      className="inline-block h-2 w-1.5 rounded-sm bg-blue-400"
                      style={{ animation: "pulse-dot 1s ease-in-out infinite" }}
                    />
                    <span
                      className="inline-block h-2 w-1.5 rounded-sm bg-blue-400"
                      style={{
                        animation: "pulse-dot 1s ease-in-out 0.2s infinite",
                      }}
                    />
                    <span
                      className="inline-block h-2 w-1.5 rounded-sm bg-blue-400"
                      style={{
                        animation: "pulse-dot 1s ease-in-out 0.4s infinite",
                      }}
                    />
                  </span>
                  <span className="text-[#4a5a7a]">Processing…</span>
                </div>
              )}
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      {/* Footer stats */}
      <div className="flex items-center justify-between border-t border-[#1e2d4a] px-4 py-2">
        <span className="text-xs text-[#4a5a7a]">
          {entries.length} log {entries.length === 1 ? "entry" : "entries"}
        </span>
        <div className="flex gap-3">
          {(["info", "success", "warning", "error"] as LogLevel[]).map((lvl) => {
            const count = entries.filter((e) => e.level === lvl).length;
            if (count === 0) return null;
            return (
              <span
                key={lvl}
                className={cn("flex items-center gap-1 text-xs", {
                  "text-[#8b9cc4]": lvl === "info",
                  "text-emerald-400": lvl === "success",
                  "text-amber-400": lvl === "warning",
                  "text-red-400": lvl === "error",
                })}
              >
                {LEVEL_ICON[lvl]}
                {count}
              </span>
            );
          })}
        </div>
      </div>
    </div>
  );
}
