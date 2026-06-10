"use client";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { useState } from "react";
import { Badge } from "@/components/ui";
import { NarrativeSection } from "@/components/car/sections";
import { CarReportOverview, DraftReport, ExceptionsWorkbench } from "@/components/car/report";
import { api, endpoints, type ReportStatus } from "@/lib/api";

const TABS = [["overview", "CAR Overview"], ["narrative", "Narrative"], ["exceptions", "Exceptions"], ["draft", "Draft CAR Report"]] as const;
const rsTone: Record<string, any> = { Draft: "neutral", Exception: "crit", Remediation: "warn", "Signed Off": "ok" };

export default function CarWorkspace() {
  const id = Number(useParams().id);
  const [tab, setTab] = useState("overview");
  const { data: inst } = useQuery({ queryKey: ["instance", id], queryFn: () => api.get<any>(endpoints.instance(id)) });
  const { data: status } = useQuery({ queryKey: ["reportStatus", id], queryFn: () => api.get<ReportStatus>(endpoints.reportStatus(id)), refetchInterval: 10000 });
  const i = inst?.instance;

  return (
    <div className="p-6 max-w-[1400px] mx-auto">
      <div className="flex items-end justify-between mb-3">
        <div>
          <div className="eyebrow mb-1">CAR-SA-01 · Capital Adequacy Return · {i?.period_label ?? `#${id}`}</div>
          <h1 className="font-display font-extrabold text-uq-dark-purple text-[20px] tracking-tight">{i?.bank_name ?? "Report Pack"}</h1>
        </div>
        <Badge tone={rsTone[status?.report_status ?? "Draft"]}>{status?.report_status ?? "Draft"}</Badge>
      </div>

      <div className="flex gap-1 mb-4 border-b border-uq-border">
        {TABS.map(([k, l]) => (
          <button key={k} onClick={() => setTab(k)}
            className={`px-3 py-2 text-[12px] font-display font-bold border-b-2 -mb-px ${tab === k ? "border-uq-magenta text-uq-dark-purple" : "border-transparent text-uq-muted hover:text-uq-purple"}`}>{l}</button>
        ))}
      </div>

      {tab === "overview" && <CarReportOverview id={id} />}
      {tab === "narrative" && <NarrativeSection id={id} />}
      {tab === "exceptions" && <ExceptionsWorkbench id={id} />}
      {tab === "draft" && <DraftReport id={id} />}
    </div>
  );
}
