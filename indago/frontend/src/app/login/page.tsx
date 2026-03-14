"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation } from "@tanstack/react-query";
import { Shield, Lock, User, AlertCircle, Loader2, Eye, EyeOff } from "lucide-react";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { useRouter } from "next/navigation";
import { clsx } from "clsx";

const schema = z.object({
  username: z.string().min(1, "Username required"),
  password: z.string().min(1, "Password required"),
});

type FormData = z.infer<typeof schema>;

export default function LoginPage() {
  const router = useRouter();
  const { setAuth } = useAuthStore();
  const [showPassword, setShowPassword] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const mutation = useMutation({
    mutationFn: ({ username, password }: FormData) => authApi.login(username, password),
    onSuccess: async (response) => {
      const { access_token, user_id, username, role } = response.data;
      const meRes = await authApi.me();
      setAuth(access_token, meRes.data);
      router.push("/dashboard");
    },
  });

  return (
    <div className="min-h-screen bg-[#0a0e1a] bg-grid flex items-center justify-center p-4">
      {/* Background glow */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl" />
      </div>

      <div className="w-full max-w-md relative z-10">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-blue-600/20 border border-blue-500/30 mb-4">
            <Shield className="w-8 h-8 text-blue-400" />
          </div>
          <h1 className="text-3xl font-bold text-white">INDAGO</h1>
          <p className="text-[#00a8ff] text-sm mt-1 font-medium">Digital Evidence Preservation Platform</p>
        </div>

        {/* Card */}
        <div className="forensic-card p-8">
          <h2 className="text-lg font-semibold text-slate-200 mb-6">Sign In to Continue</h2>

          <form onSubmit={handleSubmit((d) => mutation.mutate(d))} className="space-y-4">
            {/* Username */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-400 flex items-center gap-1.5">
                <User className="w-3.5 h-3.5" />
                Username
              </label>
              <input
                {...register("username")}
                autoComplete="username"
                className={clsx(
                  "w-full px-3.5 py-2.5 rounded-lg bg-[#0a0e1a] border text-slate-200 text-sm",
                  "placeholder:text-slate-600 focus:outline-none focus:ring-1 transition-colors",
                  errors.username
                    ? "border-red-500/50 focus:ring-red-500/50"
                    : "border-[#1e3a5f] focus:ring-blue-500/50 focus:border-blue-500/50"
                )}
                placeholder="investigator"
              />
              {errors.username && (
                <p className="text-xs text-red-400 flex items-center gap-1">
                  <AlertCircle className="w-3 h-3" />
                  {errors.username.message}
                </p>
              )}
            </div>

            {/* Password */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-400 flex items-center gap-1.5">
                <Lock className="w-3.5 h-3.5" />
                Password
              </label>
              <div className="relative">
                <input
                  {...register("password")}
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  className={clsx(
                    "w-full px-3.5 py-2.5 pr-10 rounded-lg bg-[#0a0e1a] border text-slate-200 text-sm",
                    "placeholder:text-slate-600 focus:outline-none focus:ring-1 transition-colors",
                    errors.password
                      ? "border-red-500/50 focus:ring-red-500/50"
                      : "border-[#1e3a5f] focus:ring-blue-500/50 focus:border-blue-500/50"
                  )}
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {errors.password && (
                <p className="text-xs text-red-400 flex items-center gap-1">
                  <AlertCircle className="w-3 h-3" />
                  {errors.password.message}
                </p>
              )}
            </div>

            {/* Error */}
            {mutation.isError && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
                <p className="text-xs text-red-400">Invalid credentials. Please try again.</p>
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={mutation.isPending}
              className={clsx(
                "w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg font-semibold text-sm transition-all mt-2",
                mutation.isPending
                  ? "bg-blue-600/50 text-blue-300 cursor-not-allowed"
                  : "bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-600/20"
              )}
            >
              {mutation.isPending ? (
                <><Loader2 className="w-4 h-4 animate-spin" /> Signing in...</>
              ) : (
                <><Shield className="w-4 h-4" /> Sign In Securely</>
              )}
            </button>
          </form>
        </div>

        {/* Standards footer */}
        <p className="text-center text-xs text-slate-600 mt-6">
          ISO/IEC 27037 · RFC 3227 · RFC 3161 · NIST Digital Forensics
        </p>
      </div>
    </div>
  );
}
