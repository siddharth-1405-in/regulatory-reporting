"use client";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useRole } from "@/components/RoleContext";
import { Badge, Panel } from "@/components/ui";
import { api, endpoints, type Instance, type Pack } from "@/lib/api";

const SUB = [
  ["sources", "Source Systems"], ["packs", "Pack Registry"], ["registry", "Canonical Elements"],
  ["ownership", "Ownership Matrix"], ["params", "Parameters"], ["prompt", "Prompt / Model"],
  ["change", "Regulatory Change"], ["roles", "Roles & Permissions"], ["audit", "Audit Trail"],
] as const;

export default function Admin() {
  const { role } = useRole();
  const [sub, setSub] = useState("packs");
  const ro = role !== "Admin";

  return (
    <div className="p-6 max-w-[1400px] mx-auto">
      <div className="flex items-end justify-between mb-4">
        <div>
          <div className="eyebrow mb-1">Configuration</div>
          <h1 className="font-display font-extrabold text-uq-dark-purple text-[22px] tracking-tight">Admin</h1>
          <p className="text-[12px] text-uq-muted">Shared configuration — registries, ownership, parameters, model governance, regulatory change. No operational workflow here.</p>
        </div>
        {ro && <Badge tone="warn">Read-only — switch to Admin to edit</Badge>}
      </div>

      <div className="flex gap-1 mb-4 border-b border-uq-border">
        {SUB.map(([k, l]) => (
          <button key={k} onClick={() => setSub(k)}
            className={`px-3 py-2 text-[12px] font-display font-bold border-b-2 -mb-px ${sub === k ? "border-uq-magenta text-uq-dark-purple" : "border-transparent text-uq-muted hover:text-uq-purple"}`}>{l}</button>
        ))}
      </div>

      {sub === "sources" && <Sources />}
      {sub === "packs" && <Packs />}
      {sub === "registry" && <Registry />}
      {sub === "ownership" && <Ownership />}
      {sub === "params" && <Params />}
      {sub === "prompt" && <PromptModel />}
      {sub === "change" && <Change />}
      {sub === "roles" && <Roles />}
      {sub === "audit" && <Audit />}
    </div>
  );
}

function Sources() {
  const { data = [] } = useQuery({ queryKey: ["sources"], queryFn: () => api.get<any[]>(endpoints.sources) });
  return (
    <Panel eyebrow="Connections" title="Source system configuration">
      <table className="w-full text-[12px]">
        <thead><tr className="text-left text-uq-purple">{["System", "Vendor", "Category", "Status", "CAR", "Coverage", "Steward"].map((h) => <th key={h} className="font-display font-extrabold uppercase text-[9px] tracking-wider pb-2 border-b border-uq-border">{h}</th>)}</tr></thead>
        <tbody>{data.map((s) => (
          <tr key={s.code} className="border-b border-uq-border/50">
            <td className="py-2 font-semibold text-uq-ink">{s.name}</td><td className="text-uq-mid">{s.vendor}</td>
            <td className="text-uq-muted">{s.category}</td>
            <td><Badge tone={s.status === "connected" ? "ok" : "neutral"}>{s.status}</Badge></td>
            <td>{s.used_in_car ? <Badge tone="purple">{s.car_elements}</Badge> : <span className="text-uq-lavender">—</span>}</td>
            <td className="text-uq-muted text-[10px] max-w-[260px]">{s.coverage}</td>
            <td className="text-uq-muted text-[10px]">{s.steward}</td>
          </tr>))}</tbody>
      </table>
    </Panel>
  );
}

const ROLE_MATRIX = [
  ["Edit / override data values", "✓", "—", "✓"],
  ["Freeze & submit for sign-off", "✓", "—", "✓"],
  ["Edit rule parameters", "✓", "—", "✓"],
  ["Approve / reject data certification", "—", "✓", "✓"],
  ["Decide exceptions (approve remediation)", "—", "✓", "✓"],
  ["Schedule & summary sign-off", "—", "✓", "✓"],
  ["Configure sources / parameters", "—", "—", "✓"],
];
function Roles() {
  return (
    <Panel eyebrow="Governance" title="Roles & permissions">
      <p className="text-[11px] text-uq-muted mb-3">Maker-checker separation is enforced server-side; the top-bar role switcher sets the acting role. Agents are advisory and never certify, sign off, export or mutate state without a Checker.</p>
      <table className="w-full text-[12px]">
        <thead><tr className="text-left text-uq-purple">{["Capability", "Maker", "Checker", "Admin"].map((h) => <th key={h} className="font-display font-extrabold uppercase text-[9px] tracking-wider pb-2 border-b border-uq-border">{h}</th>)}</tr></thead>
        <tbody>{ROLE_MATRIX.map((r) => (
          <tr key={r[0]} className="border-b border-uq-border/50">
            <td className="py-2 text-uq-ink">{r[0]}</td>
            {r.slice(1).map((c, i) => <td key={i} className={`py-2 font-bold ${c === "✓" ? "text-ok" : "text-uq-lavender"}`}>{c}</td>)}
          </tr>))}</tbody>
      </table>
    </Panel>
  );
}

