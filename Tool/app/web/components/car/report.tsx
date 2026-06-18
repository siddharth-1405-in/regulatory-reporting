"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { Drawer } from "@/components/Drawer";
import { useRole } from "@/components/RoleContext";
import { AiBadge, Badge, Button, Panel, Stat, StatusDot } from "@/components/ui";
import {
  api, endpoints, type Drilldown, type ExceptionItem, type ReportStatus, type ScheduleDetail,
} from "@/lib/api";
import { money, pct, relTime } from "@/lib/format";

const rsTone: Record<string, any> = { Draft: "neutral", Exception: "crit", Remediation: "warn", "Signed Off": "ok" };

function useStatus(id: number) {
  return useQuery({ queryKey: ["reportStatus", id], queryFn: () => api.get<ReportStatus>(endpoints.reportStatus(id)), refetchInterval: 10000 });
}

// ============================ CAR OVERVIEW =================================
export function CarReportOverview({ id }: { id: number }) {
  const qc = useQueryClient();
  const { data } = useStatus(id);
  const [refreshing, setRefreshing] = useState(false);
  const m = data?.metrics; const flags = data?.flags;
  const scheds = data?.schedules ?? [];
  const signed = scheds.filter((s) => s.status === "signed_off").length;
  const breach = flags?.buffer_status === "Breach";
  const observations = [
    breach ? "Combined capital buffer requirement is breached — investigate inflated RWA." : "Capital buffers are met.",
    m ? `Total RWA SAR ${money(m.total_rwa)} '000; total capital ratio ${pct(m.total_ratio)}.` : "Awaiting certified data to compute.",
    `${signed} of ${scheds.length} sections signed off.`,
  ];

  const handleRefresh = () => {
    setRefreshing(true);
    qc.invalidateQueries({ queryKey: ["reportStatus", id] });
    setTimeout(() => setRefreshing(false), 1200);
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-4 gap-3">
        <Stat label="Report Status" value={data?.report_status ?? "—"} tone={breach ? "crit" : data?.report_status === "Signed Off" ? "ok" : undefined} sub="CAR-SA-01" />
        <Stat label="Total Capital Ratio" value={m ? pct(m.total_ratio) : "—"} sub="min 10.50%" tone={m && m.total_ratio < 0.105 ? "crit" : "ok"} />
        <Stat label="Total RWA" value={m ? money(m.total_rwa) : "—"} sub="SAR '000" tone="magenta" />
        <Stat label="Sections Signed-off" value={`${signed}/${scheds.length}`} sub="schedule + summary" tone={signed === scheds.length && scheds.length ? "ok" : undefined} />
      </div>
      <div className="grid grid-cols-[1fr_320px] gap-4 items-start">
        <Panel eyebrow="Report" title="Key observations">
          <ul className="flex flex-col gap-1.5 text-[12px] text-uq-mid list-disc pl-4">{observations.map((o, i) => <li key={i}>{o}</li>)}</ul>
          <div className="flex items-center justify-between mt-3 text-[10px] text-uq-muted">
            <span>Draft auto-computes from certified data — no manual run needed.</span>
            <button className="flex items-center gap-1 text-uq-purple hover:underline" onClick={handleRefresh} disabled={refreshing}>
              <RefreshCw className={`w-3 h-3 ${refreshing ? "animate-spin" : ""}`} />
              {refreshing ? "Updating…" : `last computed ${data?.last_computed ? relTime(data.last_computed) : "—"} · refresh`}
            </button>
          </div>
        </Panel>
        <Panel eyebrow="Composition" title="Capital & RWA">
          {m ? <>
            <Row k="CET1 capital" v={money(m.cet1)} /><Row k="Tier 1 capital" v={money(m.tier1)} />
            <Row k="Total regulatory capital" v={money(m.total_capital)} bold />
            <div className="h-px bg-uq-border my-2" />
            <Row k="Credit RWA" v={money(m.credit_rwa)} /><Row k="Market RWA" v={money(m.market_rwa)} /><Row k="Operational RWA" v={money(m.oprisk_rwa)} />
            <Row k="Total RWA" v={money(m.total_rwa)} bold />
          </> : <div className="py-6 text-center text-[11px] text-uq-muted">Certify data in the Data Foundation to populate the draft.</div>}
        </Panel>
      </div>
    </div>
  );
}

