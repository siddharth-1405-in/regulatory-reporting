"use client";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Badge, Panel } from "@/components/ui";
import { api, endpoints, type Instance } from "@/lib/api";
import { CanonicalElements } from "./_components/canonical";
import { RuleEngine } from "./_components/rules";
import { SourceSystems } from "./_components/sources";

const TABS = [["sources", "Source Systems"], ["elements", "Canonical Elements"], ["rules", "Rule Engine"]] as const;

export default function DataFoundation() {
  const [tab, setTab] = useState("elements");
  const { data: instances = [] } = useQuery({ queryKey: ["instances"], queryFn: () => api.get<Instance[]>(endpoints.instances) });
  const [iid, setIid] = useState<number | null>(null);
  const activeId = iid ?? instances[0]?.id ?? null;

  return (
    <div className="p-6 max-w-[1500px] mx-auto">
      <div className="flex items-end justify-between mb-3">
        <div>
          <div className="eyebrow mb-1">Governed Canonical Data · Shared Foundation</div>
          <h1 className="font-display font-extrabold text-uq-dark-purple text-[22px] tracking-tight">Data Foundation</h1>
          <p className="text-[12px] text-uq-muted">Source → ingest → canonical element → rule engine → maker-checker. One certified foundation feeding every report pack.</p>
        </div>
        {tab !== "sources" && (
          <label className="flex items-center gap-2 text-[12px]">
            <span className="kpi-label">Reporting period</span>
            <select value={activeId ?? ""} onChange={(e) => setIid(Number(e.target.value))} className="rounded-row border border-uq-border px-2.5 py-1.5">
              {instances.map((i) => <option key={i.id} value={i.id}>{i.period_label} · {i.bank_name}</option>)}
            </select>
          </label>
        )}
      </div>

      <div className="flex gap-1 mb-4 border-b border-uq-border">
        {TABS.map(([k, l]) => (
          <button key={k} onClick={() => setTab(k)}
            className={`px-3 py-2 text-[12px] font-display font-bold border-b-2 -mb-px ${tab === k ? "border-uq-magenta text-uq-dark-purple" : "border-transparent text-uq-muted hover:text-uq-purple"}`}>{l}</button>
        ))}
      </div>

      {tab === "sources" && <SourceSystems />}
      {tab === "elements" && activeId && <CanonicalElements id={activeId} />}
      {tab === "rules" && activeId && <RuleEngine id={activeId} />}
      {!activeId && tab !== "sources" && <Panel title="No instance"><div className="py-8 text-center text-[11px] text-uq-muted">Create a report instance first.</div></Panel>}
    </div>
  );
}
