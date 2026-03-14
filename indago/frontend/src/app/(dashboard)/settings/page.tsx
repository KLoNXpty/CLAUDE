"use client";

import { useQuery } from "@tanstack/react-query";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { User, Shield, Key, Info, Server } from "lucide-react";

export default function SettingsPage() {
  const { user } = useAuthStore();

  const { data: me } = useQuery({
    queryKey: ["me"],
    queryFn: () => authApi.me().then((r) => r.data),
  });

  const currentUser = me || user;

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Configuración</h1>
        <p className="text-slate-500 text-sm mt-1">Perfil de investigador y configuración del sistema</p>
      </div>

      {/* Profile */}
      <div className="forensic-card p-6 space-y-4">
        <h2 className="font-semibold text-slate-200 flex items-center gap-2">
          <User className="w-4 h-4 text-blue-400" /> Perfil de Investigador
        </h2>
        <div className="grid grid-cols-2 gap-4">
          {[
            { label: "Nombre completo", value: currentUser?.full_name },
            { label: "Usuario", value: currentUser?.username },
            { label: "Email", value: currentUser?.email },
            { label: "Rol", value: currentUser?.role },
            { label: "Organización", value: currentUser?.organization || "—" },
            { label: "Número de placa", value: (currentUser as any)?.badge_number || "—" },
          ].map((field) => (
            <div key={field.label}>
              <p className="text-xs text-slate-500">{field.label}</p>
              <p className="text-sm text-slate-200 mt-0.5 font-medium">{field.value || "—"}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Platform info */}
      <div className="forensic-card p-6 space-y-4">
        <h2 className="font-semibold text-slate-200 flex items-center gap-2">
          <Server className="w-4 h-4 text-blue-400" /> Información de la Plataforma
        </h2>
        <div className="space-y-3">
          {[
            { label: "Plataforma", value: "INDAGO Evidence Capture v1.0" },
            { label: "Base de datos", value: "SQLite (demo) / PostgreSQL (producción)" },
            { label: "Motor de captura", value: "Playwright Chromium Headless" },
            { label: "Almacenamiento", value: "Local / S3-compatible (MinIO)" },
            { label: "Formato de evidencia", value: "WARC/1.1, PNG sin compresión, ZIP" },
            { label: "Hashes", value: "SHA-256, SHA-512, MD5" },
            { label: "Sellado temporal", value: "RFC 3161 TSA (FreeTSA.org)" },
          ].map((item) => (
            <div key={item.label} className="flex items-center justify-between py-2 border-b border-[#1e3a5f]/50 last:border-0">
              <span className="text-xs text-slate-500">{item.label}</span>
              <span className="text-xs text-slate-300 font-medium">{item.value}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Compliance */}
      <div className="forensic-card p-6">
        <h2 className="font-semibold text-slate-200 flex items-center gap-2 mb-4">
          <Shield className="w-4 h-4 text-blue-400" /> Estándares de Cumplimiento
        </h2>
        <div className="grid grid-cols-2 gap-3">
          {[
            { std: "ISO/IEC 27037", desc: "Identificación, recolección y preservación de evidencia digital" },
            { std: "ISO/IEC 27042", desc: "Análisis e interpretación de evidencia digital" },
            { std: "RFC 3227", desc: "Mejores prácticas para recolección de evidencia" },
            { std: "RFC 3161", desc: "Protocolo de sellado temporal de confianza" },
            { std: "NIST SP 800-86", desc: "Guía de técnicas forenses en respuesta a incidentes" },
            { std: "WARC/1.1", desc: "Formato de archivo web para preservación" },
          ].map((item) => (
            <div key={item.std} className="p-3 rounded-lg bg-[#0a0e1a] border border-[#1e3a5f]">
              <p className="text-xs font-semibold text-blue-400">{item.std}</p>
              <p className="text-[10px] text-slate-500 mt-0.5 leading-relaxed">{item.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