// ============================ DRAFT CAR REPORT =============================
export function DraftReport({ id, onNavigate }: { id: number; onNavigate?: (tab: string) => void }) {
  const { data: status } = useStatus(id);
  const scheds = status?.schedules ?? [];
  const [key, setKey] = useState("Cover");
  const flags = status?.flags;
  const breach = flags?.buffer_status === "Breach";

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <div className="flex gap-1 flex-wrap">
          {scheds.map((s) => (
            <button key={s.key} onClick={() => setKey(s.key)} title={s.label}
              className={`chip flex items-center gap-1 ${key === s.key ? "bg-uq-purple text-white" : "bg-uq-alt-light text-uq-mid"}`}>
              {s.key}{s.status === "signed_off" && <StatusDot tone="ok" />}{s.status === "reopened" && <StatusDot tone="warn" />}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <Badge tone={rsTone[status?.report_status ?? "Draft"]}>{status?.report_status ?? "Draft"}</Badge>
          <Button variant="soft" onClick={() => window.open(`/api/instances/${id}/export/excel`, "_blank")}>Export Excel</Button>
          <Button variant="soft" onClick={() => window.open(`/api/instances/${id}/export/pdf`, "_blank")}>Export PDF</Button>
        </div>
      </div>
      <ScheduleView id={id} schedKey={key} view={scheds.find((s) => s.key === key)}
        onBreachClick={breach && onNavigate ? () => onNavigate("exceptions") : undefined} />
    </div>
  );
}

function ScheduleView({ id, schedKey, view, onBreachClick }: { id: number; schedKey: string; view?: any; onBreachClick?: () => void }) {
  const qc = useQueryClient();
  const { role, actor } = useRole();
  const isMaker = role === "Maker" || role === "Admin";
  const isChecker = role === "Checker" || role === "Admin";
  const isLineSchedule = ["S1", "S2", "S3", "S4", "S5", "S6"].includes(schedKey);
  const { data } = useQuery<ScheduleDetail>({ queryKey: ["schedule", id, schedKey], enabled: isLineSchedule, queryFn: () => api.get(endpoints.reportSchedule(id, schedKey)) });
  const [submittedLocal, setSubmittedLocal] = useState<Set<string>>(new Set());
  const [drill, setDrill] = useState<string | null>(null);

  const signoff = useMutation({
    mutationFn: () => api.post(endpoints.reportSignoff(id, schedKey), { role, actor, comment: "" }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["reportStatus", id] }); qc.invalidateQueries({ queryKey: ["overview"] }); },
    onError: (e: any) => alert(e?.detail ?? "Sign-off blocked"),
  });
  const { data: dd } = useQuery<Drilldown>({ queryKey: ["drilldown", id, drill], enabled: !!drill, queryFn: () => api.get(endpoints.dfDrilldown(id, drill!)) });

  const makerSubmitted = submittedLocal.has(schedKey);

  const signoffBar = view && (
    <div className="flex items-center gap-2">
      <Badge tone={view.status === "signed_off" ? "ok" : view.status === "reopened" ? "warn" : "neutral"}>{view.status}</Badge>
      {isMaker && view.status !== "signed_off" && !makerSubmitted && (
        <Button variant="soft" onClick={() => setSubmittedLocal((s) => new Set([...s, schedKey]))}>
          Submit for Sign-off
        </Button>
      )}
      {isMaker && makerSubmitted && view.status !== "signed_off" && (
        <Badge tone="warn">Submitted — awaiting Checker</Badge>
      )}
      {isChecker && view.can_signoff && (
        <Button onClick={() => signoff.mutate()} disabled={signoff.isPending}>
          {signoff.isPending ? "Signing off…" : `Sign-off ${schedKey}`}
        </Button>
      )}
      {!view.can_signoff && view.status !== "signed_off" && <span className="text-[10px] text-warn2">{view.blocked_reason}</span>}
    </div>
  );

  if (schedKey === "Cover") return <CoverPanel id={id} actions={signoffBar} onBreachClick={onBreachClick} />;
  if (schedKey === "Summary") return <SummaryPanel data={data} id={id} actions={signoffBar} />;

  return (
    <Panel eyebrow="Draft CAR Report" title={view?.label ?? schedKey} actions={signoffBar}>
      {!data?.available && (
        <div className="py-8 text-center text-[11px] text-uq-muted">
          Pending certification — values will populate once data is signed off in the Data Foundation.
        </div>
      )}
      {data?.available && (
        <div className="overflow-auto max-h-[520px]">
          <table className="w-full text-[11px]">
            <thead className="sticky top-0 bg-white"><tr className="text-left text-uq-purple">
              {["Data element", "Business meaning", "Computation", "Value", ""].map((h) => <th key={h} className="font-display font-extrabold uppercase text-[9px] tracking-wider py-2 border-b border-uq-border">{h}</th>)}
            </tr></thead>
            <tbody>
              {data.lines.map((l) => (
                <tr key={l.element_code} className={`border-b border-uq-border/50 hover:bg-uq-alt-light align-top ${l.emphasis ? "bg-uq-alt-light/60" : ""}`}>
                  <td className={`py-1.5 text-uq-ink ${l.emphasis ? "font-display font-bold text-uq-dark-purple" : ""}`}>{l.label}<div className="font-mono text-[9px] text-uq-lavender">{l.element_code}</div></td>
                  <td className="py-1.5 text-uq-muted text-[10px] max-w-[220px]">{l.business_meaning}</td>
                  <td className="py-1.5 text-uq-muted text-[10px] max-w-[260px] italic">
                    {l.computation || "This line is directly sourced and requires no separate computation."}
                  </td>
                  <td className="py-1.5 text-right num font-semibold text-uq-dark-purple">{l.display ?? money(l.result)}</td>
                  <td className="py-1.5 text-right">{l.derived
                    ? <span className="text-[9px] text-uq-lavender uppercase tracking-wider">derived</span>
                    : <button className="text-[10px] text-uq-purple hover:underline" onClick={() => setDrill(l.element_code)}>lineage</button>}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>{Object.entries(data.totals).map(([k, v]) => (
              <tr key={k} className="bg-uq-alt-light"><td className="py-1.5 font-display font-bold text-uq-purple text-[10px]" colSpan={3}>{k}</td><td className="py-1.5 text-right font-display font-extrabold text-uq-magenta num">{money(v)}</td><td /></tr>
            ))}</tfoot>
          </table>
        </div>
      )}
      <Drawer open={!!drill} onClose={() => setDrill(null)} eyebrow="Lineage" title={dd?.label ?? "…"}>
        {dd && <div className="text-[12px]">
          <div className="text-[11px] text-uq-mid mb-3">{dd.business_meaning}</div>
          {dd.steps.map((s, i) => <div key={i} className="rounded-row bg-uq-alt-light p-2 mb-1.5"><div className="flex justify-between"><span className="font-display font-bold text-[11px] text-uq-dark-purple">{s.step}</span>{s.value != null && <span className="num text-[11px]">{money(s.value)}</span>}</div><div className="text-[10px] text-uq-muted">{s.detail}</div></div>)}
        </div>}
      </Drawer>
    </Panel>
  );
}

function CoverPanel({ id, actions, onBreachClick }: { id: number; actions: any; onBreachClick?: () => void }) {
  const { data } = useQuery({ queryKey: ["instance", id], queryFn: () => api.get<any>(endpoints.instance(id)) });
  const inst = data?.instance;
  const breach = data?.flags?.buffer_status === "Breach";
  return (
    <Panel eyebrow="CAR-SA-01" title="Cover" actions={actions}>
      <div className="grid grid-cols-2 gap-x-8 gap-y-1 text-[12px] max-w-2xl">
        {[["Bank full legal name", inst?.bank_name], ["Reporting quarter", inst?.period_label], ["Reporting period end", inst?.period_end], ["Reporting currency", inst?.currency], ["Units", inst?.units]].map(([k, v]) => (
          <div key={k as string} className="flex justify-between py-1.5 border-b border-uq-border/50"><span className="text-uq-muted">{k}</span><span className="font-semibold text-uq-ink">{v ?? "—"}</span></div>
        ))}
        <div className="flex justify-between py-1.5 border-b border-uq-border/50">
          <span className="text-uq-muted">Report status</span>
          <span className={`font-semibold ${breach ? "text-crit" : "text-ok"}`}>
            {data?.flags?.buffer_status ?? "—"}
            {breach && onBreachClick && (
              <button className="ml-2 text-[10px] text-uq-purple underline" onClick={onBreachClick}>→ View Exceptions</button>
            )}
          </span>
        </div>
      </div>
      <div className="mt-4 rounded-row bg-uq-alt-light p-3 border-l-[3px] border-uq-magenta text-[11px] text-uq-mid max-w-3xl">
        <div className="eyebrow mb-1">Declaration</div>
        We confirm that the information contained in this Capital Adequacy Return is accurate and complete to the best of our knowledge and belief, and has been prepared in accordance with SAMA's Basel III Capital Adequacy Framework and all applicable SAMA circulars and guidelines.
      </div>
    </Panel>
  );
}

function SummaryPanel({ data, id, actions }: { data?: ScheduleDetail; id: number; actions: any }) {
  const { data: sd } = useQuery<ScheduleDetail>({ queryKey: ["schedule", id, "Summary"], queryFn: () => api.get(endpoints.reportSchedule(id, "Summary")) });
  const v = (sd ?? data)?.values ?? {};
  const rows = [["Common Equity Tier 1 (CET1)", v.S1_CET1_NET, v.SUM_CET1_RATIO, 0.07], ["Tier 1 Capital", v.S1_TIER1_TOTAL, v.SUM_TIER1_RATIO, 0.085], ["Total Regulatory Capital", v.S1_TOTAL_CAPITAL, v.SUM_TOTAL_RATIO, 0.105]] as const;
  return (
    <Panel eyebrow="CAR-SA-01" title="Summary — Capital Adequacy Ratios" actions={actions}>
      <table className="w-full text-[12px]">
        <thead><tr className="text-left text-uq-purple">{["Metric", "Amount", "Ratio", "SAMA min", "Status"].map((h) => <th key={h} className="font-display font-extrabold uppercase text-[9px] tracking-wider py-2 border-b border-uq-border">{h}</th>)}</tr></thead>
        <tbody>
          {rows.map(([label, amt, ratio, min]) => (
            <tr key={label} className="border-b border-uq-border/50">
              <td className="py-2 text-uq-ink">{label}</td><td className="py-2 num text-right">{money(amt as number)}</td>
              <td className="py-2 num text-right font-semibold text-uq-dark-purple">{pct(ratio as number)}</td>
              <td className="py-2 num text-right text-uq-muted">{pct(min as number)}</td>
              <td className="py-2 text-right">{(ratio as number) >= (min as number) ? <Badge tone="ok">Met</Badge> : <Badge tone="crit">Below</Badge>}</td>
            </tr>
          ))}
          <tr><td className="py-2 font-display font-bold text-uq-purple">Total Risk-Weighted Assets</td><td className="py-2 num text-right font-display font-extrabold text-uq-magenta" colSpan={4}>{money(v.SUM_TOTAL_RWA)}</td></tr>
        </tbody>
      </table>
    </Panel>
  );
}

// ============================ EXCEPTIONS ===================================
export function ExceptionsWorkbench({ id }: { id: number }) {
  const qc = useQueryClient();
  const { data, refetch } = useQuery({
    queryKey: ["exceptions", id],
    queryFn: () => api.get<{ exceptions: ExceptionItem[]; open: number }>(endpoints.reportExceptions(id)),
    refetchOnMount: true,
    refetchOnWindowFocus: false,
  });

  // auto-refresh when this component mounts (tab activation)
  useEffect(() => { refetch(); }, []);

  const refresh = () => { qc.invalidateQueries({ queryKey: ["exceptions", id] }); qc.invalidateQueries({ queryKey: ["reportStatus", id] }); };

  // filter out approved remediation items (already resolved)
  const items = (data?.exceptions ?? []).filter((x) => x.proposal?.status !== "approved");

  return (
    <Panel eyebrow="Validation & AI" title="Exception workbench"
      actions={
        <div className="flex items-center gap-2">
          <AiBadge label="AI Analysis" />
          <Badge tone={items.length ? "crit" : "ok"}>{items.length} open</Badge>
          <Button variant="ghost" onClick={refresh} className="flex items-center gap-1">
            <RefreshCw className="w-3 h-3" /> Refresh
          </Button>
        </div>
      }>
      {items.length === 0 && <div className="py-10 text-center text-[11px] text-uq-muted">No open exceptions — the draft is clean.</div>}
      <div className="flex flex-col gap-3">
        {items.map((x, i) => (
          <div key={`${x.rule_code}-${i}`} className="rounded-row border border-uq-border p-3">
            <div className="flex items-center justify-between mb-1">
              <span className="font-display font-bold text-[12px] text-uq-dark-purple">{x.rule_code}</span>
              <Badge tone="magenta">{x.impacted_schedule}</Badge>
            </div>
            <div className="text-[11px] text-uq-ink mb-2">{x.issue}</div>
            <div className="grid grid-cols-2 gap-2 mb-2">
              <div className="rounded-row bg-uq-alt-light p-2">
                <div className="flex items-center gap-1 mb-0.5"><span className="eyebrow">AI Root Cause</span><AiBadge /></div>
                <div className="text-[10.5px] text-uq-mid">{x.ai_root_cause || "No AI analysis available — run agents to generate."}</div>
              </div>
              <div className="rounded-row bg-uq-alt-light p-2">
                <div className="flex items-center gap-1 mb-0.5"><span className="eyebrow">AI Recommendation</span><AiBadge /></div>
                <div className="text-[10.5px] text-uq-mid">{x.ai_recommendation || "Run agents to generate AI recommendations."}</div>
              </div>
            </div>
            {x.proposal && (
              <div className="rounded-row border border-uq-border p-2.5">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-mono text-[10px] text-uq-purple">{x.proposal.element_code}: {money(x.proposal.current_value)} → {money(x.proposal.proposed_value)}</span>
                  <Badge tone={x.proposal.status === "approved" ? "ok" : x.proposal.status === "rejected" ? "crit" : "warn"}>{x.proposal.status}</Badge>
                </div>
                {x.proposal.maker_rationale && <div className="text-[10px] text-uq-mid">Maker: {x.proposal.maker_rationale}</div>}
                {x.proposal.checker_comment && <div className="text-[10px] text-uq-muted">Checker: {x.proposal.checker_comment}</div>}
              </div>
            )}
            <div className="mt-2 text-[9.5px] text-uq-muted border-t border-uq-border/40 pt-2">
              Resolution: Correct the underlying data via the Data Foundation workflow, then re-run validation.
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function Row({ k, v, bold }: { k: string; v: string; bold?: boolean }) {
  return <div className="flex items-center justify-between py-1 text-[11.5px]"><span className={bold ? "font-display font-bold text-uq-dark-purple" : "text-uq-mid"}>{k}</span><span className={`num ${bold ? "font-display font-extrabold text-uq-magenta" : "text-uq-ink"}`}>{v}</span></div>;
}
