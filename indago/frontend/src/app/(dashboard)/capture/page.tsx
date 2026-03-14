"use client";

import { Shield, Info } from "lucide-react";
import { CaptureForm } from "@/components/capture/capture-form";

export default function CapturePage() {
  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-100">New Evidence Capture</h1>
        <p className="text-slate-500 text-sm mt-1">
          Capture and preserve digital evidence with full chain of custody
        </p>
      </div>

      {/* Info Banner */}
      <div className="p-4 rounded-lg bg-blue-500/5 border border-blue-500/20 flex items-start gap-3">
        <Info className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
        <div className="text-xs text-slate-400 space-y-1">
          <p className="font-medium text-blue-300">Forensic Capture Process</p>
          <p>
            The system will capture the complete page content using Playwright Chromium headless browser,
            preserving all resources, generating cryptographic hashes, and requesting an RFC 3161 trusted
            timestamp. The evidence will be immutably locked after capture.
          </p>
        </div>
      </div>

      {/* Capture Form */}
      <div className="forensic-card p-6">
        <div className="flex items-center gap-2 mb-6 pb-4 border-b border-[#1e3a5f]">
          <Shield className="w-5 h-5 text-blue-400" />
          <h2 className="font-semibold text-slate-200">Capture Configuration</h2>
        </div>
        <CaptureForm />
      </div>
    </div>
  );
}
