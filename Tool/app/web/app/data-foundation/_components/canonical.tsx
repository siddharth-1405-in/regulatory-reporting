"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Drawer } from "@/components/Drawer";
import { useRole } from "@/components/RoleContext";
import { Badge, Button, Panel, StatusPill } from "@/components/ui";
import { api, endpoints, type Catalogue, type DataElement, type Drilldown } from "@/lib/api";
import { money } from "@/lib/format";

const SHEETS = ["All", "Schedule 1", "Schedule 2", "Schedule 3", "Schedule 4", "Schedule 6"];

export function CanonicalElements({ id }: { id: number }) {
  const qc = useQueryClient();
  const { role, actor } = useRole();
  const isMaker = role === "Maker" || role === "Admin";
  const isChecker = role === "Checker" || role === "Admin";

  const { data: cat } = useQuery({ queryKey: ["catalogue", id], queryFn: () => api.get<Catalogue>(endpoints.catalogue(id)) });
  const { data: queue = [] } = useQuery({ queryKey: ["signoff", id], queryFn: () => api.get<any[]>(endpoints.signoffQueue(id)) });

  const [sheet, setSheet] = useState("All");
  const [domain, setDomain] = useState("All");
  const [q, setQ] = useState("");
  const [sel, setSel] = useState<Set<string>>(new Set());
  const [editing, setEditing] = useState<{ code: string; value: string } | null>(null);
  const [drill, setDrill] = useState<string | null>(null);

  const refresh = () => {
    ["catalogue", "signoff"].forEach((k) => qc.invalidateQueries({ queryKey: [k, id] }));
    qc.invalidateQueries({ queryKey: ["overview"] });
    qc.invalidateQueries({ queryKey: ["reportStatus", id] });
    setSel(new Set());
  };
  const bulk = useMutation({
    mutationFn: ({ ep, codes }: { ep: string; codes: string[] }) => api.post(ep, { element_codes: codes, role, actor }),
    onSuccess: refresh, onError: (e: any) => alert(e?.detail ?? "Action not permitted."),
  });
  const editMut = useMutation({
    mutationFn: ({ code, value }: { code: string; value: number }) =>
      api.post(endpoints.dlEdit(id), { element_code: code, value, role, actor, reason: "Manual override" }),
    onSuccess: () => { setEditing(null); refresh(); },
    onError: (e: any) => { setEditing(null); alert(e?.detail ?? "Edit not permitted."); },
  });
  const clearMut = useMutation({
    mutationFn: (code: string) => api.post(endpoints.dlClearOverride(id), { element_code: code, value: 0, role, actor }),
    onSuccess: refresh, onError: (e: any) => alert(e?.detail ?? "Not permitted."),
  });

  const rows = useMemo(() => (cat?.elements ?? []).filter((e) =>
    (sheet === "All" || e.sheet_name === sheet) && (domain === "All" || e.domain === domain) &&
    (!q || e.label.toLowerCase().includes(q.toLowerCase()) || e.element_code.toLowerCase().includes(q.toLowerCase()))
  ), [cat, sheet, domain, q]);
  const selCodes = [...sel];
  const toggle = (c: string) => setSel((s) => { const n = new Set(s); n.has(c) ? n.delete(c) : n.add(c); return n; });

  const { data: dd } = useQuery<Drilldown>({ queryKey: ["drilldown", id, drill], enabled: !!drill, queryFn: () => api.get(endpoints.dfDrilldown(id, drill!)) });

  return (
    <div className="grid grid-cols-[1fr_300px] gap-4 items-start">
      <Panel eyebrow="Canonical elements" title="Governed value grid"
        actions={
          <div className="flex items-center gap-1.5">
            {cat && Object.entries(cat.summary).slice(0, 4).map(([s, n]) => <span key={s} className="flex items-center gap-1"><StatusPill status={s} /><span className="text-[10px] text-uq-mid">{n}</span></span>)}
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
            <Button variant="soft" disabled={!selCodes.length} onClick={() => bulk.mutate({ ep: endpoints.dlFreeze(id), codes: selCodes })}>Freeze</Button>
            <Button variant="soft" disabled={!selCodes.length} onClick={() => bulk.mutate({ ep: endpoints.dlSubmit(id), codes: selCodes })}>Submit</Button>
            <Button variant="ghost" disabled={!selCodes.length} onClick={() => bulk.mutate({ ep: endpoints.dlReopen(id), codes: selCodes })}>Reopen</Button>
          </>}
          {isChecker && <>
            <Button disabled={!selCodes.length} onClick={() => bulk.mutate({ ep: endpoints.dlApprove(id), codes: selCodes })}>Approve</Button>
            <Button variant="ghost" disabled={!selCodes.length} onClick={() => bulk.mutate({ ep: endpoints.dlReject(id), codes: selCodes })}>Reject</Button>
          </>}
        </div>
        <div className="overflow-auto max-h-[560px] border border-uq-border rounded-row">
          <table className="w-full text-[11px]">
            <thead className="sticky top-0 bg-uq-near-white">
              <tr className="text-left text-uq-purple">
                <th className="p-2 w-6"></th>
                {["Element", "Source", "System value", "Override", "Status", ""].map((h) => <th key={h} className="font-display font-extrabold uppercase text-[9px] tracking-wider p-2 border-b border-uq-border">{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {rows.map((e) => (
                <tr key={e.element_code} className="border-b border-uq-border/50 hover:bg-uq-alt-light">
                  <td className="p-2"><input type="checkbox" checked={sel.has(e.element_code)} onChange={() => toggle(e.element_code)} /></td>
                  <td className="p-2"><div className="text-uq-ink">{e.label}</div><div className="font-mono text-[9px] text-uq-lavender">{e.element_code}</div></td>
                  <td className="p-2 text-uq-muted text-[10px]">{e.source_system}<span className={`ml-1 ${e.domain === "Risk" ? "text-uq-magenta" : "text-uq-purple"}`}>· {e.domain}</span></td>
                  <td className="p-2 text-right num text-uq-mid">{money(e.raw_value)}</td>
                  <td className="p-2 text-right num">
                    {editing?.code === e.element_code ? (
                      <input autoFocus value={editing.value} onChange={(ev) => setEditing({ code: e.element_code, value: ev.target.value })}
                        onBlur={() => editMut.mutate({ code: e.element_code, value: Number(editing.value) })}
                        onKeyDown={(ev) => ev.key === "Enter" && editMut.mutate({ code: e.element_code, value: Number(editing.value) })}
                        className="w-24 rounded border border-uq-magenta px-1 py-0.5 text-right" />
                    ) : e.override_value != null ? (
                      <span className="text-uq-magenta font-semibold cursor-pointer" onClick={() => isMaker && e.editable && setEditing({ code: e.element_code, value: String(e.override_value) })}>{money(e.override_value)}</span>
                    ) : isMaker && e.editable ? (
                      <button className="text-[10px] text-uq-purple hover:underline" onClick={() => setEditing({ code: e.element_code, value: String(e.raw_value) })}>+ override</button>
                    ) : <span className="text-uq-lavender">—</span>}
                  </td>
                  <td className="p-2"><StatusPill status={e.status} /></td>
                  <td className="p-2 text-right whitespace-nowrap">
                    {e.override_value != null && isMaker && e.editable && <button className="text-[9px] text-uq-muted hover:text-crit mr-1" onClick={() => clearMut.mutate(e.element_code)}>clear</button>}
                    <button className="text-[10px] text-uq-purple hover:underline" onClick={() => setDrill(e.element_code)}>trace</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="text-[10px] text-uq-muted mt-1.5">
          {isMaker ? "Overrides are governed: the system value is preserved; submit for Checker approval. Frozen/certified rows must be reopened to amend."
            : isChecker ? "Select submitted elements and Approve/Reject. Approvals roll up to domain certification and auto-recompute the draft."
            : "Read-only — switch to Maker/Checker to act."}
        </div>
      </Panel>

      <Panel eyebrow="Sign-off" title="Sign-off queue" actions={<Badge tone="warn">{queue.length}</Badge>}>
        {queue.length === 0 && <div className="py-6 text-center text-[11px] text-uq-muted">Empty — Makers submit frozen values for Checker sign-off.</div>}
        <div className="flex flex-col gap-1.5">
          {queue.map((qr) => (
            <div key={qr.element_code} className="rounded-row border border-uq-border p-2 flex items-center justify-between">
              <div><div className="text-[11px] text-uq-ink">{qr.label}</div><div className="text-[9px] text-uq-muted uppercase tracking-wider">{qr.domain} · {qr.steward}</div></div>
              {isChecker && <Button onClick={() => bulk.mutate({ ep: endpoints.dlApprove(id), codes: [qr.element_code] })}>Approve</Button>}
            </div>
          ))}
        </div>
      </Panel>

      <Drawer open={!!drill} onClose={() => setDrill(null)} eyebrow="Raw → Processed lineage" title={dd?.label ?? "…"} width={500}>
        {dd && (
          <div className="text-[12px]">
            <div className="font-mono text-[10px] text-uq-lavender mb-1">{dd.element_code}</div>
            <div className="text-[11px] text-uq-mid mb-3">{dd.business_meaning}</div>
            {dd.override_value != null && (
              <div className="grid grid-cols-2 gap-2 mb-3">
                <div className="rounded-row border border-uq-border p-2"><div className="kpi-label">System value</div><div className="num text-uq-mid">{money(dd.raw_value ?? 0)}</div></div>
                <div className="rounded-row border border-uq-magenta p-2"><div className="kpi-label text-uq-magenta">Override</div><div className="num text-uq-magenta font-bold">{money(dd.override_value)}</div></div>
              </div>
            )}
            <div className="eyebrow mb-1.5">Transformation</div>
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
