"use client";

import React, { useCallback, useRef, useState } from "react";
import {
  CloudUpload,
  FileText,
  X,
  CheckCircle2,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import type { AuditResponse, AgentLogEntry } from "@/lib/types";

interface FileUploadProps {
  onUploadStart: () => void;
  onLogEntry: (entry: Omit<AgentLogEntry, "id">) => void;
  onResult: (data: AuditResponse) => void;
  onError: (msg: string) => void;
  isLoading: boolean;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Simulated agent log sequence played while awaiting the real API response
const PIPELINE_STAGES: Array<Omit<AgentLogEntry, "id">> = [
  { agent: "System",      level: "info",    message: "Pipeline initialised. Dispatching agents…",             timestamp: "" },
  { agent: "Intake",      level: "info",    message: "Extracting text from PDF document…",                    timestamp: "" },
  { agent: "Intake",      level: "info",    message: "Sending extracted content to LLM for structured parsing…", timestamp: "" },
  { agent: "Intake",      level: "success", message: "Invoice data extracted successfully.",                   timestamp: "" },
  { agent: "Compliance",  level: "info",    message: "Running GST rate compliance check…",                    timestamp: "" },
  { agent: "Compliance",  level: "info",    message: "Checking invoice total against ₹3,00,000 limit…",       timestamp: "" },
  { agent: "Compliance",  level: "warning", message: "Compliance scan complete — reviewing findings…",        timestamp: "" },
  { agent: "Investigator",level: "info",    message: "Analysing violations with LLM investigator…",           timestamp: "" },
  { agent: "Investigator",level: "info",    message: "Calculating risk scores and confidence levels…",        timestamp: "" },
  { agent: "Remediator",  level: "info",    message: "Applying auto-remediation for low-risk violations…",    timestamp: "" },
  { agent: "Remediator",  level: "success", message: "Remediation complete.",                                 timestamp: "" },
  { agent: "Auditor",     level: "info",    message: "Compiling final audit report…",                        timestamp: "" },
  { agent: "Auditor",     level: "success", message: "Audit pipeline finished.",                              timestamp: "" },
];

export default function FileUpload({
  onUploadStart,
  onLogEntry,
  onResult,
  onError,
  isLoading,
}: FileUploadProps) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadDone, setUploadDone] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const stageTimerRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  const clearStageTimers = () => {
    stageTimerRef.current.forEach(clearTimeout);
    stageTimerRef.current = [];
  };

  const playPipelineLogs = () => {
    clearStageTimers();
    PIPELINE_STAGES.forEach((stage, i) => {
      const t = setTimeout(
        () => onLogEntry({ ...stage, timestamp: new Date().toISOString() }),
        i * 700
      );
      stageTimerRef.current.push(t);
    });
  };

  const handleFile = (file: File) => {
    if (file.type !== "application/pdf") {
      onError("Only PDF files are accepted.");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      onError("File exceeds the 10 MB limit.");
      return;
    }
    setSelectedFile(file);
    setUploadDone(false);
  };

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragActive(true);
  };

  const handleDragLeave = () => setDragActive(false);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  const handleUpload = async () => {
    if (!selectedFile || isLoading) return;

    setUploadDone(false);
    onUploadStart();
    playPipelineLogs();

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const res = await fetch(`${API_URL}/upload`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail ?? "Upload failed");
      }

      const data: AuditResponse = await res.json();
      setUploadDone(true);
      onResult(data);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "An unexpected error occurred.";
      onError(msg);
      onLogEntry({
        agent: "System",
        level: "error",
        message: `Pipeline failed: ${msg}`,
        timestamp: new Date().toISOString(),
      });
    } finally {
      clearStageTimers();
    }
  };

  const removeFile = () => {
    setSelectedFile(null);
    setUploadDone(false);
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Drop zone */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => !selectedFile && inputRef.current?.click()}
        className={cn(
          "relative flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-8 transition-all duration-200 cursor-pointer",
          dragActive
            ? "border-blue-500 bg-blue-500/10 scale-[1.01]"
            : selectedFile
            ? "border-[#1e2d4a] bg-[#0f1629] cursor-default"
            : "border-[#1e2d4a] bg-[#0f1629] hover:border-blue-600/60 hover:bg-blue-950/20"
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,application/pdf"
          className="hidden"
          onChange={handleInputChange}
          disabled={isLoading}
        />

        {!selectedFile ? (
          <>
            {/* Upload icon with glow */}
            <div className="relative">
              <div className="absolute inset-0 rounded-full bg-blue-500/20 blur-xl" />
              <div className="relative rounded-full border border-blue-600/30 bg-blue-600/10 p-4">
                <CloudUpload className="h-8 w-8 text-blue-400" />
              </div>
            </div>
            <div className="text-center">
              <p className="font-medium text-[#e8edf8]">
                Drag & drop invoice PDF
              </p>
              <p className="mt-1 text-sm text-[#8b9cc4]">
                or{" "}
                <span className="text-blue-400 hover:text-blue-300 transition-colors">
                  browse files
                </span>{" "}
                · Max 10 MB
              </p>
            </div>
          </>
        ) : (
          /* File selected state */
          <div className="flex w-full items-center gap-3 px-2">
            <div className="flex-shrink-0 rounded-lg border border-blue-600/30 bg-blue-600/10 p-2.5">
              <FileText className="h-5 w-5 text-blue-400" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-[#e8edf8]">
                {selectedFile.name}
              </p>
              <p className="text-xs text-[#8b9cc4]">
                {(selectedFile.size / 1024).toFixed(1)} KB ·{" "}
                {uploadDone ? (
                  <span className="text-emerald-400">Upload complete</span>
                ) : (
                  <span className="text-blue-400">Ready to upload</span>
                )}
              </p>
            </div>
            {!isLoading && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  removeFile();
                }}
                className="flex-shrink-0 rounded-lg p-1.5 text-[#4a5a7a] hover:bg-[#1a2340] hover:text-[#e8edf8] transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
        )}

        {/* Drag overlay label */}
        {dragActive && (
          <div className="absolute inset-0 flex items-center justify-center rounded-xl bg-blue-500/10">
            <p className="text-lg font-semibold text-blue-300">
              Release to upload
            </p>
          </div>
        )}
      </div>

      {/* Action button */}
      <Button
        onClick={handleUpload}
        disabled={!selectedFile || isLoading}
        className="w-full h-10 font-semibold text-sm"
        size="lg"
      >
        {isLoading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Running audit pipeline…
          </>
        ) : uploadDone ? (
          <>
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
            Audit complete — re-run?
          </>
        ) : (
          <>
            <CloudUpload className="h-4 w-4" />
            Run AutoAudit
          </>
        )}
      </Button>

      {/* Hint text */}
      {!selectedFile && (
        <div className="flex items-start gap-2 rounded-lg border border-[#1e2d4a] bg-[#0a0f1e] px-3 py-2.5">
          <AlertCircle className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-[#4a5a7a]" />
          <p className="text-xs text-[#4a5a7a]">
            Upload a real invoice PDF. The pipeline extracts data, checks
            compliance, investigates violations, and auto-remediates where safe.
          </p>
        </div>
      )}
    </div>
  );
}
