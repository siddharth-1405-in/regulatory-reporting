"use client";
import { Database, FileStack, LayoutDashboard, Settings } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import { Role, useRole } from "./RoleContext";

const NAV = [
  { href: "/", label: "Overview", icon: LayoutDashboard, match: (p: string) => p === "/" },
  { href: "/data-foundation", label: "Data Foundation", icon: Database, match: (p: string) => p.startsWith("/data-foundation") || p.startsWith("/data-layer") },
  { href: "/report-pack", label: "Report Pack", icon: FileStack, match: (p: string) => p.startsWith("/report-pack") || p.startsWith("/instances") },
  { href: "/admin", label: "Admin", icon: Settings, match: (p: string) => p.startsWith("/admin") },
];

const ROLES: Role[] = ["Maker", "Checker", "Admin"];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() || "/";
  const { role, setRole } = useRole();
  const active = NAV.find((n) => n.match(pathname));

  return (
    <div className="min-h-screen grid grid-cols-[208px_1fr]">
      {/* sidebar */}
      <aside className="bg-uq-dark-purple text-white flex flex-col">
        <div className="h-[60px] flex items-center gap-2.5 px-4 border-b border-white/10">
          <div className="w-[30px] h-[30px] rounded-[8px] bg-uq-symbol grid place-items-center font-display font-extrabold text-[12px]">UQ</div>
          <div className="leading-tight">
            <div className="font-display font-extrabold text-[12px]">Uniqus</div>
            <div className="text-[9px] text-uq-lavender uppercase tracking-wider">Reg Reporting</div>
          </div>
        </div>
        <nav className="flex flex-col gap-0.5 p-2.5 flex-1">
          {NAV.map((n) => {
            const on = active?.href === n.href;
            const Icon = n.icon;
            return (
              <Link key={n.href} href={n.href}
                className={clsx("flex items-center gap-2.5 rounded-row px-3 py-2 text-[12.5px] font-medium transition",
                  on ? "bg-white/12 text-white font-semibold" : "text-uq-lavender hover:bg-white/5 hover:text-white")}>
                <Icon size={15} strokeWidth={2} />
                {n.label}
              </Link>
            );
          })}
        </nav>
        <div className="p-3 border-t border-white/10 text-[9px] text-uq-lavender">
          Governed agentic platform · CAR-SA-01
        </div>
      </aside>

      {/* main column */}
      <div className="flex flex-col min-w-0">
        {/* top bar */}
        <header className="h-[52px] bg-white border-b border-uq-border flex items-center justify-between px-6 sticky top-0 z-20">
          <div className="flex items-center gap-2 text-[12px]">
            <span className="text-uq-muted">Platform</span>
            <span className="text-uq-lavender">›</span>
            <span className="font-display font-bold text-uq-purple">{active?.label ?? "Overview"}</span>
          </div>
          <div className="flex items-center gap-4">
            {/* role switcher */}
            <div className="flex items-center gap-1.5">
              <span className="kpi-label">Acting as</span>
              <div className="flex bg-uq-alt-light rounded-pill p-0.5">
                {ROLES.map((r) => (
                  <button key={r} onClick={() => setRole(r)}
                    className={clsx("px-2.5 py-1 rounded-pill text-[10.5px] font-display font-bold transition",
                      role === r ? "bg-uq-symbol text-white" : "text-uq-mid hover:text-uq-purple")}>
                    {r}
                  </button>
                ))}
              </div>
            </div>
            <div className="w-px h-6 bg-uq-border" />
            <div className="flex items-center gap-2">
              <div className="w-[26px] h-[26px] rounded-full bg-uq-symbol" />
              <div className="leading-tight text-right">
                <div className="text-[11px] font-semibold text-uq-ink">Siddharth Sharma</div>
                <div className="text-[9px] text-uq-muted uppercase tracking-wider">{role}</div>
              </div>
            </div>
          </div>
        </header>
        <div className="h-0.5 bg-uq-bar" />
        <main className="flex-1 min-w-0">{children}</main>
      </div>
    </div>
  );
}
