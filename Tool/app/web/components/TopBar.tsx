"use client";
import Link from "next/link";
import { StatusDot } from "./ui";

export function TopBar({ crumbs }: { crumbs?: { label: string; href?: string }[] }) {
  return (
    <div className="bg-white border-b border-uq-border">
      <div className="h-[60px] px-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-[34px] h-[34px] rounded-[9px] bg-uq-symbol grid place-items-center text-white font-display font-extrabold text-[13px]">
            UQ
          </div>
          <div className="leading-tight">
            <div className="font-display font-extrabold text-uq-dark-purple text-[13px]">
              Uniqus · Regulatory Reporting
            </div>
            <div className="text-[10px] text-uq-muted">Agentic AI Platform · SAMA CAR-SA-01</div>
          </div>
          <div className="w-px h-6 bg-uq-border mx-2" />
          <nav className="flex items-center gap-1.5 text-[11px]">
            <Link href="/" className="text-uq-muted hover:text-uq-purple">Report Packs</Link>
            {crumbs?.map((c, i) => (
              <span key={i} className="flex items-center gap-1.5">
                <span className="text-uq-lavender">›</span>
                {c.href
                  ? <Link href={c.href} className="text-uq-muted hover:text-uq-purple">{c.label}</Link>
                  : <span className="text-uq-purple font-semibold">{c.label}</span>}
              </span>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-3">
          <span className="chip bg-ok/12 text-ok"><StatusDot tone="ok" /> Governed</span>
          <div className="flex items-center gap-2">
            <div className="w-[26px] h-[26px] rounded-full bg-uq-symbol" />
            <div className="leading-tight text-right">
              <div className="text-[11px] font-semibold text-uq-ink">Siddharth Sharma</div>
              <div className="text-[9px] text-uq-muted uppercase tracking-wider">Checker · Risk</div>
            </div>
          </div>
        </div>
      </div>
      <div className="h-0.5 bg-uq-bar" />
    </div>
  );
}
