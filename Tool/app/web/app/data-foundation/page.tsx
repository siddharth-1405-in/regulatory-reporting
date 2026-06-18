"use client";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ArrowRight, Building2 } from "lucide-react";
import { Badge, Button, Panel } from "@/components/ui";
import { api, endpoints, type Instance, type Pack } from "@/lib/api";
import { DataIngestion } from "./_components/ingestion";
import { DataValidation } from "./_components/validation";
import { ReportReadyElements } from "./_components/elements";
import { RuleEngine } from "./_components/rules";
import { WorkflowNav, type Stage } from "./_components/WorkflowNav";

export default function DataFoundation() {
  const router = useRouter();
  const [stage, setStage] = useState<Stage>("ingestion");
  const [report, setReport] = useState("CAR-SA-01");
  const { data: instances = [] } = useQuery({ queryKey: ["instances"], queryFn: () => api.get<Instance[]>(endpoints.instances) });
  const { data: packs = [] } = useQuery({ queryKey: ["packs"], queryFn: () => api.get<Pack[]>(endpoints.packs) });
  const [iid, setIid] = useState<number | null>(null);
  const activeId = iid ?? instances[0]?.id ?? null;
  const active = instances.find((i) => i.id === activeId);

  const stageLabels: Record<Stage, string> = {
    ingestion: "Step 1 of 4 — Data Ingestion",
    validation: "Step 2 of 4 — Data Validation",
    rules: "Step 3 of 4 — Rule Engine",
    elements: "Step 4 of 4 — Report-Ready Data & Sign-off",
  };

  return (
    <div className="p-6 max-w-[1500px] mx-auto flex flex-col gap-3.5">
      {/* A. context header */}
      <div className="flex items-end justify-between">
        <div>
          <div className="eyebrow mb-0.5">{stageLabels[stage]}</div>
          <h1 className="font-display font-extrabold text-uq-dark-purple text-[22px] tracking-tight">Data Foundation</h1>
          <p className="text-[12.5px] text-uq-muted max-w-[680px]">Prepare, validate and sign off the data that feeds a selected regulatory report. Only certified data elements are published to the Report Pack.</p>
        </div>
        <Button variant="ghost" className="flex items-center gap-1.5" disabled={!activeId}
          onClick={() => activeId && router.push(`/report-pack/car/${activeId}`)}>
          Go to Report Pack <ArrowRight className="w-3.5 h-3.5" />
        </Button>
      </div>

      {/* scoping controls */}
      <div className="panel p-3 flex items-end gap-5 flex-wrap">
        <label className="flex flex-col gap-1">
          <span className="kpi-label">Select report</span>
          <select value={report} onChange={(e) => setReport(e.target.value)} className="rounded-row border border-uq-border px-2.5 py-1.5 text-[12px] font-display font-bold text-uq-dark-purple min-w-[230px]">
            {packs.map((p) => <option key={p.code} value={p.code} disabled={p.status !== "active"}>{p.name} ({p.code}){p.status !== "active" ? " — planned" : ""}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="kpi-label">Reporting period</span>
          <select value={activeId ?? ""} onChange={(e) => setIid(Number(e.target.value))} className="rounded-row border border-uq-border px-2.5 py-1.5 text-[12px]">
            {instances.map((i) => <option key={i.id} value={i.id}>{i.period_label}</option>)}
          </select>
        </label>
        <div className="flex flex-col gap-1">
          <span className="kpi-label">Legal entity</span>
          <span className="flex items-center gap-1.5 rounded-row bg-uq-alt-light px-2.5 py-1.5 text-[12px] text-uq-dark-purple font-medium">
            <Building2 className="w-3.5 h-3.5 text-uq-purple" />{active?.bank_name ?? "—"}
          </span>
        </div>
        <div className="flex flex-col gap-1 ml-auto">
          <span className="kpi-label">Cycle</span>
          <Badge tone="purple">{active?.status ?? "—"}</Badge>
        </div>
      </div>

      {/* B. workflow navigator */}
      <WorkflowNav active={stage} onSelect={setStage} />

      {/* C. stage work area */}
      {!activeId
        ? <Panel title="No reporting cycle"><div className="py-8 text-center text-[11px] text-uq-muted">Open a reporting cycle from the Overview first.</div></Panel>
        : <div>
          {stage === "ingestion" && <DataIngestion id={activeId} />}
          {stage === "validation" && <DataValidation id={activeId} onProceed={() => setStage("rules")} />}
          {stage === "rules" && <RuleEngine id={activeId} />}
          {stage === "elements" && <ReportReadyElements id={activeId} />}
        </div>}
    </div>
  );
}
