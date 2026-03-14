"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { capturesApi, type Capture } from "@/lib/api";
import { format } from "date-fns";
import {
  Shield, Hash, Download, Play, Search, Filter,
  CheckCircle, Clock, XCircle, Globe, Lock
} from "lucide-react";
import Link from "next/link";
import { clsx } from "clsx";

export default function CapturesPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const { data: captures, isLoading } = useQuery({
    queryKey: ["captures", statusFilter],
    queryFn: () =>
      capturesApi.list({ limit: 100, status: statusFilter || undefined }).then((r) => r.data as Capture[]),
    refetchInterval: 15000,
  });

  const filtered = (captures || []).filter(
    (c) =>
      !search ||
      c.url.toLowerCase().includes(search.toLowerCase()) ||
      c.case_number?.toLowerCase().includes(search.toLowerCase()) ||
      c.evidence_id?.includes(search.toLowerCase())
  );

  const statusConfig = {
    pending: { icon: Clock, color: "text-amber-400", bg: "bg-amber-500/10 border-amber-500/20" },
    running: { icon: Clock, color: "text-blue-400", bg: "bg-blue-500/10 border-blue-500/20" },
    completed: { icon: CheckCircle, color: "text-green-400", bg: "bg-green-500/10 border-green-500/20" },
    failed: { icon: XCircle, color: "text-red-400", bg: "bg-red-500/10 border-red-500/20" },
    cancelled: { icon: XCircle, color: "text-slate-400", bg: "bg-slate-500/10 border-slate-500/20" },
  };

  const formatSize = (bytes: number) => {
    if (!bytes) return "—";
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Evidence Library</h1>
          <p className="text-slate-500 text-sm mt-1">{(captures || []).length} evidence captures</p>
        </div>
        <Link
          href="/capture"
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors"
        >
          <Play className="w-4 h-4" />
          New Capture
        </Link>
      </div>

      {/* Filters */}
      <div className="flex gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by URL, case number, or evidence ID..."
            className="w-full pl-9 pr-4 py-2 rounded-lg bg-[#0d1526] border border-[#1e3a5f] text-slate-200 text-sm placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-blue-500/50 focus:border-blue-500/50"
          />
        </div>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 rounded-lg bg-[#0d1526] border border-[#1e3a5f] text-slate-300 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500/50"
        >
          <option value="">All Status</option>
          <option value="pending">Pending</option>
          <option value="running">Running</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      {/* Table */}
      <div className="forensic-card overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-[#1e3a5f] bg-[#0a0e1a]">
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Status</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">URL / Evidence</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Date</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Resources</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Integrity</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1e3a5f]">
            {isLoading ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center">
                  <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto" />
                </td>
              </tr>
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-12 text-center text-slate-500">
                  <Globe className="w-8 h-8 mx-auto mb-2 text-slate-700" />
                  <p>No captures found</p>
                </td>
              </tr>
            ) : (
              filtered.map((capture) => {
                const cfg = statusConfig[capture.status] || statusConfig.pending;
                const StatusIcon = cfg.icon;
                return (
                  <tr key={capture.id} className="hover:bg-white/5 transition-colors group">
                    <td className="px-4 py-3">
                      <span className={clsx("flex items-center gap-1.5 text-xs font-medium w-fit px-2 py-1 rounded-full border", cfg.bg, cfg.color)}>
                        <StatusIcon className="w-3 h-3" />
                        {capture.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <p className="text-sm text-slate-300 font-mono truncate max-w-xs group-hover:text-blue-300 transition-colors">
                        {capture.url}
                      </p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <p className="text-xs text-slate-600 font-mono">{capture.evidence_id?.slice(0, 8)}...</p>
                        {capture.case_number && (
                          <span className="text-xs text-slate-500">· {capture.case_number}</span>
                        )}
                        {capture.is_locked && <Lock className="w-3 h-3 text-green-400" />}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <p className="text-xs text-slate-400">
                        {capture.initiated_at ? format(new Date(capture.initiated_at), "MMM d, yyyy") : "—"}
                      </p>
                      <p className="text-xs text-slate-600">
                        {capture.initiated_at ? format(new Date(capture.initiated_at), "HH:mm:ss") : ""}
                      </p>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400">
                      <p>{capture.total_resources || 0} files</p>
                      <p className="text-slate-600">{formatSize(capture.total_size_bytes)}</p>
                    </td>
                    <td className="px-4 py-3">
                      {capture.package_sha256 ? (
                        <div className="flex items-center gap-1.5">
                          <Hash className="w-3.5 h-3.5 text-green-400" />
                          <span className="text-xs text-green-400 font-mono">
                            {capture.package_sha256.slice(0, 8)}...
                          </span>
                        </div>
                      ) : (
                        <span className="text-xs text-slate-600">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Link
                          href={`/captures/${capture.id}`}
                          className="text-xs px-2.5 py-1 rounded-lg bg-blue-600/20 text-blue-400 border border-blue-500/20 hover:bg-blue-600/30 transition-colors"
                        >
                          View
                        </Link>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
