"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, CheckSquare } from "lucide-react";
import { Drawer } from "@/components/Drawer";
import { useRole } from "@/components/RoleContext";
import { Badge, Button, Panel, StatusPill } from "@/components/ui";
import { api, endpoints, type Catalogue, type Drilldown } from "@/lib/api";
import { money } from "@/lib/format";

const SHEETS = ["All", "Schedule 1", "Schedule 2", "Schedule 3", "Schedule 4", "Schedule 6"];

export function ReportReadyElements({ id }: { id: number }) {
  const qc = useQueryClient();
  const router = useRouter();
  const { role, actor } = useRole();
  const isMaker = role === "Maker" || role === "Admin";
  const isChecker = role === "Checker" || role === "Admin";

  const { data: cat } = useQuery({ queryKey: ["catalogue", id], queryFn: () => api.get<Catalogue>(endpoints.catalogue(id)) });
  const { data: queue = [] } = useQuery({ queryKey: ["signoff", id], queryFn: () => api.get<any[]>(endpoints.signoffQueue(id)) });

  const [sheet, setSheet] = useState("All");
  const [domain, setDomain] = useState("All");
  const [q, setQ] = useState("");
  const [sel, setSel] = useState<Set<string>>(new Set());
  const [drill, setDrill] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3500);
  };

  const refresh = () => {
    ["catalogue", "signoff"].forEach((k) => qc.invalidateQueries({ queryKey: [k, id] }));
    qc.invalidateQueries({ queryKey: ["overview"] });
    qc.invalidateQueries({ queryKey: ["reportStatus", id] });
    setSel(new Set());
  };
  const bulk = useMutation({
    mutationFn: ({ ep, codes }: { ep: string; codes: string[] }) => api.post(ep, { element_codes: codes, role, actor }),
    onSuccess: (_data, { ep }) => {
      refresh();
      if (ep === endpoints.dlReject(id)) showToast("Returned for correction — maker has been notified.");
      else if (ep === endpoints.dlApprove(id)) showToast("Signed off successfully.");
      else showToast("Submitted for sign-off.");
    },
    onError: (e: any) => alert(e?.detail ?? "Action not permitted."),
  });

  const rows = useMemo(() => (cat?.elements ?? []).filter((e) =>
    (sheet === "All" || e.sheet_name === sheet) && (domain === "All" || e.domain === domain) &&
    (!q || e.label.toLowerCase().includes(q.toLowerCase()) || e.element_code.toLowerCase().includes(q.toLowerCase()))
  ), [cat, sheet, domain, q]);
  const selCodes = [...sel];
  const toggle = (c: string) => setSel((s) => { const n = new Set(s); n.has(c) ? n.delete(c) : n.add(c); return n; });
  const toggleAll = () => {
    if (selCodes.length === rows.length) setSel(new Set());
    else setSel(new Set(rows.map((r) => r.element_code)));
  };

  const { data: dd } = useQuery<Drilldown>({ queryKey: ["drilldown", id, drill], enabled: !!drill, queryFn: () => api.get(endpoints.dfDrilldown(id, drill!)) });

  const summary = cat?.summary ?? {};
  const ready = summary["draft"] ?? 0;
  const submitted = summary["submitted"] ?? 0;
  const certified = summary["certified"] ?? 0;
  const total = Object.values(summary).reduce((a: number, b: any) => a + b, 0) as number;
  const allSignedOff = certified === total && total > 0;

  return (
    <div className="flex flex-col gap-4">
      {/* Status strip above the table */}
      <div className="grid grid-cols-3 gap-3">
        {[["Ready", ready, "text-uq-purple"], ["Submitted", submitted, "text-warn2"], ["Signed-off", certified, "text-ok"]].map(([l, n, c]) => (
          <div key={l as string} className="panel p-3 flex items-center gap-3">
            <div className={`font-display font-extrabold text-[26px] num ${c}`}>{n as number}</div>
            <div>
              <div className="font-display font-bold text-[11px] text-uq-dark-purple">{l as string}</div>
              <div className="text-[9.5px] text-uq-muted">data elements</div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-[1fr_300px] gap-4 items-start">
        <Panel eyebrow="Report-ready data elements" title="Review grid"
          actions={
            <div className="flex items-center gap-1.5">
              <input placeholder="Search…" value={q} onChange={(e) => setQ(e.target.value)} className="rounded-row border border-uq-border px-2 py-1 text-[11px] w-28" />
              <select value={domain} onChange={(e) => setDomain(e.target.value)} className="rounded-row border border-uq-border px-2 py-1 text-[11px]">
                {["All", "Finance", "Risk"].map((d) => <option key={d}>{d}</option>)}
              </select>
            </div>}>
          <div className="flex gap-1 mb-2 flex-wrap">
            {SHEETS.map((s) => <button key={s} onClick={() => setSheet(s)} className={`chip ${sheet === s ? "bg-uq-purple text-white" : "bg-uq-alt-light text-uq-mid"}`}>{s.replace("Schedule ", "S")}</button>)}
          </div>
          <div className="flex items-center gap-2 mb-2 min-h-[30px]">
            <span className="text-[11px] text-uq-muted">{selCodes.length} selected</span>
            {isMaker && <>
              <Button variant="soft" disabled={!selCodes.length} onClick={() => bulk.mutate({ ep: endpoints.dlSubmit(id), codes: selCodes })}>Submit for sign-off</Button>
            </>}
            {isChecker && <>
              <Button disabled={!selCodes.length} onClick={() => bulk.mutate({ ep: endpoints.dlApprove(id), codes: selCodes })}>Sign-off</Button>
              <Button variant="ghost" disabled={!selCodes.length} onClick={() => bulk.mutate({ ep: endpoints.dlReject(id), codes: selCodes })}>Return for correction</Button>
            </>}
          </div>
          <div className="overflow-auto max-h-[540px] border border-uq-border rounded-row">
            <table className="w-full text-[11px]">
              <thead className="sticky top-0 bg-uq-near-white">
                <tr className="text-left text-uq-purple">
                  <th className="p-2 w-6">
                    <button onClick={toggleAll} title="Select all" className="text-uq-purple hover:text-uq-magenta">
                      <CheckSquare className="w-3.5 h-3.5" strokeWidth={2} />
                    </button>
                  </th>
                  {["Data element", "Source lineage", "Value", "Readiness", ""].map((h) => <th key={h} className="font-display font-extrabold uppercase text-[9px] tracking-wider p-2 border-b border-uq-border">{h}</th>)}
                </tr>
              </thead>
              <tbody>
                {rows.map((e) => (
                  <tr key={e.element_code} className="border-b border-uq-border/50 hover:bg-uq-alt-light align-top">
                    <td className="p-2"><input type="checkbox" checked={sel.has(e.element_code)} onChange={() => toggle(e.element_code)} /></td>
                    <td className="p-2">
                      <div className="text-uq-ink font-medium">{e.label}</div>
                      <div className="text-[9.5px] text-uq-muted leading-tight">{e.business_meaning}</div>
                    </td>
                    <td className="p-2 text-uq-muted text-[10px]">{e.source_system}<span className={`ml-1 ${e.domain === "Risk" ? "text-uq-magenta" : "text-uq-purple"}`}>· {e.domain}</span></td>
                    <td className="p-2 text-right num text-uq-ink">{money(e.value)}</td>
                    <td className="p-2"><StatusPill status={e.status} /></td>
                    <td className="p-2 text-right whitespace-nowrap">
                      <button className="text-[10px] text-uq-purple hover:underline" onClick={() => setDrill(e.element_code)}>trace</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="text-[10px] text-uq-muted mt-1.5">
            {isMaker ? "Values are produced upstream and are not edited here. Review the report-ready elements and submit them for Checker sign-off."
              : isChecker ? "Review submitted elements and Sign-off, or Return for correction. Sign-offs roll up to domain certification and auto-recompute the draft."
              : "Read-only — switch to Maker/Checker to act."}
          </div>
        </Panel>

        {/* sign-off queue */}
        <Panel eyebrow="Sign-off queue" title="Checker review queue" actions={<Badge tone={queue.length ? "warn" : "ok"}>{queue.length}</Badge>}>
          {queue.length === 0
            ? <div className="py-5 text-center text-[11px] text-uq-muted">Nothing awaiting review. Makers submit report-ready elements here for Checker sign-off.</div>
            : <div className="flex flex-col gap-1.5">
              {queue.map((qr) => (
                <div key={qr.element_code} className="rounded-row border border-uq-border p-2 flex items-center justify-between">
                  <div><div className="text-[11px] text-uq-ink">{qr.label}</div><div className="text-[9px] text-uq-muted uppercase tracking-wider">{qr.domain} · {qr.steward}</div></div>
                  {isChecker && <Button onClick={() => bulk.mutate({ ep: endpoints.dlApprove(id), codes: [qr.element_code] })}>Sign-off</Button>}
                </div>
              ))}
            </div>}

          {allSignedOff && (
            <div className="mt-4 rounded-row border border-ok/30 bg-ok/5 p-3 text-center">
              <div className="text-ok font-display font-bold text-[12px] mb-1">All data elements signed off</div>
              <Button className="w-full flex items-center justify-center gap-1.5 mt-1" onClick={() => router.push(`/report-pack/car/${id}`)}>
                Go to Report Pack <ArrowRight className="w-3.5 h-3.5" />
              </Button>
            </div>
          )}
        </Panel>
      </div>

      {/* toast */}
      {toast && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 bg-uq-dark-purple text-white text-[12px] font-display font-bold px-5 py-3 rounded-row shadow-lg">
          {toast}
        </div>
      )}

      <Drawer open={!!drill} onClose={() => setDrill(null)} eyebrow="Source → processed lineage" title={dd?.label ?? "…"} width={500}>
        {dd && (
          <div className="text-[12px]">
            <div className="font-mono text-[10px] text-uq-lavender mb-1">{dd.element_code}</div>
            <div className="text-[11px] text-uq-mid mb-3">{dd.business_meaning}</div>
            <div className="eyebrow mb-1.5">Derivation trace</div>
            <div className="flex flex-col gap-1.5 mb-3">
              {dd.steps.map((s, i) => (
                <div key={i} className="rounded-row bg-uq-alt-light p-2">
                  <div className="flex items-center justify-between">
                    <span className="font-display font-bold text-[11px] text-uq-dark-purple">{s.step}</span>
                    {s.value != null && <span className="num text-[11px] text-uq-ink">{money(s.value)}</span>}
                  </div>
                  <div className="text-[10px] text-uq-muted">{s.detail}</div>
                </div>
              ))}
            </div>
            <div className="rounded-row border border-uq-border p-2 flex items-center justify-between">
              <span className="kpi-label">Processed / contribution</span>
              <span className="num font-display font-extrabold text-uq-magenta">{dd.processed_value != null ? money(dd.processed_value) : "—"}</span>
            </div>
            <div className="eyebrow mt-3 mb-1">Rule</div>
            <div className="text-[11px] text-uq-mid">{dd.rule?.plain_english}</div>
            <div className="text-[9px] text-uq-lavender mt-1">{dd.rule?.origin}</div>
          </div>
        )}
      </Drawer>
    </div>
  );
}
