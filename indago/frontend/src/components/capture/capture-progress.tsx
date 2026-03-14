"use client";

import { useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Shield, CheckCircle, XCircle, Clock, Globe,
  Camera, Download, Hash, FileText, Lock, Loader2,
  AlertTriangle, ExternalLink
} from "lucide-react";
import { clsx } from "clsx";
import { capturesApi, type Capture } from "@/lib/api";
import { format } from "date-fns";
import Link from "next/link";

const STEPS = [
  { key: "dns", label: "DNS Resolution", icon: Globe, events: ["dns_lookup", "dns_result"] },
  { key: "tls", label: "TLS Certificate", icon: Shield, events: ["tls_handshake", "tls_certificate"] },
  { key: "navigate", label: "Page Navigation", icon: Globe, events: ["page_navigate", "page_load_complete"] },
  { key: "screenshot", label: "Screenshots", icon: Camera, events: ["screenshot_taken"] },
  { key: "resources", label: "Resource Download", icon: Download, events: ["resource_download"] },
  { key: "hash", label: "Hash Calculation", icon: Hash, events: ["hash_calculated", "hash_manifest_created"] },
  { key: "timestamp", label: "RFC 3161 Timestamp", icon: Clock, events: ["timestamp_received"] },
  { key: "report", label: "Evidence Package", icon: FileText, events: ["evidence_pack_created"] },
  { key: "lock", label: "Evidence Locked", icon: Lock, events: ["evidence_locked"] },
];

interface Props {
  captureId: number;
}

