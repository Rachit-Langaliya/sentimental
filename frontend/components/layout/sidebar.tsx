"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  TrendingUp,
  MessageSquare,
  Network,
  FlaskConical,
  Settings,
  LogOut,
  ShieldCheck,
  Radio,
  Cpu,
  Layers,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { clearAuth, getStoredUser } from "@/lib/auth";
import { authApi } from "@/lib/api";

const NAV_MAIN = [
  { href: "/dashboard",  icon: LayoutDashboard, label: "Overview" },
  { href: "/trends",     icon: TrendingUp,      label: "Trends" },
  { href: "/sentiment",  icon: MessageSquare,   label: "Sentiment" },
  { href: "/network",    icon: Network,         label: "Network" },
];

const NAV_ANALYSIS = [
  { href: "/audience",   icon: Users,           label: "Audience",     badge: null },
  { href: "/segments",   icon: Layers,          label: "Segments",     badge: null },
  { href: "/simulation", icon: FlaskConical,    label: "Policy Sim",   badge: "LLM" },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const user = getStoredUser();

  async function handleLogout() {
    try { await authApi.logout(); } catch {}
    clearAuth();
    router.push("/login");
  }

  function NavLink({ href, icon: Icon, label, badge }: {
    href: string; icon: React.ElementType; label: string; badge?: string | null;
  }) {
    const active = pathname === href || pathname.startsWith(href + "/");
    return (
      <Link
        href={href}
        className={cn(
          "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all",
          active
            ? "bg-accent/15 text-accent border border-accent/25"
            : "text-ink-2 hover:bg-surface hover:text-ink"
        )}
      >
        <Icon className={cn("w-4 h-4 flex-shrink-0", active ? "text-accent" : "text-ink-3")} />
        {label}
        {badge && (
          <span className="ml-auto text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-success/20 text-success border border-success/25">
            {badge}
          </span>
        )}
      </Link>
    );
  }

  return (
    <aside className="fixed left-0 top-0 h-screen w-60 bg-[#0A1220] border-r border-bdr flex flex-col z-40">
      {/* Brand */}
      <div className="px-5 py-5 border-b border-bdr">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-accent/20 border border-accent/30 flex items-center justify-center flex-shrink-0">
            <ShieldCheck className="w-4 h-4 text-accent" />
          </div>
          <div>
            <div className="text-sm font-bold text-ink leading-tight">SIH Intelligence</div>
            <div className="text-[10px] text-ink-3 uppercase tracking-widest">Analytics Platform</div>
          </div>
        </div>

        {/* Live indicator */}
        <div className="mt-3 flex items-center gap-2 px-2.5 py-1.5 bg-surface rounded-lg border border-bdr">
          <Radio className="w-3 h-3 text-success animate-pulse" />
          <span className="text-[10px] font-semibold text-ink-2 uppercase tracking-wider">Demo Mode Active</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 overflow-y-auto space-y-4">
        <div className="space-y-0.5">
          <p className="text-[10px] font-bold text-ink-3 uppercase tracking-widest px-2 pb-2">Monitor</p>
          {NAV_MAIN.map((item) => (
            <NavLink key={item.href} {...item} />
          ))}
        </div>

        <div className="space-y-0.5">
          <p className="text-[10px] font-bold text-ink-3 uppercase tracking-widest px-2 pb-2">Analysis</p>
          {NAV_ANALYSIS.map((item) => (
            <NavLink key={item.href} {...item} />
          ))}
        </div>
      </nav>

      {/* Footer */}
      <div className="px-3 py-4 border-t border-bdr space-y-1">
        <Link href="/settings" className={cn(
          "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all",
          pathname === "/settings" ? "bg-accent/15 text-accent" : "text-ink-2 hover:bg-surface hover:text-ink"
        )}>
          <Settings className="w-4 h-4 text-ink-3" />
          Settings
        </Link>
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-ink-2 hover:bg-danger/10 hover:text-danger transition-all"
        >
          <LogOut className="w-4 h-4" />
          Sign out
        </button>
        {user && (
          <div className="mt-2 px-3 py-2 bg-surface rounded-lg border border-bdr">
            <p className="text-xs font-medium text-ink truncate">{user.full_name}</p>
            <p className="text-[10px] text-ink-3 uppercase tracking-wide">{user.role}</p>
          </div>
        )}
      </div>
    </aside>
  );
}
