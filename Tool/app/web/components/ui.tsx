"use client";
import clsx from "clsx";
import Link from "next/link";
import { ChevronRight, Sparkles } from "lucide-react";

export function Panel({ title, eyebrow, actions, children, className }: {
  title?: string; eyebrow?: string; actions?: React.ReactNode;
  children: React.ReactNode; className?: string;
}) {
  return (
    <section className={clsx("panel p-3.5", className)}>
      {(title || actions) && (
        <header className="flex items-center justify-between mb-3">
          <div>
            {eyebrow && <div className="eyebrow mb-0.5">{eyebrow}</div>}
            {title && <h2 className="panel-title">{title}</h2>}
          </div>
          {actions}
        </header>
      )}
      {children}
    </section>
  );
}

export function Badge({ tone = "neutral", children }: {
  tone?: "ok" | "warn" | "crit" | "magenta" | "neutral" | "purple"; children: React.ReactNode;
}) {
  const map: Record<string, string> = {
    ok: "bg-ok/12 text-ok", warn: "bg-warn/15 text-warn2", crit: "bg-crit/12 text-crit",
    magenta: "bg-uq-magenta/12 text-uq-magenta", purple: "bg-uq-purple/10 text-uq-purple",
    neutral: "bg-uq-alt-light text-uq-mid",
  };
  return <span className={clsx("chip", map[tone])}>{children}</span>;
}

export function StatusDot({ tone }: { tone: "ok" | "warn" | "crit" | "live" }) {
  const c = { ok: "bg-ok", warn: "bg-warn", crit: "bg-crit", live: "bg-uq-magenta dot-live" }[tone];
  return <span className={clsx("inline-block w-2 h-2 rounded-full", c)} />;
}

export function Button({ variant = "primary", className, ...props }:
  React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" | "soft" }) {
  const v = {
    primary: "bg-uq-symbol text-white hover:opacity-90",
    ghost: "bg-white border border-uq-border text-uq-purple hover:bg-uq-alt-light",
    soft: "bg-uq-alt-light text-uq-purple hover:bg-uq-light-lavender",
  }[variant];
  return (
    <button {...props} className={clsx(
      "rounded-row px-3 py-1.5 font-display font-bold text-[12px] transition disabled:opacity-40 disabled:cursor-not-allowed",
      v, className)} />
  );
}

const ELEMENT_STATUS: Record<string, { label: string; cls: string }> = {
  draft: { label: "Draft", cls: "bg-uq-alt-light text-uq-mid" },
  edited: { label: "Edited", cls: "bg-uq-blush text-uq-magenta" },
  frozen: { label: "Frozen", cls: "bg-uq-light-lavender text-uq-purple" },
  submitted: { label: "Submitted", cls: "bg-warn/15 text-warn2" },
  certified: { label: "Certified", cls: "bg-ok/12 text-ok" },
  rejected: { label: "Rejected", cls: "bg-crit/12 text-crit" },
  invalidated: { label: "Invalidated", cls: "bg-crit/12 text-crit" },
};

export function StatusPill({ status }: { status: string }) {
  const s = ELEMENT_STATUS[status] ?? { label: status, cls: "bg-uq-alt-light text-uq-mid" };
  return <span className={clsx("chip", s.cls)}>{s.label}</span>;
}

export function NavTile({ href, icon, title, desc }: {
  href: string; icon: React.ReactNode; title: string; desc: string;
}) {
  return (
    <Link href={href}
      className="panel p-3.5 flex items-center gap-3 hover:border-uq-magenta hover:shadow-soft transition group">
      <span className="grid place-items-center w-10 h-10 rounded-row bg-uq-symbol text-white shrink-0">{icon}</span>
      <span className="min-w-0">
        <span className="flex items-center gap-1.5 font-display font-extrabold text-[14px] text-uq-dark-purple tracking-tight">
          {title}<ChevronRight className="w-3.5 h-3.5 text-uq-magenta group-hover:translate-x-0.5 transition" strokeWidth={2.5} />
        </span>
        <span className="block text-[11px] text-uq-muted leading-snug">{desc}</span>
      </span>
    </Link>
  );
}

export function AiBadge({ label = "AI" }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-1 text-[9.5px] bg-uq-purple/8 text-uq-purple border border-uq-purple/20 rounded-full px-2 py-0.5 font-display font-bold tracking-wide">
      <Sparkles className="w-2.5 h-2.5" strokeWidth={2} /> {label}
    </span>
  );
}

export function Stat({ label, value, sub, tone }: {
  label: string; value: React.ReactNode; sub?: React.ReactNode; tone?: "ok" | "crit" | "magenta";
}) {
  const vc = tone === "ok" ? "text-ok" : tone === "crit" ? "text-crit"
    : tone === "magenta" ? "text-uq-magenta" : "text-uq-dark-purple";
  return (
    <div className="panel p-3 flex flex-col gap-1">
      <div className="kpi-label">{label}</div>
      <div className={clsx("font-display font-extrabold tracking-tight num", vc)} style={{ fontSize: 24 }}>{value}</div>
      {sub && <div className="text-[10.5px] text-uq-muted">{sub}</div>}
    </div>
  );
}
