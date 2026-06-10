"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRole } from "@/components/RoleContext";
import { Badge, Button, Panel, Stat, StatusDot } from "@/components/ui";
import { api, endpoints, type CalcResult } from "@/lib/api";
import { money, pct } from "@/lib/format";

const useInvalidate = () => {
  const qc = useQueryClient();
  return () => qc.invalidateQueries();
};

function gateMsg(err: any): string {
  const d = err?.detail;
  if (d?.error === "certification_gate") return `Blocked: certify ${d.blocking_domains?.join(", ")} in the Data Layer`;
  if (d?.error === "validation_failures") return `Sign-off blocked: ${d.count} failing validation rule(s)`;
  if (d?.error === "not_signed_off") return `Export blocked: instance is ${d.status}`;
  return "Action blocked by governance gate.";
}

const STEPS = ["DRAFT", "INGESTED", "CERTIFYING", "VALIDATED", "REMEDIATION", "SIGNED_OFF", "EXPORTED"];
function Stepper({ status }: { status?: string }) {
  const idx = STEPS.indexOf(status ?? "DRAFT");
  return (
    <div className="flex items-center gap-1">
      {STEPS.map((s, i) => (
        <div key={s} className={`flex-1 text-center rounded-pill py-1 text-[9px] font-display font-bold uppercase tracking-wider
          ${i <= idx ? "bg-uq-symbol text-white" : "bg-uq-alt-light text-uq-muted"}`}>{s}</div>
      ))}
    </div>
  );
}

export function CarOverview({ id, detail }: { id: number; detail: any }) {
  const invalidate = useInvalidate();
  const { role, actor } = useRole();
  const isChecker = role === "Checker" || role === "Admin";
  const m = detail?.metrics;
  const flags = detail?.flags;
  const breach = flags?.buffer_status === "Breach";

  const calculate = useMutation({ mutationFn: () => api.post(`/instances/${id}/calculate`), onSuccess: invalidate });
  const runAgents = useMutation({ mutationFn: () => api.post(`/instances/${id}/agents/run`), onSuccess: invalidate });
  const signoff = useMutation({ mutationFn: () => api.post(`/instances/${id}/signoff`, { actor }), onSuccess: invalidate });

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-6 gap-3">
        <Stat label="CET1 Ratio" value={m ? pct(m.cet1_ratio) : "—"} sub="min 7.00%" tone={m && m.cet1_ratio < 0.07 ? "crit" : "ok"} />
        <Stat label="Tier 1 Ratio" value={m ? pct(m.tier1_ratio) : "—"} sub="min 8.50%" tone={m && m.tier1_ratio < 0.085 ? "crit" : "ok"} />
        <Stat label="Total Capital Ratio" value={m ? pct(m.total_ratio) : "—"} sub="min 10.50%" tone={m && m.total_ratio < 0.105 ? "crit" : "ok"} />
        <Stat label="Total RWA" value={m ? money(m.total_rwa) : "—"} sub="SAR '000" tone="magenta" />
        <Stat label="Buffer Surplus" value={m ? pct(m.cet1_buffer_surplus) : "—"} sub={`combined ${m ? pct(m.combined_buffer) : "—"}`} tone={breach ? "crit" : "ok"} />
        <Stat label="Buffer Status" value={flags?.buffer_status ?? "—"} sub={detail?.instance?.status} tone={breach ? "crit" : "ok"} />
      </div>

      <div className="grid grid-cols-[1fr_320px] gap-4 items-start">
        <Panel eyebrow="Workflow" title="Report pipeline & actions">
          <Stepper status={detail?.instance?.status} />
          <div className="flex flex-wrap gap-2 mt-4">
            <Button onClick={() => calculate.mutate()} disabled={!detail?.calc_allowed || calculate.isPending}>
              {calculate.isPending ? "Calculating…" : "Run calculation"}
            </Button>
            <Button variant="ghost" onClick={() => runAgents.mutate()} disabled={!m || runAgents.isPending}>
              {runAgents.isPending ? "Running agents…" : "Run governed agents"}
            </Button>
            {isChecker && <Button variant="soft" onClick={() => signoff.mutate()} disabled={signoff.isPending}>Checker sign-off</Button>}
          </div>
          {!detail?.calc_allowed && (
            <div className="mt-3 text-[11px] text-warn2 flex items-center gap-1.5">
              <StatusDot tone="warn" /> Calculation blocked — certify in Data Layer: {detail?.blocking_domains?.join(", ")}
            </div>
          )}
          {(calculate.error || signoff.error) && (
            <div className="mt-3 text-[11px] text-crit">{gateMsg((calculate.error as any) || (signoff.error as any))}</div>
          )}
        </Panel>

        <Panel eyebrow="Capital composition" title="Snapshot">
          <Row label="CET1 capital" value={money(m?.cet1)} />
          <Row label="Tier 1 capital" value={money(m?.tier1)} />
          <Row label="Total regulatory capital" value={money(m?.total_capital)} bold />
          <div className="h-px bg-uq-border my-2" />
          <Row label="Credit risk RWA" value={money(m?.credit_rwa)} />
          <Row label="Market risk RWA" value={money(m?.market_rwa)} />
          <Row label="Operational risk RWA" value={money(m?.oprisk_rwa)} />
          <Row label="Total RWA" value={money(m?.total_rwa)} bold />
          <div className="h-px bg-uq-border my-2" />
          <Row label="Reconciliation difference" value={money(m?.recon_diff)} />
          <Row label="RWA composition" value={pct(m?.rwa_composition_pct, 0)} />
        </Panel>
      </div>
    </div>
  );
}

