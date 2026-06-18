"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Database, FileStack } from "lucide-react";
import { Badge, Button, NavTile, Panel, Stat, StatusDot } from "@/components/ui";
import { api, endpoints, type Instance, type PlatformOverview } from "@/lib/api";

type CycleStatus = { label: string; tone: any; desc: string };

function cycleStatus(i: PlatformOverview["instances"][number]): CycleStatus {
  if (i.report_status === "Signed Off")
    return { label: "Signed Off", tone: "ok", desc: "Approved for this cycle" };
  if (i.failing_rules > 0 || i.open_remediations > 0 || i.buffer_status)
    return {
      label: "Needs Attention", tone: "crit",
      desc: i.failing_rules > 0 ? `${i.failing_rules} exception${i.failing_rules > 1 ? "s" : ""} to resolve`
        : i.open_remediations > 0 ? "Remediation pending review" : "Capital buffer breach — review required",
    };
  if (i.blocking_domains?.length)
    return { label: "In Progress", tone: "purple", desc: "Data preparation underway, pending certification" };
  if (i.report_readiness > 0 && i.report_readiness < 100)
    return { label: "Ready for Sign-off", tone: "warn", desc: "Schedules reviewed, pending final sign-off" };
  return { label: "Under Review", tone: "neutral", desc: "Draft prepared, ready for review" };
}

