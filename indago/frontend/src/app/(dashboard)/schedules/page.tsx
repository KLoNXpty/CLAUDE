"use client";
// @ts-nocheck

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { capturesApi } from "@/lib/api";
import { Clock, Plus, Trash2, Play, CheckCircle, AlertCircle, ChevronDown, ChevronUp } from "lucide-react";
import { clsx } from "clsx";
import { format } from "date-fns";

const schema = z.object({
  url: z.string().url("URL inválida"),
  schedule_cron: z.string().min(1, "Cron requerido"),
  capture_type: z.string().optional(),
  case_number: z.string().optional(),
  schedule_description: z.string().optional(),
});

const CRON_PRESETS = [
  { label: "Cada hora", value: "0 * * * *" },
  { label: "Cada 6 horas", value: "0 */6 * * *" },
  { label: "Diario (8am)", value: "0 8 * * *" },
  { label: "Cada lunes", value: "0 8 * * 1" },
  { label: "Mensual (día 1)", value: "0 8 1 * *" },
];

export default function SchedulesPage() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);

  const { data: schedules, isLoading } = useQuery({
    queryKey: ["schedules"],
    queryFn: () => capturesApi.listSchedules().then((r) => r.data),
  });

  const createMutation = useMutation({
    mutationFn: capturesApi.createSchedule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["schedules"] });
      setShowForm(false);
      reset();
    },
  });

  const { register, handleSubmit, setValue, watch, reset, formState: { errors } } = useForm({
    resolver: zodResolver(schema),
    defaultValues: { capture_type: "full_page" },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Capturas Programadas</h1>
          <p className="text-slate-500 text-sm mt-1">Monitoreo automático de URLs a intervalos regulares</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors"
        >
          <Plus className="w-4 h-4" />
          Nueva Programación
        </button>
      </div>

      {/* Create form */}
      {showForm && (
        <div className="forensic-card p-6">
          <h2 className="font-semibold text-slate-200 mb-4 flex items-center gap-2">
            <Clock className="w-4 h-4 text-blue-400" />
            Programar Captura Automática
          </h2>
          <form onSubmit={handleSubmit((d) => createMutation.mutate(d))} className="space-y-4">
            <div>
              <label className="text-xs font-medium text-slate-400">URL objetivo *</label>
              <input {...register("url")} placeholder="https://example.com"
                className="w-full mt-1 px-3 py-2 rounded-lg bg-[#0a0e1a] border border-[#1e3a5f] text-slate-200 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500/50" />
              {errors.url && <p className="text-xs text-red-400 mt-1">{errors.url.message}</p>}
            </div>

            <div>
              <label className="text-xs font-medium text-slate-400">Frecuencia (Cron) *</label>
              <div className="flex flex-wrap gap-2 mt-1 mb-2">
                {CRON_PRESETS.map((p) => (
                  <button key={p.value} type="button"
                    onClick={() => setValue("schedule_cron", p.value)}
                    className={clsx("text-xs px-2.5 py-1 rounded-full border transition-colors",
                      watch("schedule_cron") === p.value
                        ? "bg-blue-600/30 border-blue-500/50 text-blue-300"
                        : "border-[#1e3a5f] text-slate-500 hover:text-slate-300 hover:border-[#1e5a8f]"
                    )}>
                    {p.label}
                  </button>
                ))}
              </div>
              <input {...register("schedule_cron")} placeholder="0 * * * *"
                className="w-full px-3 py-2 rounded-lg bg-[#0a0e1a] border border-[#1e3a5f] text-slate-200 text-sm font-mono focus:outline-none focus:ring-1 focus:ring-blue-500/50" />
              {errors.schedule_cron && <p className="text-xs text-red-400 mt-1">{errors.schedule_cron.message}</p>}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-medium text-slate-400">Número de caso</label>
                <input {...register("case_number")} placeholder="CASE-2024-001"
                  className="w-full mt-1 px-3 py-2 rounded-lg bg-[#0a0e1a] border border-[#1e3a5f] text-slate-200 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500/50" />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-400">Descripción</label>
                <input {...register("schedule_description")} placeholder="Monitoreo de..."
                  className="w-full mt-1 px-3 py-2 rounded-lg bg-[#0a0e1a] border border-[#1e3a5f] text-slate-200 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500/50" />
              </div>
            </div>

            <div className="flex gap-2 pt-2">
              <button type="submit" disabled={createMutation.isPending}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50">
                {createMutation.isPending ? "Creando..." : "Crear Programación"}
              </button>
              <button type="button" onClick={() => setShowForm(false)}
                className="px-4 py-2 border border-[#1e3a5f] text-slate-400 hover:text-slate-200 rounded-lg text-sm transition-colors">
                Cancelar
              </button>
            </div>
          </form>
        </div>
      )}

      {/* List */}
      <div className="forensic-card">
        <div className="px-4 py-3 border-b border-[#1e3a5f]">
          <h2 className="font-semibold text-slate-200">Programaciones Activas</h2>
        </div>
        {isLoading ? (
          <div className="flex justify-center p-8">
            <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : !schedules?.length ? (
          <div className="flex flex-col items-center justify-center p-12 text-slate-500">
            <Clock className="w-10 h-10 mb-2 text-slate-700" />
            <p>No hay capturas programadas</p>
            <p className="text-xs mt-1">Crea una para monitorear URLs automáticamente</p>
          </div>
        ) : (
          <div className="divide-y divide-[#1e3a5f]">
            {schedules.map((s: any) => (
              <div key={s.id} className="px-4 py-4 flex items-center gap-4">
                <div className={clsx("w-2 h-2 rounded-full flex-shrink-0",
                  s.is_active ? "bg-green-400" : "bg-slate-600")} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-mono text-slate-300 truncate">{s.url}</p>
                  <div className="flex items-center gap-3 mt-0.5">
                    <span className="text-xs font-mono text-blue-400">{s.schedule_cron}</span>
                    {s.schedule_description && <span className="text-xs text-slate-500">{s.schedule_description}</span>}
                    {s.run_count > 0 && <span className="text-xs text-slate-600">{s.run_count} ejecuciones</span>}
                  </div>
                </div>
                <div className="text-right flex-shrink-0">
                  {s.next_run_at && (
                    <p className="text-xs text-slate-400">
                      Próxima: {format(new Date(s.next_run_at), "MMM d, HH:mm")}
                    </p>
                  )}
                  <span className={clsx("text-xs px-2 py-0.5 rounded-full",
                    s.is_active ? "bg-green-500/10 text-green-400 border border-green-500/20" : "bg-slate-500/10 text-slate-400")}>
                    {s.is_active ? "Activo" : "Inactivo"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