function Row({ label, value, bold }: { label: string; value: string; bold?: boolean }) {
  return (
    <div className="flex items-center justify-between py-1 text-[11.5px]">
      <span className={bold ? "font-display font-bold text-uq-dark-purple" : "text-uq-mid"}>{label}</span>
      <span className={`num ${bold ? "font-display font-extrabold text-uq-magenta" : "text-uq-ink"}`}>{value}</span>
    </div>
  );
}

export function CoverView({ detail }: { detail: any }) {
  const inst = detail?.instance;
  return (
    <Panel eyebrow="CAR-SA-01" title="Cover">
      <div className="grid grid-cols-2 gap-x-8 gap-y-1 text-[12px] max-w-2xl">
        <CoverRow k="Bank full legal name" v={inst?.bank_name} />
        <CoverRow k="Reporting quarter" v={inst?.period_label} />
        <CoverRow k="Reporting period end" v={inst?.period_end} />
        <CoverRow k="Reporting currency" v={inst?.currency} />
        <CoverRow k="Units" v={inst?.units} />
        <CoverRow k="Status" v={inst?.status} />
      </div>
      <div className="mt-4 rounded-row bg-uq-alt-light p-3 border-l-[3px] border-uq-magenta text-[11px] text-uq-mid max-w-3xl">
        <div className="eyebrow mb-1">Declaration</div>
        We confirm that the information contained in this Capital Adequacy Return is accurate and complete
        to the best of our knowledge and belief, and has been prepared in accordance with SAMA's Basel III
        Capital Adequacy Framework and all applicable SAMA circulars and guidelines.
      </div>
    </Panel>
  );
}
function CoverRow({ k, v }: { k: string; v?: string }) {
  return <div className="flex justify-between py-1.5 border-b border-uq-border/50"><span className="text-uq-muted">{k}</span><span className="font-semibold text-uq-ink">{v ?? "—"}</span></div>;
}

export function SummaryView({ id }: { id: number }) {
  const { data, isError } = useQuery({ queryKey: ["calc", id], queryFn: () => api.get<CalcResult>(endpoints.calc(id)), retry: false });
  if (isError || !data) return <Panel title="Summary"><div className="py-10 text-center text-[11px] text-uq-muted">No calculation yet.</div></Panel>;
  const v = data.values;
  const rows = [
    ["Common Equity Tier 1 (CET1)", v.S1_CET1_NET, v.SUM_CET1_RATIO, 0.07],
    ["Tier 1 Capital", v.S1_TIER1_TOTAL, v.SUM_TIER1_RATIO, 0.085],
    ["Total Regulatory Capital", v.S1_TOTAL_CAPITAL, v.SUM_TOTAL_RATIO, 0.105],
  ] as const;
  return (
    <div className="grid grid-cols-[1fr_320px] gap-4 items-start">
      <Panel eyebrow="CAR-SA-01" title="Summary — Capital Adequacy Ratios">
        <table className="w-full text-[12px]">
          <thead><tr className="text-left text-uq-purple">
            {["Metric", "Amount", "Ratio", "SAMA min", "Status"].map((h) => <th key={h} className="font-display font-extrabold uppercase text-[9px] tracking-wider py-2 border-b border-uq-border">{h}</th>)}
          </tr></thead>
          <tbody>
            {rows.map(([label, amt, ratio, min]) => (
              <tr key={label} className="border-b border-uq-border/50">
                <td className="py-2 text-uq-ink">{label}</td>
                <td className="py-2 num text-right">{money(amt as number)}</td>
                <td className="py-2 num text-right font-semibold text-uq-dark-purple">{pct(ratio as number)}</td>
                <td className="py-2 num text-right text-uq-muted">{pct(min as number)}</td>
                <td className="py-2 text-right">{(ratio as number) >= (min as number) ? <Badge tone="ok">Met</Badge> : <Badge tone="crit">Below</Badge>}</td>
              </tr>
            ))}
            <tr><td className="py-2 font-display font-bold text-uq-purple">Total Risk-Weighted Assets</td><td className="py-2 num text-right font-display font-extrabold text-uq-magenta" colSpan={4}>{money(v.SUM_TOTAL_RWA)}</td></tr>
          </tbody>
        </table>
      </Panel>
      <Panel eyebrow="Schedule 5" title="Capital buffers">
        <Row label="Combined buffer requirement" value={pct(v.S5_COMBINED_BUFFER)} />
        <Row label="CCB" value={pct(v.S5_BUFFER_CCB)} />
        <Row label="CCyB" value={pct(v.S5_BUFFER_CCYB)} />
        <Row label="D-SIB surcharge" value={pct(v.S5_BUFFER_DSIB)} />
        <div className="h-px bg-uq-border my-2" />
        <Row label="CET1 available for buffers" value={pct(v.S5_CET1_AVAILABLE_FOR_BUFFERS)} bold />
        <Row label="Surplus / (deficit)" value={pct(v.S5_CET1_SURPLUS)} bold />
        <div className="mt-2">{(v.S5_CET1_SURPLUS ?? 0) >= 0 ? <Badge tone="ok">Buffer compliant</Badge> : <Badge tone="crit">Buffer breach</Badge>}</div>
      </Panel>
    </div>
  );
}
