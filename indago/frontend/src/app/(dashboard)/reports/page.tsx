"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { capturesApi, type Capture } from "@/lib/api";
import { FileText, Download, RefreshCw, CheckCircle, Clock } from "lucide-react";
import { format } from "date-fns";
import { clsx } from "clsx";
import { useState } from "react";

export default function ReportsPage() {
  const [generating, setGenerating] = useState<number | null>(null);

  const { data: captures, isLoading } = useQuery({
    queryKey: ["captures-completed"],
    queryFn: () => capturesApi.list({ limit: 100, status: "completed" }).then((r) => r.data as Capture[]),
  });

  const generateMutation = useMutation({
    mutationFn: (id: number) => capturesApi.generateReport(id),
    onSuccess: () => setGenerating(null),
    onError: () => setGenerating(null),
  });

  const downloadMutation = useMutation({
    mutationFn: async (capture: Capture) => {
      const response = await capturesApi.download(capture.id);
      const url = URL.createObjectURL(response.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `evidence_${capture.evidence_id.slice(0, 8)}.zip`;
      a.click();
      URL.revokeObjectURL(url);
    },
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Reportes de Evidencia</h1>
        <p className="text-slate-500 text-sm mt-1">Genera y descarga reportes forenses en PDF y JSON</p>
      </div>

      <div className="forensic-card p-4 flex items-start gap-3 bg-blue-500/5 border-blue-500/20">
        <FileText className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
        <div className="text-xs text-slate-400">
          <p className="font-medium text-blue-300 mb-0.5">Reporte Forense Completo</p>
          <p>Incluye: ID de evidencia, URL, metadatos de red, hashes SHA-256/SHA-512, log forense completo,
          datos de redes sociales (si aplica), sello temporal RFC 3161, y declaración de integridad.</p>
        </div>
      </div>

      <div className="forensic-card">
        <div className="px-4 py-3 border-b border-[#1e3a5f]">
          <h2 className="font-semibold text-slate-200">Capturas Completadas</h2>
        </div>

        {isLoading ? (
          <div className="flex justify-center p-8">
            <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : !captures?.length ? (
          <div className="flex flex-col items-center justify-center p-12 text-slate-500">
            <FileText className="w-10 h-10 mb-2 text-slate-700" />
            <p>No hay capturas completadas</p>
            <p className="text-xs mt-1">Los reportes se generan desde capturas completadas</p>
          </div>
        ) : (
          <div className="divide-y divide-[#1e3a5f]">
            {captures.map((capture) => (
              <div key={capture.id} className="px-4 py-4 flex items-center gap-4">
                <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-mono text-slate-300 truncate">{capture.url}</p>
                  <div className="flex items-center gap-3 mt-0.5">
                    <span className="text-xs font-mono text-slate-500">{capture.evidence_id.slice(0, 8)}...</span>
                    <span className="text-xs text-slate-500">
                      {format(new Date(capture.initiated_at), "MMM d, yyyy HH:mm")}
                    </span>
                    {capture.case_number && (
                      <span className="text-xs text-blue-400">{capture.case_number}</span>
                    )}
                  </div>
                </div>
                <div className="flex gap-2 flex-shrink-0">
                  <button
                    onClick={() => { setGenerating(capture.id); generateMutation.mutate(capture.id); }}
                    disabled={generating === capture.id}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#1e3a5f] text-slate-400 hover:text-slate-200 hover:border-[#1e5a8f] text-xs font-medium transition-colors disabled:opacity-50"
                  >
                    {generating === capture.id ? (
                      <><RefreshCw className="w-3 h-3 animate-spin" /> Generando...</>
                    ) : (
                      <><FileText className="w-3 h-3" /> Generar Reporte</>
                    )}
                  </button>
                  <button
                    onClick={() => downloadMutation.mutate(capture)}
                    disabled={downloadMutation.isPending}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium transition-colors disabled:opacity-50"
                  >
                    <Download className="w-3 h-3" />
                    Descargar ZIP
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
