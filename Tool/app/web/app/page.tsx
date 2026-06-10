"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Badge, Button, Panel, Stat, StatusDot } from "@/components/ui";
import { api, endpoints, type Instance, type PlatformOverview } from "@/lib/api";

const statusTone: Record<string, any> = {
  Draft: "neutral", Exception: "crit", Remediation: "warn", "Signed Off": "ok",
};

export default function Overview() {
  const qc = useQueryClient();
  const router = useRouter();
  const { data } = useQuery({ queryKey: ["overview"], queryFn: () => api.get<PlatformOverview>(endpoints.overview), refetchInterval: 8000 });
  const m = data?.metrics;
  const [open, setOpen] = useState(false);
  const [bank, setBank] = useState("Tadawul National Bank (demo)");
  const [period, setPeriod] = useState("Q1 2026");
  const [end, setEnd] = useState("2026-03-31");

  const create = useMutation({
    mutationFn: () => api.post<Instance>(endpoints.instances, { bank_name: bank, period_label: period, period_end: end, actor: "maker" }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["overview"] }); setOpen(false); },
  });

  return (
    <div className="p-6 max-w-[1400px] mx-auto">
      <div className="flex items-end justify-between mb-4">
        <div>
          <div className="eyebrow mb-1">Platform Command Center</div>
          <h1 className="font-display font-extrabold text-uq-dark-purple text-[22px] tracking-tight">Regulatory Reporting Overview</h1>
          <p className="text-[12px] text-uq-muted">Cross-pack health, instances and readiness. Report-specific detail lives inside each Report Pack.</p>
        </div>
        <Button onClick={() => setOpen((v) => !v)}>+ New report instance</Button>
      </div>

      {/* global KPI strip */}
      <div className="grid grid-cols-6 gap-3 mb-4">
        <Stat label="Active Reports" value={m?.active_reports ?? "—"} sub={`${m?.active_packs ?? 0} active pack`} />
        <Stat label="Uncertified Data" value={m?.uncertified_data ?? "—"} sub="data gate not met" tone={m && m.uncertified_data ? "crit" : "ok"} />
        <Stat label="In Remediation" value={m?.in_remediation ?? "—"} sub="exceptions open" tone={m && m.in_remediation ? "magenta" : "ok"} />
        <Stat label="Ready for Preview" value={m?.ready_for_preview ?? "—"} sub="clean, awaiting sign-off" />
        <Stat label="Signed Off" value={m?.signed_off ?? "—"} sub="this cycle" tone="ok" />
        <Stat label="Source Health" value={data ? `${data.source_health.connected}/${data.source_health.used_in_car}` : "—"}
          sub={`${data?.source_health.degraded ?? 0} degraded`} tone={data && data.source_health.degraded ? "crit" : "ok"} />
      </div>

      {open && (
        <Panel eyebrow="New" title="Create report instance" className="mb-4">
          <div className="grid grid-cols-4 gap-2.5 items-end text-[12px]">
            <label className="flex flex-col gap-1 col-span-2"><span className="kpi-label">Bank legal name</span>
              <input value={bank} onChange={(e) => setBank(e.target.value)} className="rounded-row border border-uq-border px-2.5 py-1.5" /></label>
            <label className="flex flex-col gap-1"><span className="kpi-label">Period</span>
              <input value={period} onChange={(e) => setPeriod(e.target.value)} className="rounded-row border border-uq-border px-2.5 py-1.5" /></label>
            <label className="flex flex-col gap-1"><span className="kpi-label">Period end</span>
              <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} className="rounded-row border border-uq-border px-2.5 py-1.5" /></label>
            <Button onClick={() => create.mutate()} disabled={create.isPending} className="col-span-1">{create.isPending ? "Creating…" : "Create"}</Button>
          </div>
        </Panel>
      )}

      <div className="grid grid-cols-[1fr_360px] gap-4 items-start">
        {/* instances */}
        <Panel eyebrow="Report Instances" title="Active instances · data readiness vs report readiness">
          <table className="w-full text-[12px]">
            <thead><tr className="text-left text-uq-purple">
              {["Pack", "Period", "Report status", "Data", "Report", "Issues", ""].map((h) => (
                <th key={h} className="font-display font-extrabold uppercase text-[9px] tracking-wider pb-2 border-b border-uq-border">{h}</th>))}
            </tr></thead>
            <tbody>
              {data?.instances.map((i) => (
                <tr key={i.id} className="border-b border-uq-border/60 hover:bg-uq-alt-light cursor-pointer"
                  onClick={() => router.push(`/report-pack/car/${i.id}`)}>
                  <td className="py-2.5"><span className="font-mono text-[10px] text-uq-purple">{i.pack}</span></td>
                  <td className="font-semibold text-uq-ink">{i.period_label}</td>
                  <td><Badge tone={statusTone[i.report_status] ?? "neutral"}>{i.report_status}</Badge></td>
                  <td><Readiness pct={i.data_readiness} /></td>
                  <td><Readiness pct={i.report_readiness} /></td>
                  <td>{i.failing_rules > 0 ? <span className="text-crit text-[11px] font-semibold">{i.failing_rules} exc.</span> : <span className="text-ok text-[11px]">clean</span>}</td>
                  <td className="text-right"><Button variant="ghost">Open ›</Button></td>
                </tr>
              ))}
              {data && data.instances.length === 0 && <tr><td colSpan={7} className="py-8 text-center text-uq-muted">No instances yet.</td></tr>}
            </tbody>
          </table>
        </Panel>

        {/* pack catalogue */}
        <Panel eyebrow="Catalogue" title="Report packs">
          <div className="flex flex-col gap-2">
            {data?.packs.map((p) => (
              <div key={p.code} className="rounded-row border border-uq-border p-2.5 flex items-center justify-between">
                <div>
                  <div className="font-display font-bold text-[12px] text-uq-dark-purple">{p.name}</div>
                  <div className="text-[10px] text-uq-muted">{p.regulator} · {p.frequency} · {p.code}</div>
                </div>
                {p.status === "active"
                  ? <Badge tone="ok"><StatusDot tone="ok" /> Active</Badge>
                  : <Badge tone="neutral">Planned</Badge>}
              </div>
            ))}
          </div>
          <div className="mt-2 text-[10px] text-uq-muted">The canonical Data Layer is built to feed every pack; CAR-SA-01 is the first live pack.</div>
        </Panel>
      </div>

      {/* source health strip */}
      <Panel eyebrow="Source connections" title="Enterprise source systems" className="mt-4">
        <div className="grid grid-cols-4 gap-2">
          {data?.sources.filter((s) => s.used_in_car).map((s) => (
            <div key={s.code} className="rounded-row border border-uq-border p-2.5">
              <div className="flex items-center justify-between">
                <span className="font-display font-bold text-[11.5px] text-uq-dark-purple">{s.name}</span>
                <StatusDot tone={s.status === "connected" ? "ok" : "crit"} />
              </div>
              <div className="text-[10px] text-uq-muted">{s.vendor} · {s.car_elements} CAR elements</div>
            </div>
          ))}
        </div>
      </Panel>

      {/* readiness / blockers */}
      <Panel eyebrow="Readiness" title="Blockers summary" className="mt-4">
        <div className="flex flex-wrap gap-2">
          {data?.instances.flatMap((i) => [
            ...(i.blocking_domains?.length ? [{ k: `${i.period_label}: certify ${i.blocking_domains.join(", ")}`, t: "warn" }] : []),
            ...(i.failing_rules > 0 ? [{ k: `${i.period_label}: ${i.failing_rules} validation failure(s)`, t: "crit" }] : []),
            ...(i.open_remediations > 0 ? [{ k: `${i.period_label}: ${i.open_remediations} remediation pending`, t: "magenta" }] : []),
          ]).map((b, idx) => <Badge key={idx} tone={b.t as any}>{b.k}</Badge>)}
          {data && data.instances.every((i) => !i.blocking_domains?.length && !i.failing_rules && !i.open_remediations) &&
            <span className="text-[12px] text-ok">All instances clear — no platform blockers.</span>}
        </div>
      </Panel>
    </div>
  );
}

function Readiness({ pct }: { pct: number }) {
  const tone = pct >= 100 ? "bg-ok" : pct >= 50 ? "bg-warn" : "bg-crit";
  return (
    <div className="flex items-center gap-1.5">
      <div className="w-16 h-[5px] rounded-pill bg-uq-light-lavender overflow-hidden">
        <div className={`h-full ${tone}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] text-uq-muted num">{pct}%</span>
    </div>
  );
}
