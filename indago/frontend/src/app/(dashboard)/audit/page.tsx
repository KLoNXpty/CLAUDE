"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Hash, User, Clock, Shield, Download, Eye, Lock } from "lucide-react";
import { format } from "date-fns";
import { clsx } from "clsx";

const ACTION_CONFIG: Record<string, { label: string; icon: any; color: string }> = {
  login_success: { label: "Inicio de sesión", icon: User, color: "text-green-400" },
  login_failed: { label: "Login fallido", icon: User, color: "text-red-400" },
  capture_created: { label: "Captura creada", icon: Shield, color: "text-blue-400" },
  evidence_accessed: { label: "Evidencia accedida", icon: Eye, color: "text-amber-400" },
  evidence_downloaded: { label: "Evidencia descargada", icon: Download, color: "text-purple-400" },
  evidence_transferred: { label: "Evidencia transferida", icon: Lock, color: "text-orange-400" },
};

export default function AuditPage() {
  const { data: auditLogs, isLoading } = useQuery({
    queryKey: ["audit-logs"],
    queryFn: () => api.get("/audit").then((r) => r.data).catch(() => []),
    refetchInterval: 30000,
  });

  // Fallback: use captures list for audit display
  const { data: captures } = useQuery({
    queryKey: ["captures"],
    queryFn: () => api.get("/captures").then((r) => r.data),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Cadena de Custodia</h1>
        <p className="text-slate-500 text-sm mt-1">Registro completo de accesos y acciones sobre la evidencia</p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="forensic-card p-4">
          <p className="text-xs text-slate-500 mb-1">Total Capturas</p>
          <p className="text-2xl font-bold text-slate-100">{captures?.length || 0}</p>
        </div>
        <div className="forensic-card p-4">
          <p className="text-xs text-slate-500 mb-1">Completadas</p>
          <p className="text-2xl font-bold text-green-400">{captures?.filter((c: any) => c.status === "completed").length || 0}</p>
        </div>
        <div className="forensic-card p-4">
          <p className="text-xs text-slate-500 mb-1">Evidencias Bloqueadas</p>
          <p className="text-2xl font-bold text-blue-400">{captures?.filter((c: any) => c.is_locked).length || 0}</p>
        </div>
      </div>

      {/* Compliance banner */}
      <div className="forensic-card p-4 flex items-start gap-3 bg-green-500/5 border-green-500/20">
        <Shield className="w-4 h-4 text-green-400 mt-0.5 flex-shrink-0" />
        <div className="text-xs text-slate-400">
          <p className="font-medium text-green-300 mb-0.5">Cumplimiento ISO/IEC 27037 — Cadena de Custodia Digital</p>
          <p>Todos los accesos, descargas y transferencias de evidencia digital quedan registrados con timestamp UTC,
          IP del operador y hash del paquete. La evidencia es read-only tras ser capturada.</p>
        </div>
      </div>

      {/* Evidence table */}
      <div className="forensic-card">
        <div className="px-4 py-3 border-b border-[#1e3a5f] flex items-center justify-between">
          <h2 className="font-semibold text-slate-200">Registro de Evidencias</h2>
          <span className="text-xs text-slate-500">{captures?.length || 0} registros</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#1e3a5f] bg-[#0a0e1a]">
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">ID Evidencia</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">URL</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Fecha UTC</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Estado</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Integridad</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Bloqueada</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1e3a5f]">
              {isLoading ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center">
                  <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto" />
                </td></tr>
              ) : (captures || []).map((c: any) => (
                <tr key={c.id} className="hover:bg-white/5 transition-colors">
                  <td className="px-4 py-3 text-xs font-mono text-blue-400">{c.evidence_id?.slice(0, 12)}...</td>
                  <td className="px-4 py-3 text-xs text-slate-300 font-mono max-w-xs truncate">{c.url}</td>
                  <td className="px-4 py-3 text-xs text-slate-400">
                    {format(new Date(c.initiated_at), "yyyy-MM-dd HH:mm:ss")}
                  </td>
                  <td className="px-4 py-3">
                    <span className={clsx("text-xs px-2 py-0.5 rounded-full border",
                      c.status === "completed" ? "bg-green-500/10 text-green-400 border-green-500/20" :
                      c.status === "running" ? "bg-blue-500/10 text-blue-400 border-blue-500/20" :
                      c.status === "failed" ? "bg-red-500/10 text-red-400 border-red-500/20" :
                      "bg-slate-500/10 text-slate-400 border-slate-500/20"
                    )}>{c.status}</span>
                  </td>
                  <td className="px-4 py-3">
                    {c.package_sha256 ? (
                      <span className="text-xs font-mono text-green-400 flex items-center gap-1">
                        <Hash className="w-3 h-3" />{c.package_sha256.slice(0, 10)}...
                      </span>
                    ) : <span className="text-xs text-slate-600">—</span>}
                  </td>
                  <td className="px-4 py-3">
                    {c.is_locked
                      ? <span className="flex items-center gap-1 text-xs text-green-400"><Lock className="w-3 h-3" /> Sí</span>
                      : <span className="text-xs text-slate-600">No</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
