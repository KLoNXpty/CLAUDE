"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import {
  Shield, Globe, Hash, Clock, Download, FileText, Lock,
  CheckCircle, XCircle, Server, Eye, AlertTriangle, Copy,
  RefreshCw, ChevronRight, Camera, Database, List
} from "lucide-react";
import { capturesApi, type Capture } from "@/lib/api";
import { format } from "date-fns";
import { clsx } from "clsx";
import { CaptureProgress } from "@/components/capture/capture-progress";
import { useState } from "react";

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button onClick={copy} className="text-slate-500 hover:text-blue-400 transition-colors">
      {copied ? <CheckCircle className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
    </button>
  );
}

function Section({ title, icon: Icon, children }: { title: string; icon: any; children: React.ReactNode }) {
  return (
    <div className="forensic-card">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-[#1e3a5f]">
        <Icon className="w-4 h-4 text-blue-400" />
        <h3 className="text-sm font-semibold text-slate-200">{title}</h3>
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

function DataRow({ label, value, mono = false }: { label: string; value: string | null | undefined; mono?: boolean }) {
  if (!value) return null;
  return (
    <div className="flex items-start gap-4 py-2 border-b border-[#1e3a5f]/50 last:border-0">
      <span className="text-xs text-slate-500 w-36 flex-shrink-0 pt-0.5">{label}</span>
      <div className="flex items-center gap-2 flex-1 min-w-0">
        <span className={clsx("text-xs text-slate-300 break-all", mono && "font-mono text-[#00a8ff]")}>
          {value}
        </span>
        {mono && <CopyButton text={value} />}
      </div>
    </div>
  );
}

export default function CaptureDetailPage() {
  const { id } = useParams<{ id: string }>();
  const captureId = parseInt(id);
  const [activeTab, setActiveTab] = useState<"overview" | "hashes" | "logs" | "metadata" | "social">("overview");

  const { data: capture, isLoading } = useQuery({
    queryKey: ["capture", captureId],
    queryFn: () => capturesApi.get(captureId).then((r) => r.data as Capture),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "running" || status === "pending" ? 3000 : false;
    },
  });

  const { data: hashes } = useQuery({
    queryKey: ["capture-hashes", captureId],
    queryFn: () => capturesApi.getHashes(captureId).then((r) => r.data),
    enabled: capture?.status === "completed",
  });

  const { data: logs } = useQuery({
    queryKey: ["capture-logs", captureId],
    queryFn: () => capturesApi.getLogs(captureId).then((r) => r.data),
    enabled: !!capture,
  });

  const { data: metadata } = useQuery({
    queryKey: ["capture-metadata", captureId],
    queryFn: () => capturesApi.getMetadata(captureId).then((r) => r.data),
    enabled: capture?.status === "completed",
  });

  const { data: social } = useQuery({
    queryKey: ["capture-social", captureId],
    queryFn: () => capturesApi.getSocial(captureId).then((r) => r.data),
    enabled: capture?.status === "completed",
  });

  const reportMutation = useMutation({
    mutationFn: () => capturesApi.generateReport(captureId),
  });

  const downloadMutation = useMutation({
    mutationFn: async () => {
      const response = await capturesApi.download(captureId);
      const url = URL.createObjectURL(response.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `evidence_${capture?.evidence_id?.slice(0, 8)}.zip`;
      a.click();
      URL.revokeObjectURL(url);
    },
  });

  const verifyMutation = useMutation({
    mutationFn: () => capturesApi.verify(captureId),
  });

  if (isLoading || !capture) {
    return (
      <div className="flex items-center justify-center h-48">
        <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const tabs = [
    { key: "overview", label: "Overview", icon: Eye },
    { key: "hashes", label: "Hashes", icon: Hash },
    { key: "logs", label: "Forensic Log", icon: List },
    { key: "metadata", label: "Metadata", icon: Database },
    ...(social && social.platform ? [{ key: "social", label: "Social Data", icon: Globe }] : []),
  ] as const;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-xl font-bold text-slate-100">Evidence Detail</h1>
            {capture.is_locked && (
              <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-green-500/10 text-green-400 border border-green-500/20">
                <Lock className="w-3 h-3" />
                Locked
              </span>
            )}
          </div>
          <p className="text-slate-500 text-xs font-mono truncate max-w-xl">{capture.url}</p>
          <p className="text-slate-600 text-xs mt-1 font-mono">ID: {capture.evidence_id}</p>
        </div>

        {/* Actions */}
        {capture.status === "completed" && (
          <div className="flex gap-2 flex-shrink-0">
            <button
              onClick={() => verifyMutation.mutate()}
              disabled={verifyMutation.isPending}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-[#1e3a5f] text-slate-400 hover:text-slate-200 hover:border-[#1e5a8f] text-xs font-medium transition-colors"
            >
              <CheckCircle className="w-3.5 h-3.5" />
              Verify
            </button>
            <button
              onClick={() => reportMutation.mutate()}
              disabled={reportMutation.isPending}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-[#1e3a5f] text-slate-400 hover:text-slate-200 hover:border-[#1e5a8f] text-xs font-medium transition-colors"
            >
              <FileText className="w-3.5 h-3.5" />
              Generate Report
            </button>
            <button
              onClick={() => downloadMutation.mutate()}
              disabled={downloadMutation.isPending}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              Download
            </button>
          </div>
        )}
      </div>

      {/* Verify result */}
      {verifyMutation.data && (
        <div className={clsx(
          "p-3 rounded-lg border flex items-center gap-2 text-sm",
          verifyMutation.data.data.verified
            ? "bg-green-500/10 border-green-500/20 text-green-400"
            : "bg-red-500/10 border-red-500/20 text-red-400"
        )}>
          {verifyMutation.data.data.verified ? <CheckCircle className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
          {verifyMutation.data.data.verified
            ? "Evidence integrity verified - All hashes match"
            : `Integrity check failed: ${verifyMutation.data.data.errors?.join(", ")}`}
        </div>
      )}

      {/* Status + Progress for active captures */}
      {(capture.status === "pending" || capture.status === "running") && (
        <Section title="Capture Progress" icon={RefreshCw}>
          <CaptureProgress captureId={captureId} />
        </Section>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-[#1e3a5f]">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as any)}
            className={clsx(
              "flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px",
              activeTab === tab.key
                ? "border-blue-500 text-blue-400"
                : "border-transparent text-slate-500 hover:text-slate-300"
            )}
          >
            <tab.icon className="w-3.5 h-3.5" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === "overview" && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Section title="Capture Information" icon={Shield}>
            <DataRow label="Evidence ID" value={capture.evidence_id} mono />
            <DataRow label="URL" value={capture.url} />
            <DataRow label="Final URL" value={capture.final_url} />
            <DataRow label="Domain" value={capture.domain} />
            <DataRow label="Status" value={capture.status} />
            <DataRow label="Capture Type" value={capture.capture_type} />
            <DataRow label="Case Number" value={capture.case_number} />
            <DataRow label="HTTP Status" value={capture.http_status_code?.toString()} />
            <DataRow label="Server IP" value={capture.server_ip} />
            <DataRow label="Resources" value={capture.total_resources?.toString()} />
          </Section>

          <Section title="Timestamps" icon={Clock}>
            <DataRow label="Initiated (UTC)" value={capture.initiated_at ? format(new Date(capture.initiated_at), "yyyy-MM-dd HH:mm:ss") : null} />
            <DataRow label="Started (UTC)" value={capture.capture_started_at ? format(new Date(capture.capture_started_at), "yyyy-MM-dd HH:mm:ss") : null} />
            <DataRow label="Completed (UTC)" value={capture.capture_completed_at ? format(new Date(capture.capture_completed_at), "yyyy-MM-dd HH:mm:ss") : null} />
            <DataRow label="RFC 3161 TSA" value={capture.tsa_url} />
            <DataRow label="Timestamp Token" value={capture.tsa_timestamp ? "Received ✓" : "Not requested"} />
          </Section>

          <Section title="Integrity Hashes" icon={Hash}>
            <DataRow label="HTML SHA-256" value={capture.html_sha256} mono />
            <DataRow label="DOM SHA-256" value={capture.dom_sha256} mono />
            <DataRow label="Package SHA-256" value={capture.package_sha256} mono />
            <DataRow label="Package SHA-512" value={capture.package_sha512 ? capture.package_sha512.slice(0, 32) + "..." : null} mono />
          </Section>

          <Section title="Browser Context" icon={Globe}>
            <DataRow label="User Agent" value={capture.user_agent} />
            <DataRow label="Viewport" value={capture.viewport_width ? `${capture.viewport_width}x${capture.viewport_height}` : null} />
            <DataRow label="Screenshots" value={capture.screenshot_count?.toString()} />
            <DataRow label="Evidence Locked" value={capture.is_locked ? "Yes (Read-Only)" : "No"} />
          </Section>
        </div>
      )}

      {activeTab === "hashes" && hashes && (
        <Section title="Complete Hash Manifest" icon={Hash}>
          <div className="space-y-4">
            <div className="p-3 rounded bg-[#0a0e1a] border border-[#1e3a5f]">
              <p className="text-xs text-slate-500 mb-1">Evidence Package SHA-256</p>
              <p className="hash-text break-all">{hashes.package?.sha256 || "N/A"}</p>
            </div>
            <div className="p-3 rounded bg-[#0a0e1a] border border-[#1e3a5f]">
              <p className="text-xs text-slate-500 mb-1">Evidence Package SHA-512</p>
              <p className="hash-text break-all text-[10px]">{hashes.package?.sha512 || "N/A"}</p>
            </div>

            {hashes.screenshots && hashes.screenshots.length > 0 && (
              <div>
                <h4 className="text-xs font-medium text-slate-400 mb-2">Screenshots</h4>
                <div className="space-y-2">
                  {hashes.screenshots.map((ss: any, i: number) => (
                    <div key={i} className="flex items-center gap-3 p-2 rounded bg-[#0a0e1a] border border-[#1e3a5f]">
                      <Camera className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" />
                      <span className="text-xs text-slate-400 w-24 flex-shrink-0">{ss.filename}</span>
                      <span className="hash-text text-[10px] break-all flex-1">{ss.sha256}</span>
                      <CopyButton text={ss.sha256} />
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </Section>
      )}

      {activeTab === "logs" && (
        <Section title="Forensic Process Log" icon={List}>
          <div className="space-y-1 max-h-[600px] overflow-y-auto">
            {(logs || []).map((log: any) => (
              <div
                key={log.sequence}
                className={clsx(
                  "flex items-start gap-3 px-3 py-2 rounded text-xs",
                  log.success ? "hover:bg-white/5" : "bg-red-500/5 border border-red-500/10"
                )}
              >
                <span className="text-slate-600 font-mono w-8 flex-shrink-0">{String(log.sequence).padStart(3, "0")}</span>
                <span className="text-slate-500 w-32 flex-shrink-0 font-mono">{log.timestamp_utc?.slice(11, 19)}</span>
                <span className={clsx(
                  "w-40 flex-shrink-0 font-mono",
                  log.success ? "text-blue-400" : "text-red-400"
                )}>
                  {log.event_type}
                </span>
                <span className="text-slate-400 flex-1">{log.message}</span>
              </div>
            ))}
          </div>
        </Section>
      )}

      {activeTab === "metadata" && metadata && (
        <Section title="Page Metadata" icon={Database}>
          <DataRow label="Page Title" value={metadata.title} />
          <DataRow label="Description" value={metadata.description} />
          <DataRow label="Canonical URL" value={metadata.canonical_url} />
          <DataRow label="Language" value={metadata.language} />
          <DataRow label="Links Found" value={metadata.links_count?.toString()} />
          <DataRow label="Cookies" value={metadata.cookies_count?.toString()} />
          <DataRow label="iFrames" value={metadata.iframes_count?.toString()} />
        </Section>
      )}

      {activeTab === "social" && social && (
        <Section title="Social Media Data" icon={Globe}>
          <DataRow label="Platform" value={social.platform} />
          <DataRow label="Author" value={social.author_username} />
          <DataRow label="Display Name" value={social.author_display_name} />
          <DataRow label="Post Date" value={social.post_datetime} />
          <DataRow label="Likes" value={social.likes_count?.toString()} />
          <DataRow label="Comments" value={social.comments_count?.toString()} />
          {social.post_text && (
            <div className="mt-4">
              <p className="text-xs text-slate-500 mb-2">Post Content</p>
              <div className="p-3 rounded bg-[#0a0e1a] border border-[#1e3a5f] text-sm text-slate-300 whitespace-pre-wrap">
                {social.post_text}
              </div>
            </div>
          )}
          {social.hashtags && social.hashtags.length > 0 && (
            <div className="mt-3">
              <p className="text-xs text-slate-500 mb-2">Hashtags</p>
              <div className="flex flex-wrap gap-1.5">
                {social.hashtags.map((tag: string, i: number) => (
                  <span key={i} className="text-xs px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}
        </Section>
      )}
    </div>
  );
}
