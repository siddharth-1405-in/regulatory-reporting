"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useRole } from "@/components/RoleContext";
import { Badge, Button, Panel } from "@/components/ui";
import { api, endpoints, type RuleRow } from "@/lib/api";

const SHEETS = ["All", "Schedule 1", "Schedule 2", "Schedule 3", "Schedule 4"];
const tagTone: Record<string, any> = { system: "neutral", "user-edited": "magenta" };

export function RuleEngine({ id }: { id: number }) {
  const qc = useQueryClient();
  const { role, actor } = useRole();
  const canEdit = role === "Maker" || role === "Admin";
  const { data = [] } = useQuery({ queryKey: ["rules", id], queryFn: () => api.get<RuleRow[]>(endpoints.rules(id)) });
  const [sheet, setSheet] = useState("Schedule 2");
  const [edit, setEdit] = useState<{ key: string; value: string } | null>(null);

  const editMut = useMutation({
    mutationFn: ({ key, value }: { key: string; value: number }) => api.post(endpoints.ruleEdit(id), { key, value, role, actor }),
    onSuccess: () => { setEdit(null); qc.invalidateQueries({ queryKey: ["rules", id] }); qc.invalidateQueries({ queryKey: ["reportStatus", id] }); qc.invalidateQueries({ queryKey: ["overview"] }); },
    onError: (e: any) => { setEdit(null); alert(e?.detail ?? "Edit not permitted."); },
  });

  const rows = useMemo(() => data.filter((r) => sheet === "All" || r.sheet_name === sheet), [data, sheet]);

  return (
    <Panel eyebrow="Transformation logic" title="Rule engine"
      actions={<div className="flex gap-1">{SHEETS.map((s) => <button key={s} onClick={() => setSheet(s)} className={`chip ${sheet === s ? "bg-uq-purple text-white" : "bg-uq-alt-light text-uq-mid"}`}>{s.replace("Schedule ", "S")}</button>)}</div>}>
      <p className="text-[11px] text-uq-muted mb-2">Plain-English transformation rules over the report inputs. Editing a parameter automatically recalculates the downstream report-ready data elements — no sign-off applies to rules themselves. {canEdit ? "" : "Switch to Maker to edit."}</p>
      <div className="overflow-auto max-h-[560px] border border-uq-border rounded-row">
        <table className="w-full text-[11px]">
          <thead className="sticky top-0 bg-uq-near-white"><tr className="text-left text-uq-purple">
            {["Element", "Type", "Rule (plain English)", "Parameters", "Provenance"].map((h) => <th key={h} className="font-display font-extrabold uppercase text-[9px] tracking-wider p-2 border-b border-uq-border">{h}</th>)}
          </tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.element_code} className="border-b border-uq-border/50 hover:bg-uq-alt-light align-top">
                <td className="p-2"><div className="text-uq-ink">{r.label}</div><div className="font-mono text-[9px] text-uq-lavender">{r.element_code}</div></td>
                <td className="p-2"><Badge tone="purple">{r.rule_type}</Badge></td>
                <td className="p-2 text-uq-mid leading-snug">{r.plain_english}<div className="text-[9px] text-uq-lavender mt-0.5">{r.origin}</div></td>
                <td className="p-2">
                  {r.editable_params.length === 0 && <span className="text-uq-lavender text-[10px]">—</span>}
                  <div className="flex flex-col gap-1">
                    {r.editable_params.map((p) => (
                      <div key={p.key} className="flex items-center gap-1.5">
                        <span className="text-[9px] text-uq-muted uppercase tracking-wider">{p.label}</span>
                        {edit?.key === p.key ? (
                          <input autoFocus value={edit.value} onChange={(e) => setEdit({ key: p.key, value: e.target.value })}
                            onBlur={() => editMut.mutate({ key: p.key, value: Number(edit.value) })}
                            onKeyDown={(e) => e.key === "Enter" && editMut.mutate({ key: p.key, value: Number(edit.value) })}
                            className="w-16 rounded border border-uq-magenta px-1 py-0.5 text-right text-[10px]" />
                        ) : (
                          <span className={`num text-[11px] ${canEdit ? "text-uq-purple cursor-pointer hover:text-uq-magenta" : "text-uq-ink"}`}
                            onClick={() => canEdit && setEdit({ key: p.key, value: String(p.value) })}>{(p.value * 100).toFixed(2)}%</span>
                        )}
                      </div>
                    ))}
                  </div>
                </td>
                <td className="p-2"><Badge tone={tagTone[r.tag] ?? "neutral"}>{r.tag}</Badge></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}
