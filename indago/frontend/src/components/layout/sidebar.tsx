"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Shield, Search, List, BarChart2, Clock, Settings,
  LogOut, User, FileText, Hash, GitBranch, ChevronRight
} from "lucide-react";
import { clsx } from "clsx";
import { useAuthStore } from "@/lib/store";

const navItems = [
  { href: "/dashboard", icon: BarChart2, label: "Dashboard" },
  { href: "/capture", icon: Search, label: "New Capture" },
  { href: "/captures", icon: List, label: "Evidence Library" },
  { href: "/schedules", icon: Clock, label: "Schedules" },
  { href: "/compare", icon: GitBranch, label: "Compare Evidence" },
  { href: "/reports", icon: FileText, label: "Reports" },
  { href: "/audit", icon: Hash, label: "Audit Trail" },
];

const bottomItems = [
  { href: "/settings", icon: Settings, label: "Settings" },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();

  return (
    <aside className="fixed left-0 top-0 bottom-0 w-64 bg-[#0d1526] border-r border-[#1e3a5f] flex flex-col z-40">
      {/* Logo */}
      <div className="p-6 border-b border-[#1e3a5f]">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-white font-bold text-lg leading-none">INDAGO</h1>
            <p className="text-[#00a8ff] text-xs mt-0.5 font-medium">Evidence Capture</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 overflow-y-auto">
        <div className="space-y-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <Link
                key={item.href}
                href={item.href}
                className={clsx(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all group",
                  isActive
                    ? "bg-blue-600/20 text-blue-400 border border-blue-500/30"
                    : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
                )}
              >
                <item.icon className={clsx(
                  "w-4.5 h-4.5 transition-colors",
                  isActive ? "text-blue-400" : "text-slate-500 group-hover:text-slate-300"
                )} />
                <span className="text-sm font-medium">{item.label}</span>
                {isActive && <ChevronRight className="w-3.5 h-3.5 ml-auto text-blue-400" />}
              </Link>
            );
          })}
        </div>

        {/* Standards badge */}
        <div className="mt-6 p-3 rounded-lg bg-[#0a0e1a] border border-[#1e3a5f]">
          <p className="text-xs text-slate-500 font-medium mb-1.5">Compliance Standards</p>
          <div className="flex flex-wrap gap-1">
            {["ISO 27037", "RFC 3227", "RFC 3161", "NIST"].map((std) => (
              <span key={std} className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                {std}
              </span>
            ))}
          </div>
        </div>
      </nav>

      {/* Bottom items */}
      <div className="p-4 border-t border-[#1e3a5f]">
        {bottomItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-white/5 transition-all mb-1"
          >
            <item.icon className="w-4.5 h-4.5" />
            <span className="text-sm font-medium">{item.label}</span>
          </Link>
        ))}

        {/* User profile */}
        {user && (
          <div className="mt-2 p-3 rounded-lg bg-[#0a0e1a] border border-[#1e3a5f]">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-8 h-8 rounded-full bg-blue-600/30 border border-blue-500/30 flex items-center justify-center">
                <User className="w-4 h-4 text-blue-400" />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-medium text-slate-200 truncate">{user.full_name}</p>
                <p className="text-[10px] text-slate-500 capitalize">{user.role}</p>
              </div>
            </div>
            <button
              onClick={logout}
              className="flex items-center gap-2 w-full px-2 py-1.5 text-xs text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors"
            >
              <LogOut className="w-3.5 h-3.5" />
              Sign out
            </button>
          </div>
        )}
      </div>
    </aside>
  );
}