export default function Overview() {
  const qc = useQueryClient();
  const router = useRouter();
  const { data } = useQuery({ queryKey: ["overview"], queryFn: () => api.get<PlatformOverview>(endpoints.overview), refetchInterval: 8000 });
  const [open, setOpen] = useState(false);
  const [bank, setBank] = useState("Tadawul National Bank (demo)");
  const [period, setPeriod] = useState("Q1 2026");
  const [end, setEnd] = useState("2026-03-31");

  const create = useMutation({
    mutationFn: () => api.post<Instance>(endpoints.instances, { bank_name: bank, period_label: period, period_end: end, actor: "maker" }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["overview"] }); setOpen(false); },
  });

  const instances = data?.instances ?? [];
  const statuses = instances.map(cycleStatus);
  const count = (label: string) => statuses.filter((s) => s.label === label).length;

  return (
    <div className="h-[calc(100vh-52px)] overflow-hidden flex flex-col p-6 gap-3.5 max-w-[1400px] mx-auto w-full">

      {/* header */}
      <div className="flex items-end justify-between shrink-0">
        <div>
          <h1 className="font-display font-extrabold text-uq-dark-purple text-[22px] tracking-tight">Regulatory Reporting</h1>
          <p className="text-[12.5px] text-uq-muted">Command center for governed regulatory reporting — from data certification to final sign-off.</p>
        </div>
        <Button onClick={() => setOpen((v) => !v)}>+ New reporting cycle</Button>
      </div>

      {open && (
        <Panel eyebrow="New" title="Open a reporting cycle" className="shrink-0">
          <div className="grid grid-cols-4 gap-2.5 items-end text-[12px]">
            <label className="flex flex-col gap-1 col-span-2"><span className="kpi-label">Bank legal name</span>
              <input value={bank} onChange={(e) => setBank(e.target.value)} className="rounded-row border border-uq-border px-2.5 py-1.5" /></label>
            <label className="flex flex-col gap-1"><span className="kpi-label">Period</span>
              <input value={period} onChange={(e) => setPeriod(e.target.value)} className="rounded-row border border-uq-border px-2.5 py-1.5" /></label>
            <label className="flex flex-col gap-1"><span className="kpi-label">Period end</span>
              <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} className="rounded-row border border-uq-border px-2.5 py-1.5" /></label>
            <Button onClick={() => create.mutate()} disabled={create.isPending} className="col-span-1">{create.isPending ? "Opening…" : "Open cycle"}</Button>
          </div>
        </Panel>
      )}

      {/* executive KPI strip */}
      <div className="grid grid-cols-5 gap-3 shrink-0">
        <Stat label="Active Reporting Cycles" value={data ? instances.length : "—"} sub={`${data?.metrics.active_packs ?? 0} live pack`} />
        <Stat label="Ready for Review" value={data ? count("Under Review") : "—"} sub="draft prepared" />
        <Stat label="Awaiting Sign-off" value={data ? count("Ready for Sign-off") : "—"} sub="pending final approval" tone={count("Ready for Sign-off") ? "magenta" : undefined} />
        <Stat label="Signed Off" value={data ? count("Signed Off") : "—"} sub="this cycle" tone="ok" />
        <Stat label="Requiring Attention" value={data ? count("Needs Attention") : "—"} sub="exceptions to resolve" tone={count("Needs Attention") ? "crit" : "ok"} />
      </div>

      {/* Regulatory Report Portfolio — centred, full-width, prominent */}
      <Panel eyebrow="Reporting portfolio" title="Regulatory Report Portfolio" className="shrink-0">
        <div className="grid grid-cols-[repeat(auto-fill,minmax(200px,1fr))] gap-2.5">
          {data?.packs.map((p) => (
            <div key={p.code} className="rounded-row border border-uq-border p-2.5 flex items-center justify-between gap-2">
              <div>
                <div className="font-display font-bold text-[12px] text-uq-dark-purple leading-tight">{p.name}</div>
                <div className="text-[10px] text-uq-muted mt-0.5">{p.regulator} · {p.frequency} · <span className="font-mono">{p.code}</span></div>
              </div>
              {p.status === "active"
                ? <Badge tone="ok"><StatusDot tone="ok" /> Active</Badge>
                : <Badge tone="neutral">Planned</Badge>}
            </div>
          ))}
        </div>
      </Panel>

      {/* primary pathways */}
      <div className="grid grid-cols-2 gap-3 shrink-0">
        <NavTile href="/data-foundation" icon={<Database className="w-5 h-5" strokeWidth={2} />}
          title="Data Foundation" desc="Governed reporting data — ingestion, validation, controls and sign-off" />
        <NavTile href="/report-pack" icon={<FileStack className="w-5 h-5" strokeWidth={2} />}
          title="Report Pack" desc="Review-ready packs — narratives, exceptions and report outputs" />
      </div>

      {/* active reporting cycles */}
      <Panel eyebrow="Reporting cycle status" title="Active reporting cycles" className="flex flex-col flex-1 min-h-0">
        <div className="overflow-auto min-h-0">
          <table className="w-full text-[12px]">
            <thead className="sticky top-0 bg-white"><tr className="text-left text-uq-purple">
              {["Report", "Period", "Entity", "Status", ""].map((h) => (
                <th key={h} className="font-display font-extrabold uppercase text-[9px] tracking-wider pb-2 border-b border-uq-border">{h}</th>))}
            </tr></thead>
            <tbody>
              {instances.map((i, idx) => {
                const s = statuses[idx];
                return (
                  <tr key={i.id} className="border-b border-uq-border/60 hover:bg-uq-alt-light cursor-pointer"
                    onClick={() => router.push(`/report-pack/car/${i.id}`)}>
                    <td className="py-2.5">
                      <div className="font-semibold text-uq-ink">Capital Adequacy Return</div>
                      <div className="font-mono text-[9px] text-uq-lavender">{i.pack}</div>
                    </td>
                    <td className="font-semibold text-uq-ink">{i.period_label}</td>
                    <td className="text-uq-muted text-[11px]">{i.bank_name}</td>
                    <td>
                      <Badge tone={s.tone}>{s.label}</Badge>
                      <div className="text-[10px] text-uq-muted mt-0.5">{s.desc}</div>
                    </td>
                    <td className="text-right"><Button variant="ghost">Open ›</Button></td>
                  </tr>
                );
              })}
              {data && instances.length === 0 && <tr><td colSpan={5} className="py-8 text-center text-uq-muted">No reporting cycles yet.</td></tr>}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