export function CaptureProgress({ captureId }: Props) {
  const queryClient = useQueryClient();

  const { data: capture } = useQuery({
    queryKey: ["capture", captureId],
    queryFn: () => capturesApi.getStatus(captureId).then((r) => r.data as Capture),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "running" || status === "pending") return 2000;
      return false;
    },
  });

  const { data: logs } = useQuery({
    queryKey: ["capture-logs", captureId],
    queryFn: () => capturesApi.getLogs(captureId).then((r) => r.data),
    refetchInterval: capture?.status === "running" ? 3000 : false,
    enabled: !!capture,
  });

  const completedEvents = new Set((logs || []).filter((l: any) => l.success).map((l: any) => l.event_type));

  const getStepStatus = (step: typeof STEPS[0]) => {
    if (capture?.status === "completed") return "done";
    if (step.events.some((e) => completedEvents.has(e))) return "done";
    if (capture?.status === "running" && STEPS.indexOf(step) === getCurrentStepIndex()) return "active";
    return "pending";
  };

  const getCurrentStepIndex = () => {
    if (!capture || capture.status !== "running") return -1;
    for (let i = STEPS.length - 1; i >= 0; i--) {
      if (STEPS[i].events.some((e) => completedEvents.has(e))) return Math.min(i + 1, STEPS.length - 1);
    }
    return 0;
  };

  const statusConfig = {
    pending: { label: "Queued", color: "text-amber-400", bg: "bg-amber-500/10 border-amber-500/20" },
    running: { label: "Capturing", color: "text-blue-400", bg: "bg-blue-500/10 border-blue-500/20" },
    completed: { label: "Complete", color: "text-green-400", bg: "bg-green-500/10 border-green-500/20" },
    failed: { label: "Failed", color: "text-red-400", bg: "bg-red-500/10 border-red-500/20" },
    cancelled: { label: "Cancelled", color: "text-slate-400", bg: "bg-slate-500/10 border-slate-500/20" },
  };

  if (!capture) {
    return (
      <div className="flex items-center justify-center h-48">
        <Loader2 className="w-6 h-6 text-blue-400 animate-spin" />
      </div>
    );
  }

  const config = statusConfig[capture.status] || statusConfig.pending;

  return (
    <div className="space-y-6">
      {/* Status Header */}
      <div className={clsx("flex items-center justify-between p-4 rounded-lg border", config.bg)}>
        <div className="flex items-center gap-3">
          {capture.status === "running" && (
            <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
          )}
          {capture.status === "completed" && (
            <CheckCircle className="w-5 h-5 text-green-400" />
          )}
          {capture.status === "failed" && (
            <XCircle className="w-5 h-5 text-red-400" />
          )}
          {capture.status === "pending" && (
            <Clock className="w-5 h-5 text-amber-400" />
          )}
          <div>
            <p className={clsx("font-semibold", config.color)}>{config.label}</p>
            <p className="text-xs text-slate-500 mt-0.5 font-mono truncate max-w-xs">
              {capture.url}
            </p>
          </div>
        </div>
        <span className={clsx("text-sm font-bold", config.color)}>
          {Math.round(capture.progress)}%
        </span>
      </div>

      {/* Progress bar */}
      {(capture.status === "running" || capture.status === "completed") && (
        <div className="h-1.5 bg-[#0a0e1a] rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-blue-600 to-blue-400 rounded-full transition-all duration-500"
            style={{ width: `${capture.status === "completed" ? 100 : capture.progress}%` }}
          />
        </div>
      )}

      {/* Capture Steps */}
      <div className="space-y-2">
        {STEPS.map((step, index) => {
          const status = getStepStatus(step);
          return (
            <div
              key={step.key}
              className={clsx(
                "flex items-center gap-3 p-3 rounded-lg border transition-all",
                status === "done" && "bg-green-500/5 border-green-500/20",
                status === "active" && "bg-blue-500/10 border-blue-500/30",
                status === "pending" && "bg-transparent border-[#1e3a5f]/50"
              )}
            >
              <div className={clsx(
                "w-8 h-8 rounded-full flex items-center justify-center border flex-shrink-0",
                status === "done" && "bg-green-500/10 border-green-500/30",
                status === "active" && "bg-blue-500/20 border-blue-500/40",
                status === "pending" && "bg-[#0a0e1a] border-[#1e3a5f]"
              )}>
                {status === "done" ? (
                  <CheckCircle className="w-4 h-4 text-green-400" />
                ) : status === "active" ? (
                  <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
                ) : (
                  <step.icon className="w-4 h-4 text-slate-600" />
                )}
              </div>
              <span className={clsx(
                "text-sm font-medium",
                status === "done" && "text-green-300",
                status === "active" && "text-blue-300",
                status === "pending" && "text-slate-600"
              )}>
                {step.label}
              </span>
              {status === "done" && (
                <CheckCircle className="w-3.5 h-3.5 text-green-400 ml-auto" />
              )}
            </div>
          );
        })}
      </div>

      {/* Error */}
      {capture.status === "failed" && capture.error_message && (
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20">
          <div className="flex items-center gap-2 mb-1">
            <AlertTriangle className="w-4 h-4 text-red-400" />
            <span className="text-sm font-medium text-red-400">Capture Failed</span>
          </div>
          <p className="text-xs text-slate-400 font-mono">{capture.error_message}</p>
        </div>
      )}

      {/* Completed - Evidence Info */}
      {capture.status === "completed" && (
        <div className="p-4 rounded-lg bg-[#0a0e1a] border border-[#1e3a5f] space-y-3">
          <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
            <Shield className="w-4 h-4 text-blue-400" />
            Evidence Package Ready
          </h3>

          {capture.package_sha256 && (
            <div>
              <p className="text-xs text-slate-500 mb-1">Package Integrity (SHA-256)</p>
              <p className="hash-text break-all">{capture.package_sha256}</p>
            </div>
          )}

          <div className="grid grid-cols-3 gap-3 text-center">
            <div className="p-2 rounded bg-[#0d1526] border border-[#1e3a5f]">
              <p className="text-lg font-bold text-blue-400">{capture.screenshot_count}</p>
              <p className="text-xs text-slate-500">Screenshots</p>
            </div>
            <div className="p-2 rounded bg-[#0d1526] border border-[#1e3a5f]">
              <p className="text-lg font-bold text-blue-400">{capture.total_resources}</p>
              <p className="text-xs text-slate-500">Resources</p>
            </div>
            <div className="p-2 rounded bg-[#0d1526] border border-[#1e3a5f]">
              <p className="text-lg font-bold text-green-400">{capture.tsa_timestamp ? "YES" : "NO"}</p>
              <p className="text-xs text-slate-500">Timestamped</p>
            </div>
          </div>

          <div className="flex gap-2">
            <Link
              href={`/captures/${captureId}`}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition-colors"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              View Evidence
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