function Audit() {
  const { data: instances = [] } = useQuery({ queryKey: ["instances"], queryFn: () => api.get<any[]>(endpoints.instances) });
  const id = instances[0]?.id;
  const { data = [] } = useQuery({ queryKey: ["audit", id], enabled: !!id, queryFn: () => api.get<any[]>(endpoints.audit(id!)) });
  return (
    <Panel eyebrow="Immutable trail" title="Audit log" actions={<Badge tone="purple">{data.length} events</Badge>}>
      <div className="overflow-auto max-h-[560px]">
        <table className="w-full text-[11px]"><tbody>
          {data.map((a, i) => (
            <tr key={i} className="border-b border-uq-border/50">
              <td className="py-1.5 text-uq-muted whitespace-nowrap font-mono text-[9px]">{new Date(a.ts).toLocaleString()}</td>
              <td className="py-1.5"><span className="font-display font-bold text-uq-purple text-[10px] uppercase tracking-wider">{a.action}</span></td>
              <td className="py-1.5 text-uq-mid">{a.entity_type} {a.entity_id}</td>
              <td className="py-1.5 text-right text-uq-muted">{a.actor}</td>
            </tr>))}
        </tbody></table>
      </div>
    </Panel>
  );
}

function Packs() {
  const { data = [] } = useQuery({ queryKey: ["packs"], queryFn: () => api.get<Pack[]>(endpoints.packs) });
  return (
    <Panel eyebrow="Registry" title="Report pack registry">
      <table className="w-full text-[12px]">
        <thead><tr className="text-left text-uq-purple">{["Code", "Name", "Regulator", "Frequency", "Schedules", "Status"].map((h) => <th key={h} className="font-display font-extrabold uppercase text-[9px] tracking-wider pb-2 border-b border-uq-border">{h}</th>)}</tr></thead>
        <tbody>{data.map((p) => (
          <tr key={p.code} className="border-b border-uq-border/50">
            <td className="py-2 font-mono text-[10px] text-uq-purple">{p.code}</td><td className="text-uq-ink">{p.name}</td>
            <td className="text-uq-mid">{p.regulator}</td><td className="text-uq-mid">{p.frequency}</td><td className="num">{p.schedules}</td>
            <td><Badge tone={p.status === "active" ? "ok" : "neutral"}>{p.status}</Badge></td>
          </tr>))}</tbody>
      </table>
    </Panel>
  );
}

function Registry() {
  const { data } = useQuery({ queryKey: ["registry"], queryFn: () => api.get<any>("/registry") });
  const sheets = data?.sheets ?? {};
  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-4 gap-3">
        {Object.entries(sheets).map(([s, els]: any) => (
          <div key={s} className="panel p-3"><div className="kpi-label">{s}</div><div className="font-display font-extrabold text-uq-dark-purple text-[22px] num">{els.length}</div><div className="text-[10px] text-uq-muted">elements</div></div>
        ))}
      </div>
      <Panel eyebrow="Canonical model" title="Element registry" actions={<Badge tone="purple">{data?.required_domains?.join(" · ")}</Badge>}>
        <div className="overflow-auto max-h-[440px]">
          <table className="w-full text-[11px]"><tbody>
            {Object.values(sheets).flat().map((e: any) => (
              <tr key={e.element_code} className="border-b border-uq-border/40">
                <td className="py-1 font-mono text-[9px] text-uq-purple">{e.element_code}</td>
                <td className="py-1 text-uq-ink">{e.label}</td>
                <td className="py-1 text-uq-muted text-[10px]">{e.source_domain}</td>
                <td className="py-1"><Badge tone={e.is_input ? "neutral" : "magenta"}>{e.source_type}</Badge></td>
              </tr>))}
          </tbody></table>
        </div>
      </Panel>
    </div>
  );
}

