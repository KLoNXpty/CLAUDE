"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { capturesApi, type Capture } from "@/lib/api";
import { GitBranch, ArrowRight, CheckCircle, AlertTriangle, Search } from "lucide-react";
import { clsx } from "clsx";
import { format } from "date-fns";

export default function ComparePage() {
  const [idA, setIdA] = useState<number | "">("");
  const [idB, setIdB] = useState<number | "">("");

  const { data: captures } = useQuery({
    queryKey: ["captures"],
    queryFn: () => capturesApi.list({ limit: 100, status: "completed" }).then((r) => r.data as Capture[]),
  });

  const compareMutation = useMutation({
    mutationFn: () => capturesApi.compare(Number(idA), Number(idB)).then((r) => r.data),
  });

  const completedCaptures = (captures || []).filter((c) => c.status === "completed");

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Comparar Evidencias</h1>
        <p className="text-slate-500 text-sm mt-1">Detecta cambios entre dos capturas de la misma URL</p>
      </div>

      <div className="forensic-card p-6">
        <h2 className="font-semibold text-slate-200 mb-4 flex items-center gap-2">
          <GitBranch className="w-4 h-4 text-blue-400" />
          Seleccionar Capturas
        </h2>

        <div className="flex items-center gap-4">
          <div className="flex-1">
            <label className="text-xs font-medium text-slate-400 mb-1.5 block">Captura A (original)</label>
            <select value={idA} onChange={(e) => setIdA(e.target.value ? Number(e.target.value) : "")}
              className="w-full px-3 py-2.5 rounded-lg bg-[#0a0e1a] border border-[#1e3a5f] text-slate-200 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500/50">
              <option value="">Seleccionar captura...</option>
              {completedCaptures.map((c) => (
                <option key={c.id} value={c.id}>
                  #{c.id} — {c.url.slice(0, 50)} ({format(new Date(c.initiated_at), "MMM d HH:mm")})
                </option>
              ))}
            </select>
          </div>

          <ArrowRight className="w-5 h-5 text-slate-600 flex-shrink-0 mt-5" />

          <div className="flex-1">
            <label className="text-xs font-medium text-slate-400 mb-1.5 block">Captura B (nueva)</label>
            <select value={idB} onChange={(e) => setIdB(e.target.value ? Number(e.target.value) : "")}
              className="w-full px-3 py-2.5 rounded-lg bg-[#0a0e1a] border border-[#1e3a5f] text-slate-200 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500/50">
              <option value="">Seleccionar captura...</option>
              {completedCaptures.map((c) => (
                <option key={c.id} value={c.id}>
                  #{c.id} — {c.url.slice(0, 50)} ({format(new Date(c.initiated_at), "MMM d HH:mm")})
                </option>
              ))}
            </select>
          </div>
        </div>

        <button
          onClick={() => compareMutation.mutate()}
          disabled={!idA || !idB || idA === idB || compareMutation.isPending}
          className="mt-4 flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-600/40 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors"
        >
          <Search className="w-4 h-4" />
          {compareMutation.isPending ? "Comparando..." : "Comparar Evidencias"}
        </button>
      </div>

      {/* Results */}
      {compareMutation.data && (
        <div className="forensic-card p-6 space-y-4">
          <div className={clsx("flex items-center gap-3 p-4 rounded-lg border",
            compareMutation.data.identical
              ? "bg-green-500/10 border-green-500/20"
              : "bg-amber-500/10 border-amber-500/20"
          )}>
            {compareMutation.data.identical ? (
              <><CheckCircle className="w-5 h-5 text-green-400" />
                <div>
                  <p className="font-semibold text-green-300">Evidencias Idénticas</p>
                  <p className="text-xs text-slate-400">No se detectaron cambios entre las dos capturas</p>
                </div></>
            ) : (
              <><AlertTriangle className="w-5 h-5 text-amber-400" />
                <div>
                  <p className="font-semibold text-amber-300">{compareMutation.data.total_changes} Cambio(s) Detectado(s)</p>
                  <p className="text-xs text-slate-400">El contenido fue modificado entre las dos capturas</p>
                </div></>
            )}
          </div>

          {compareMutation.data.changes.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-slate-300">Diferencias detectadas:</h3>
              {compareMutation.data.changes.map((change: any, i: number) => (
                <div key={i} className="p-3 rounded-lg bg-[#0a0e1a] border border-amber-500/20">
                  <p className="text-sm font-medium text-amber-300 mb-2">{change.type}</p>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <p className="text-xs text-slate-500 mb-1">Captura A</p>
                      <p className="text-xs font-mono text-slate-300 break-all">{String(change.value_a).slice(0, 64) || "—"}</p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500 mb-1">Captura B</p>
                      <p className="text-xs font-mono text-slate-300 break-all">{String(change.value_b).slice(0, 64) || "—"}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
