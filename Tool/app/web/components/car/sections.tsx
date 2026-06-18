"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { AiBadge, Badge, Button, Panel, StatusDot } from "@/components/ui";
import {
  api, endpoints, type AgentRun, type CalcResult, type Narrative,
  type Remediation, type Validation,
} from "@/lib/api";
import { money, pct, relTime } from "@/lib/format";

const useInvalidate = (id: number) => {
  const qc = useQueryClient();
  return () => {
    ["instance", "calc", "validation", "agents", "remediations", "narratives", "audit"]
      .forEach((k) => qc.invalidateQueries({ queryKey: [k, id] }));
    qc.invalidateQueries({ queryKey: ["overview"] });
  };
};

function Empty({ text }: { text: string }) {
  return <div className="py-10 text-center text-[11px] text-uq-muted">{text}</div>;
}

// ============================ SCHEDULES ====================================
const SHEETS = ["Schedule 1", "Schedule 2", "Schedule 3", "Schedule 4", "Schedule 6"];
export function SchedulesSection({ id }: { id: number }) {
  const { data, isError } = useQuery({ queryKey: ["calc", id], queryFn: () => api.get<CalcResult>(endpoints.calc(id)), retry: false });
  const [sheet, setSheet] = useState("Schedule 2");
  if (isError || !data) return <Panel title="Schedules"><Empty text="No calculation yet — certify the Data Layer and run the calculation." /></Panel>;
  const s = data.schedules[sheet];
  return (
    <Panel eyebrow="Report" title="Schedule detail"
      actions={
        <div className="flex gap-1 flex-wrap">
          {SHEETS.map((sh) => (
            <button key={sh} onClick={() => setSheet(sh)}
              className={`chip ${sheet === sh ? "bg-uq-purple text-white" : "bg-uq-alt-light text-uq-mid"}`}>
              {sh.replace("Schedule ", "S")}
            </button>
          ))}
        </div>}>
      {s ? (
        <div className="overflow-auto max-h-[540px]">
          <table className="w-full text-[11.5px]">
            <thead className="sticky top-0 bg-white">
              <tr className="text-left text-uq-purple">
                <th className="font-display font-extrabold uppercase text-[9px] tracking-wider py-2 border-b border-uq-border">Line item</th>
                <th className="font-display font-extrabold uppercase text-[9px] tracking-wider py-2 border-b border-uq-border text-right">Inputs</th>
                <th className="font-display font-extrabold uppercase text-[9px] tracking-wider py-2 border-b border-uq-border text-right">Result</th>
              </tr>
            </thead>
            <tbody>
              {s.lines.map((l) => (
                <tr key={l.element_code} className="border-b border-uq-border/50 hover:bg-uq-alt-light">
                  <td className="py-1.5 text-uq-ink">{l.label}<div className="font-mono text-[9px] text-uq-lavender">{l.element_code}</div></td>
                  <td className="py-1.5 text-right text-uq-muted num text-[10px]">
                    {Object.entries(l.inputs).map(([k, v]) => `${k}=${typeof v === "number" && v < 1 && v > 0 ? pct(v, 2) : money(v)}`).join("  ·  ")}
                  </td>
                  <td className="py-1.5 text-right font-semibold text-uq-dark-purple num">{money(l.result)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              {Object.entries({ ...s.subtotals, ...s.totals }).map(([k, v]) => (
                <tr key={k} className="bg-uq-alt-light">
                  <td className="py-1.5 font-display font-bold text-uq-purple text-[10px]" colSpan={2}>{k}</td>
                  <td className="py-1.5 text-right font-display font-extrabold text-uq-magenta num">{money(v)}</td>
                </tr>
              ))}
            </tfoot>
          </table>
        </div>
      ) : <Empty text="This schedule has no line breakdown." />}
    </Panel>
  );
}

// ============================ EXCEPTIONS ===================================
export function ExceptionsSection({ id }: { id: number }) {
  const invalidate = useInvalidate(id);
  const { data: vals = [] } = useQuery({ queryKey: ["validation", id], queryFn: () => api.get<Validation[]>(endpoints.validation(id)) });
  const { data: rems = [] } = useQuery({ queryKey: ["remediations", id], queryFn: () => api.get<Remediation[]>(endpoints.remediations(id)) });
  const decide = useMutation({
    mutationFn: ({ pid, action }: { pid: number; action: "approve" | "reject" }) =>
      api.post(`/remediations/${pid}/${action}`, { actor: "cro.checker", reason: action === "reject" ? "Pending source confirmation" : "" }),
    onSuccess: () => invalidate(),
  });
  const tone = (s: string) => s === "fail" ? "crit" : s === "warn" ? "warn" : "ok";
  const fails = vals.filter((v) => v.status === "fail");
  return (
    <div className="grid grid-cols-[1fr_360px] gap-4 items-start">
      <Panel eyebrow="Validation" title="Exception workbench"
        actions={<Badge tone={fails.length ? "crit" : "ok"}>{fails.length} failing · {vals.length} rules</Badge>}>
        <div className="flex flex-col gap-2">
          {vals.map((v) => (
            <div key={v.rule_code} className="rounded-row border border-uq-border p-2.5 flex gap-2.5">
              <div className="pt-0.5"><StatusDot tone={tone(v.status) as any} /></div>
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <span className="font-display font-bold text-[11.5px] text-uq-dark-purple">{v.rule_code}</span>
                  <Badge tone={tone(v.status)}>{v.status}</Badge>
                </div>
                <div className="text-[11px] text-uq-mid">{v.message}</div>
                {v.remediation_hint && <div className="text-[10px] text-uq-muted mt-0.5">↳ {v.remediation_hint}</div>}
                {v.elements?.length > 0 && <div className="font-mono text-[9px] text-uq-lavender mt-0.5">{v.elements.join(", ")}</div>}
              </div>
            </div>
          ))}
        </div>
      </Panel>

      <Panel eyebrow="Remediation" title="Proposed corrections">
        {rems.length === 0 && <Empty text="No remediation proposals. Run the agents to generate proposals for failing checks." />}
        <div className="flex flex-col gap-2.5">
          {rems.map((r) => (
            <div key={r.id} className="rounded-row border border-uq-border p-2.5">
              <div className="flex items-center justify-between mb-1">
                <span className="font-mono text-[10px] text-uq-purple">{r.element_code}</span>
                <Badge tone={r.status === "approved" ? "ok" : r.status === "rejected" ? "crit" : "warn"}>{r.status}</Badge>
              </div>
              <div className="text-[11px] text-uq-ink num">
                {money(r.current_value)} <span className="text-uq-magenta font-bold">→ {money(r.proposed_value)}</span>
              </div>
              <div className="text-[10px] text-uq-muted mt-1">{r.rationale}</div>
              {r.status === "proposed" && (
                <div className="flex gap-2 mt-2">
                  <Button onClick={() => decide.mutate({ pid: r.id, action: "approve" })} disabled={decide.isPending}>Approve (Checker)</Button>
                  <Button variant="ghost" onClick={() => decide.mutate({ pid: r.id, action: "reject" })} disabled={decide.isPending}>Reject</Button>
                </div>
              )}
              {r.checker && <div className="text-[9px] text-uq-muted mt-1.5 uppercase tracking-wider">Decided by {r.checker}</div>}
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}

// ============================ REASONING (drawer body) =======================
export function ReasoningSection({ id }: { id: number }) {
  const { data: agents = [] } = useQuery({ queryKey: ["agents", id], queryFn: () => api.get<AgentRun[]>(endpoints.agents(id)) });
  if (agents.length === 0) return <Empty text="No agent runs yet — run the governed agents from the report overview." />;
  return (
    <div className="flex flex-col gap-2.5">
      {agents.map((a) => (
        <div key={a.id} className="rounded-row border border-uq-border p-3">
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2">
              <Badge tone="magenta">{a.agent_type}</Badge>
              <span className="text-[10px] text-uq-muted">{relTime(a.created_at)}</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-[50px] h-[5px] rounded-pill bg-uq-light-lavender overflow-hidden">
                <div className="h-full bg-uq-conf" style={{ width: `${a.confidence * 100}%` }} />
              </div>
              <Badge tone={a.status === "approved" ? "ok" : a.status === "rejected" ? "crit" : "neutral"}>{a.status}</Badge>
            </div>
          </div>
          <p className="text-[11px] text-uq-ink leading-relaxed">{a.reasoning_summary}</p>
          <div className="text-[10px] text-uq-magenta mt-1.5 font-medium">↳ {a.proposed_action}</div>
          <div className="flex flex-wrap gap-1.5 mt-2">
            {a.impacted_metrics?.map((mt) => <span key={mt} className="font-mono text-[9px] bg-uq-alt-light text-uq-purple px-1.5 py-0.5 rounded">{mt}</span>)}
          </div>
          <div className="flex items-center justify-between mt-2 text-[9px] text-uq-muted uppercase tracking-wider">
            <span>{a.evidence_used?.length} evidence · approval {a.approval_required ? "required" : "n/a"}</span>
            <span className="font-mono normal-case">{a.prompt_version} · {a.model_version}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

// ============================ NARRATIVE ====================================
export function NarrativeSection({ id }: { id: number }) {
  const qc = useQueryClient();
  const { data: narrs = [] } = useQuery({ queryKey: ["narratives", id], queryFn: () => api.get<Narrative[]>(endpoints.narratives(id)) });
  const approve = useMutation({
    mutationFn: (nid: number) => api.post(`/instances/${id}/narratives/${nid}/approve`, { actor: "cro.checker" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["narratives", id] }),
  });
  const regenerate = useMutation({
    mutationFn: () => api.post(`/instances/${id}/agents/run`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["narratives", id] }); qc.invalidateQueries({ queryKey: ["exceptions", id] }); qc.invalidateQueries({ queryKey: ["reportStatus", id] }); },
    onError: (e: any) => alert(e?.detail ?? "Could not regenerate — ensure a calculation run exists."),
  });

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AiBadge label="Generated by Reporting AI Agent" />
          <span className="text-[10px] text-uq-muted">Narratives are produced by the AI Narrative Agent based on the current certified data and calc results.</span>
        </div>
        <Button variant="soft" onClick={() => regenerate.mutate()} disabled={regenerate.isPending}>
          {regenerate.isPending ? "Regenerating…" : "Re-create Narrative"}
        </Button>
      </div>

      {narrs.length === 0 && (
        <Panel title="Narrative review">
          <Empty text="No narrative drafted yet — click 'Re-create Narrative' to generate the executive narrative." />
        </Panel>
      )}

      <div className="grid grid-cols-2 gap-4">
        {narrs.map((n) => (
          <Panel key={n.id} eyebrow={n.language === "ar" ? "العربية · Arabic" : "English"} title={`Executive narrative · v${n.version}`}
            actions={
              <div className="flex items-center gap-2">
                <AiBadge />
                <Badge tone={n.status === "approved" ? "ok" : "warn"}>{n.status}</Badge>
              </div>
            }>
            <div className="rounded-row bg-uq-alt-light p-3 border-l-[3px] border-uq-magenta">
              <p className={`text-[11.5px] text-uq-ink leading-relaxed ${n.language === "ar" ? "text-right" : ""}`}
                dir={n.language === "ar" ? "rtl" : "ltr"}>{n.body}</p>
            </div>
            <div className="flex items-center justify-between mt-2.5">
              <span className="text-[10px] text-uq-muted">AI confidence: {pct(n.confidence, 0)} · Narrative Agent v{n.version}</span>
              {n.status !== "approved" && <Button onClick={() => approve.mutate(n.id)} disabled={approve.isPending}>Approve narrative</Button>}
            </div>
          </Panel>
        ))}
      </div>
    </div>
  );
}

// ============================ LINEAGE (drawer body) =========================
const TRACE_METRICS = [
  ["SUM_TOTAL_RWA", "Total RWA"], ["SUM_CET1_RATIO", "CET1 ratio"],
  ["S2_CREDIT_RWA", "Credit Risk RWA"], ["S1_TOTAL_CAPITAL", "Total Regulatory Capital"],
  ["S5_CET1_SURPLUS", "CET1 buffer surplus"],
];
export function LineageSection({ id }: { id: number }) {
  const [code, setCode] = useState("SUM_CET1_RATIO");
  const { data } = useQuery({ queryKey: ["lineage", id, code], queryFn: () => api.get<any>(`/instances/${id}/lineage?code=${code}`) });
  return (
    <div>
      <select value={code} onChange={(e) => setCode(e.target.value)} className="rounded-row border border-uq-border px-2 py-1 text-[11px] mb-3 w-full">
        {TRACE_METRICS.map(([c, l]) => <option key={c} value={c}>{l}</option>)}
      </select>
      <div className="text-[12px] text-uq-ink mb-2">
        <span className="font-display font-bold text-uq-dark-purple">{data?.label}</span>
        <span className="font-mono text-[10px] text-uq-lavender ml-2">{code}</span>
      </div>
      <div className="eyebrow mb-1.5">Upstream contributing elements ({data?.upstream?.length ?? 0})</div>
      <div className="flex flex-wrap gap-1.5">
        {data?.upstream?.map((u: string) => <span key={u} className="font-mono text-[9.5px] bg-uq-alt-light text-uq-purple px-2 py-1 rounded">{u}</span>)}
      </div>
    </div>
  );
}
