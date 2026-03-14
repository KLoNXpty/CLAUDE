"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Shield, Globe, Fingerprint, Clock, AlertCircle,
  ChevronDown, ChevronUp, Loader2, Play, Instagram,
  Youtube, Twitter, Facebook
} from "lucide-react";
import { clsx } from "clsx";
import { capturesApi } from "@/lib/api";
import { useRouter } from "next/navigation";

const formSchema = z.object({
  url: z.string().url("Enter a valid URL starting with http:// or https://"),
  capture_type: z.enum(["full_page", "viewport", "social_media", "profile", "thread"]),
  case_number: z.string().optional(),
  case_description: z.string().optional(),
});

type FormData = z.infer<typeof formSchema>;

const captureTypes = [
  { value: "full_page", label: "Full Page", icon: Globe, desc: "Complete page capture with all resources" },
  { value: "viewport", label: "Viewport", icon: Shield, desc: "Visible area screenshot only" },
  { value: "social_media", label: "Social Media", icon: Instagram, desc: "Optimized for social platforms" },
  { value: "profile", label: "Profile", icon: Fingerprint, desc: "Complete social media profile" },
  { value: "thread", label: "Thread", icon: Twitter, desc: "Full thread/comment chain" },
];

const socialPlatforms = [
  { icon: Instagram, name: "Instagram", pattern: "instagram.com" },
  { icon: Youtube, name: "YouTube", pattern: "youtube.com" },
  { icon: Twitter, name: "Twitter/X", pattern: "twitter.com" },
  { icon: Facebook, name: "Facebook", pattern: "facebook.com" },
];

export function CaptureForm() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [detectedPlatform, setDetectedPlatform] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: { capture_type: "full_page" },
  });

  const urlValue = watch("url");

  const detectPlatform = (url: string) => {
    for (const platform of socialPlatforms) {
      if (url.includes(platform.pattern)) {
        setDetectedPlatform(platform.name);
        setValue("capture_type", "social_media");
        return;
      }
    }
    setDetectedPlatform(null);
  };

  const mutation = useMutation({
    mutationFn: capturesApi.create,
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ["captures"] });
      router.push(`/captures/${response.data.id}`);
    },
  });

  const onSubmit = (data: FormData) => {
    mutation.mutate(data);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      {/* URL Input */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-slate-300 flex items-center gap-2">
          <Globe className="w-4 h-4 text-blue-400" />
          Target URL
          <span className="text-red-400">*</span>
        </label>
        <div className="relative">
          <input
            {...register("url")}
            onChange={(e) => {
              register("url").onChange(e);
              detectPlatform(e.target.value);
            }}
            type="url"
            placeholder="https://example.com/post/12345"
            className={clsx(
              "w-full px-4 py-3 rounded-lg bg-[#0a0e1a] border text-slate-200",
              "placeholder:text-slate-600 focus:outline-none focus:ring-1",
              "font-mono text-sm transition-colors",
              errors.url
                ? "border-red-500/50 focus:ring-red-500/50 focus:border-red-500"
                : "border-[#1e3a5f] focus:ring-blue-500/50 focus:border-blue-500/50"
            )}
          />
          {detectedPlatform && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1.5 px-2 py-1 rounded-md bg-blue-500/10 border border-blue-500/20">
              <div className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
              <span className="text-xs text-blue-400 font-medium">{detectedPlatform}</span>
            </div>
          )}
        </div>
        {errors.url && (
          <p className="flex items-center gap-1.5 text-xs text-red-400">
            <AlertCircle className="w-3.5 h-3.5" />
            {errors.url.message}
          </p>
        )}
        <p className="text-xs text-slate-500">
          Platform auto-detected. Social media URLs get optimized capture settings.
        </p>
      </div>

      {/* Capture Type */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-slate-300">Capture Type</label>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {captureTypes.map((type) => {
            const isSelected = watch("capture_type") === type.value;
            return (
              <button
                key={type.value}
                type="button"
                onClick={() => setValue("capture_type", type.value as any)}
                className={clsx(
                  "p-3 rounded-lg border text-left transition-all",
                  isSelected
                    ? "bg-blue-600/20 border-blue-500/50 text-blue-300"
                    : "bg-[#0a0e1a] border-[#1e3a5f] text-slate-400 hover:border-[#1e5a8f] hover:text-slate-300"
                )}
              >
                <type.icon className={clsx("w-4 h-4 mb-1.5", isSelected ? "text-blue-400" : "text-slate-500")} />
                <div className="text-sm font-medium">{type.label}</div>
                <div className="text-xs opacity-70 mt-0.5 leading-tight">{type.desc}</div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Advanced Options */}
      <div className="rounded-lg border border-[#1e3a5f] overflow-hidden">
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex items-center justify-between w-full px-4 py-3 text-sm text-slate-400 hover:text-slate-200 hover:bg-white/5 transition-colors"
        >
          <span className="font-medium">Case Information (Optional)</span>
          {showAdvanced ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {showAdvanced && (
          <div className="px-4 pb-4 space-y-4 border-t border-[#1e3a5f]">
            <div className="pt-4 space-y-2">
              <label className="text-sm font-medium text-slate-300">Case Number</label>
              <input
                {...register("case_number")}
                placeholder="e.g., CASE-2024-001"
                className="w-full px-3 py-2 rounded-lg bg-[#0a0e1a] border border-[#1e3a5f] text-slate-200 placeholder:text-slate-600 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500/50 focus:border-blue-500/50"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-300">Case Description</label>
              <textarea
                {...register("case_description")}
                rows={3}
                placeholder="Brief description of the investigation..."
                className="w-full px-3 py-2 rounded-lg bg-[#0a0e1a] border border-[#1e3a5f] text-slate-200 placeholder:text-slate-600 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-blue-500/50 focus:border-blue-500/50"
              />
            </div>
          </div>
        )}
      </div>

      {/* What will be captured */}
      <div className="rounded-lg bg-[#0a0e1a] border border-[#1e3a5f] p-4">
        <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
          Evidence Collection Includes
        </h4>
        <div className="grid grid-cols-2 gap-2 text-xs text-slate-400">
          {[
            "Full page screenshot (PNG)",
            "Rendered DOM + original HTML",
            "All CSS, JS, images",
            "WARC archive format",
            "HTTP headers + TLS cert",
            "DNS resolution records",
            "WHOIS domain info",
            "RFC 3161 timestamp",
            "SHA-256/SHA-512 hashes",
            "Complete forensic log",
            "Chain of custody record",
            "PDF evidence report",
          ].map((item) => (
            <div key={item} className="flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-blue-400 flex-shrink-0" />
              {item}
            </div>
          ))}
        </div>
      </div>

      {/* Error */}
      {mutation.isError && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>Failed to initiate capture. Please try again.</span>
        </div>
      )}

      {/* Submit */}
      <button
        type="submit"
        disabled={mutation.isPending}
        className={clsx(
          "w-full flex items-center justify-center gap-2.5 px-6 py-3.5 rounded-lg",
          "font-semibold text-sm transition-all",
          mutation.isPending
            ? "bg-blue-600/50 text-blue-300 cursor-not-allowed"
            : "bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-600/20 hover:shadow-blue-500/30"
        )}
      >
        {mutation.isPending ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Initiating Forensic Capture...
          </>
        ) : (
          <>
            <Play className="w-4 h-4" />
            Start Evidence Capture
          </>
        )}
      </button>

      <p className="text-center text-xs text-slate-500">
        Evidence will be cryptographically signed and timestamped. Immutable after capture.
      </p>
    </form>
  );
}
