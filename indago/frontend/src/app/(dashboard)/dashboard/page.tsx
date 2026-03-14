"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Shield, Globe, CheckCircle, Clock, XCircle,
  TrendingUp, Download, Hash, AlertTriangle, Play
} from "lucide-react";
import { capturesApi, type Capture } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { format } from "date-fns";
import Link from "next/link";
import { clsx } from "clsx";

function StatCard({
  label, value, icon: Icon, color = "blue", sub
}: {
  label: string;
  value: string | number;
  icon: any;
  color?: string;
  sub?: string;
}) {
  const colors = {
    blue: "text-blue-400 bg-blue-500/10 border-blue-500/20",
    green: "text-green-400 bg-green-500/10 border-green-500/20",
    amber: "text-amber-400 bg-amber-500/10 border-amber-500/20",
    red: "text-red-400 bg-red-500/10 border-red-500/20",
  };

  return (
    <div className="forensic-card p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">{label}</p>
          <p className="text-2xl font-bold text-slate-100 mt-1">{value}</p>
          {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
        </div>
        <div className={clsx("p-2.5 rounded-lg border", colors[color as keyof typeof colors])}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const configs = {
    pending: { label: "Queued", className: "status-pending" },
    running: { label: "Capturing", className: "status-running" },
    completed: { label: "Complete", className: "status-completed" },
    failed: { label: "Failed", className: "status-failed" },
    cancelled: { label: "Cancelled", className: "bg-slate-500/10 text-slate-400 border border-slate-500/20" },
  };
  const cfg = configs[status as keyof typeof configs] || configs.pending;
  return (
    <span className={clsx("text-xs px-2 py-0.5 rounded-full font-medium", cfg.className)}>
      {cfg.label}
    </span>
  );
}

export default function DashboardPage() {
  const { user } = useAuthStore();

  const { data: captures, isLoading } = useQuery({
    queryKey: ["captures"],
    queryFn: () => capturesApi.list({ limit: 50 }).then((r) => r.data as Capture[]),
    refetchInterval: 10000,
  });

  const stats = {
    total: captures?.length || 0,
    completed: captures?.filter((c) => c.status === "completed").length || 0,
    running: captures?.filter((c) => c.status === "running" || c.status === "pending").length || 0,
    failed: captures?.filter((c) => c.status === "failed").length || 0,
  };

  const recentCaptures = (captures || []).slice(0, 8);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Dashboard</h1>
          <p className="text-slate-500 text-sm mt-1">
            Welcome back, <span className="text-blue-400">{user?.full_name}</span>
          </p>
        </div>
        <Link
          href="/capture"
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors shadow-lg shadow-blue-600/20"
        >
          <Play className="w-4 h-4" />
          New Capture
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Total Evidence" value={stats.total} icon={Shield} color="blue" />
        <StatCard label="Completed" value={stats.completed} icon={CheckCircle} color="green"
          sub={`${stats.total > 0 ? Math.round((stats.completed / stats.total) * 100) : 0}% success rate`} />
        <StatCard label="In Progress" value={stats.running} icon={Clock} color="amber" />
        <StatCard label="Failed" value={stats.failed} icon={XCircle} color="red" />
      </div>

      {/* Compliance Banner */}
      <div className="forensic-card p-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-blue-500/10 border border-blue-500/20">
            <Shield className="w-5 h-5 text-blue-400" />
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-200">Forensic Evidence Platform</p>
            <p className="text-xs text-slate-500">
              All captures comply with ISO/IEC 27037 · RFC 3227 · RFC 3161 · NIST Digital Forensics Guidelines
            </p>
          </div>
          <div className="ml-auto flex gap-2">
            {["ISO 27037", "RFC 3227", "RFC 3161"].map((s) => (
              <span key={s} className="text-xs px-2 py-1 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                {s}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Captures */}
      <div className="forensic-card">
        <div className="flex items-center justify-between p-4 border-b border-[#1e3a5f]">
          <h2 className="font-semibold text-slate-200">Recent Evidence Captures</h2>
          <Link href="/captures" className="text-xs text-blue-400 hover:text-blue-300 transition-colors">
            View all →
          </Link>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center h-32">
            <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : recentCaptures.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-slate-500">
            <Globe className="w-8 h-8 mb-2 text-slate-700" />
            <p className="text-sm">No captures yet</p>
            <Link href="/capture" className="text-xs text-blue-400 hover:text-blue-300 mt-1 transition-colors">
              Start your first capture →
            </Link>
          </div>
        ) : (
          <div className="divide-y divide-[#1e3a5f]">
            {recentCaptures.map((capture) => (
              <Link
                key={capture.id}
                href={`/captures/${capture.id}`}
                className="flex items-center gap-4 px-4 py-3 hover:bg-white/5 transition-colors group"
              >
                <div className={clsx(
                  "w-2 h-2 rounded-full flex-shrink-0",
                  capture.status === "completed" && "bg-green-400",
                  capture.status === "running" && "bg-blue-400 animate-pulse",
                  capture.status === "pending" && "bg-amber-400 animate-pulse",
                  capture.status === "failed" && "bg-red-400",
                  capture.status === "cancelled" && "bg-slate-400",
                )} />

                <div className="flex-1 min-w-0">
                  <p className="text-sm text-slate-300 truncate group-hover:text-blue-300 transition-colors font-mono">
                    {capture.url}
                  </p>
                  <div className="flex items-center gap-3 mt-0.5">
                    <span className="text-xs text-slate-500">
                      {capture.initiated_at ? format(new Date(capture.initiated_at), "MMM d, HH:mm") : "N/A"}
                    </span>
                    {capture.case_number && (
                      <span className="text-xs text-slate-600">Case: {capture.case_number}</span>
                    )}
                    {capture.total_resources > 0 && (
                      <span className="text-xs text-slate-600">{capture.total_resources} resources</span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 flex-shrink-0">
                  {capture.package_sha256 && (
                    <div className="flex items-center gap-1 text-xs text-green-400" title="Integrity verified">
                      <Hash className="w-3 h-3" />
                    </div>
                  )}
                  <StatusBadge status={capture.status} />
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