function Ownership() {
  const { data } = useQuery({ queryKey: ["ownership"], queryFn: () => api.get<any>("/ownership") });
  return (
    <Panel eyebrow="Governance contract" title="Data ownership matrix">
      <table className="w-full text-[12px]">
        <thead><tr className="text-left text-uq-purple">{["Data Element", "Domain", "Steward", "Source", "Frequency"].map((h) => <th key={h} className="font-display font-extrabold uppercase text-[9px] tracking-wider pb-2 border-b border-uq-border">{h}</th>)}</tr></thead>
        <tbody>{data?.assignments?.map((a: any, i: number) => (
          <tr key={i} className="border-b border-uq-border/50">
            <td className="py-2 text-uq-ink">{a.data_element}</td><td><Badge tone={a.domain === "Risk" ? "magenta" : "purple"}>{a.domain}</Badge></td>
            <td className="text-uq-mid">{a.steward}</td><td className="text-uq-muted text-[10px]">{a.source_system}</td><td className="text-uq-muted">{a.frequency}</td>
          </tr>))}</tbody>
      </table>
    </Panel>
  );
}

function Params() {
  const { data = [] } = useQuery({ queryKey: ["params"], queryFn: () => api.get<any[]>("/config/parameters") });
  return (
    <Panel eyebrow="Deterministic config" title="Parameter overrides">
      {data.length === 0 && <div className="py-6 text-center text-[11px] text-uq-muted">No overrides — registry defaults in effect (risk weights, CCFs, betas, buffer rates, ×12.5).</div>}
      <div className="grid grid-cols-3 gap-2">{data.map((p) => (
        <div key={p.key} className="rounded-row border border-uq-border p-2"><div className="font-mono text-[9px] text-uq-purple">{p.key}</div><div className="num font-display font-bold text-uq-dark-purple">{p.value}</div><div className="text-[9px] text-uq-muted uppercase tracking-wider">{p.scope}</div></div>
      ))}</div>
    </Panel>
  );
}

function PromptModel() {
  const { data: health } = useQuery({ queryKey: ["health"], queryFn: () => api.get<any>("/health") });
  return (
    <Panel eyebrow="AI governance" title="Prompt & model governance">
      <div className="grid grid-cols-2 gap-3 text-[12px]">
        <div className="rounded-row border border-uq-border p-3">
          <div className="kpi-label mb-1">Live AI</div>
          <Badge tone={health?.ai_enabled ? "ok" : "neutral"}>{health?.ai_enabled ? "Anthropic Claude enabled" : "Deterministic fallback"}</Badge>
          <p className="text-[10px] text-uq-muted mt-2">When no API key is set, agents run governed deterministic stubs. Every agent run records prompt_version and model_version for audit.</p>
        </div>
        <div className="rounded-row border border-uq-border p-3">
          <div className="kpi-label mb-1">Models</div>
          <Row k="Reasoning" v="claude-opus-4-8" /><Row k="Narrative" v="claude-haiku-4-5" /><Row k="Prompt version" v="v1" />
        </div>
      </div>
      <p className="text-[10px] text-uq-muted mt-3">Agents are advisory only — no agent may certify, sign off, export or mutate report state without Checker approval.</p>
    </Panel>
  );
}

function Change() {
  const { data: instances = [] } = useQuery({ queryKey: ["instances"], queryFn: () => api.get<Instance[]>(endpoints.instances) });
  const id = instances[0]?.id;
  const { data = [] } = useQuery({ queryKey: ["circulars", id], enabled: !!id, queryFn: () => api.get<any[]>(endpoints.circulars(id!)) });
  return (
    <Panel eyebrow="Intake" title="Regulatory change log (parsed by agent)">
      <div className="flex flex-col gap-2">
        {data.map((c: any) => (
          <div key={c.id} className="rounded-row border border-uq-border p-2.5">
            <div className="flex items-center justify-between"><span className="font-display font-bold text-[11.5px] text-uq-dark-purple">{c.regulator} · {c.standard}</span><Badge tone="neutral">{c.status}</Badge></div>
            <div className="text-[11px] text-uq-mid mt-0.5">{c.description}</div>
            {c.impact_analysis?.impacted_schedules?.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-1.5">
                {c.impact_analysis.impacted_schedules.map((s: string) => <Badge key={s} tone="magenta">{s}</Badge>)}
                {c.impact_analysis.impacted_elements?.map((e: string) => <span key={e} className="font-mono text-[9px] bg-uq-alt-light text-uq-purple px-1.5 py-0.5 rounded">{e}</span>)}
              </div>)}
          </div>))}
      </div>
    </Panel>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return <div className="flex justify-between py-1 border-b border-uq-border/40 text-[11px]"><span className="text-uq-muted">{k}</span><span className="font-mono text-uq-ink">{v}</span></div>;
}
