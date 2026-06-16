"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, XCircle } from "lucide-react";
import { Badge, Button, Panel } from "@/components/ui";
import { api, endpoints } from "@/lib/api";

type Finding = { severity: "error" | "warn" | "info"; message: string; element_code: string | null };

const CATEGORIES = ["Completeness", "Format & structure", "Duplicates", "Value integrity", "Mapping"] as const;

// Map a raw DQ finding into a business-friendly validation category.
function categorize(f: Finding): string {
  const m = f.message.toLowerCase();
  if (m.includes("negative") || m.includes("invalid") || m.includes("integrity")) return "Value integrity";
  if (m.includes("incomplete") || m.includes("no ") || m.includes("missing") || m.includes("provided")) return "Completeness";
  if (m.includes("duplicate")) return "Duplicates";
  if (m.includes("format") || m.includes("unit") || m.includes("date")) return "Format & structure";
  if (m.includes("map")) return "Mapping";
  return "Value integrity";
}

export function DataValidation({ id }: { id: number }) {
  const qc = useQueryClient();
  const { data: findings = [] } = useQuery({ queryKey: ["dq", id], queryFn: () => api.get<Finding[]>(endpoints.dq(id)) });
  const run = useMutation({
    mutationFn: () => api.post(endpoints.dqRun(id)),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["dq", id] }),
  });

  const issues = findings.filter((f) => f.severity !== "info");
  const errors = issues.filter((f) => f.severity === "error");
  const warns = issues.filter((f) => f.severity === "warn");
  const hasRun = findings.length > 0;
  const byCategory = (cat: string) => issues.filter((f) => categorize(f) === cat).length;
  const categoriesClear = CATEGORIES.filter((c) => byCategory(c) === 0).length;

  return (
    <div className="flex flex-col gap-4">
      <Panel eyebrow="Data validation" title="Validation summary"
        actions={<Button variant="soft" onClick={() => run.mutate()} disabled={run.isPending}>{run.isPending ? "Running…" : hasRun ? "Re-run validation" : "Run validation"}</Button>}>
        <p className="text-[11px] text-uq-muted mb-3">Every ingested input is checked for completeness, structure and integrity before it can become a report-ready data element. Resolve exceptions through corrected ingestion data or rule parameters.</p>
        <div className="grid grid-cols-3 gap-3 mb-4">
          <div className="panel p-3 flex items-center gap-2.5">
            <CheckCircle2 className="w-7 h-7 text-ok shrink-0" />
            <div><div className="font-display font-extrabold text-[22px] text-uq-dark-purple num">{hasRun ? `${categoriesClear}/${CATEGORIES.length}` : "—"}</div><div className="kpi-label">Categories clear</div></div>
          </div>
          <div className="panel p-3 flex items-center gap-2.5">
            <XCircle className={`w-7 h-7 shrink-0 ${errors.length ? "text-crit" : "text-uq-lavender"}`} />
            <div><div className={`font-display font-extrabold text-[22px] num ${errors.length ? "text-crit" : "text-uq-dark-purple"}`}>{errors.length}</div><div className="kpi-label">Exceptions found</div></div>
          </div>
          <div className="panel p-3 flex items-center gap-2.5">
            <AlertTriangle className={`w-7 h-7 shrink-0 ${warns.length ? "text-warn" : "text-uq-lavender"}`} />
            <div><div className={`font-display font-extrabold text-[22px] num ${warns.length ? "text-warn2" : "text-uq-dark-purple"}`}>{warns.length}</div><div className="kpi-label">Records to attend</div></div>
          </div>
        </div>
        <div className="eyebrow mb-1.5">Validation categories</div>
        <div className="grid grid-cols-5 gap-2">
          {CATEGORIES.map((c) => {
            const n = byCategory(c);
            return (
              <div key={c} className={`rounded-row border p-2.5 ${n ? "border-uq-magenta/40 bg-uq-blush/40" : "border-uq-border"}`}>
                <div className={`font-display font-extrabold text-[18px] num ${n ? "text-uq-magenta" : "text-ok"}`}>{n || "✓"}</div>
                <div className="text-[9.5px] text-uq-muted uppercase tracking-wider leading-tight mt-0.5">{c}</div>
              </div>
            );
          })}
        </div>
      </Panel>

      <Panel eyebrow="Detail" title="Records requiring attention" actions={<Badge tone={issues.length ? "warn" : "ok"}>{issues.length} open</Badge>}>
        {!hasRun && <div className="py-8 text-center text-[11px] text-uq-muted">Run validation to check the ingested data.</div>}
        {hasRun && issues.length === 0 && <div className="py-8 text-center text-[12px] text-ok">All data quality checks passed — inputs are ready for the rule engine.</div>}
        {issues.length > 0 && (
          <table className="w-full text-[11px]">
            <thead><tr className="text-left text-uq-purple">{["Severity", "Category", "Finding", "Element"].map((h) => <th key={h} className="font-display font-extrabold uppercase text-[9px] tracking-wider pb-2 border-b border-uq-border">{h}</th>)}</tr></thead>
            <tbody>
              {issues.map((f, i) => (
                <tr key={i} className="border-b border-uq-border/50">
                  <td className="py-2"><Badge tone={f.severity === "error" ? "crit" : "warn"}>{f.severity === "error" ? "Exception" : "Attention"}</Badge></td>
                  <td className="py-2 text-uq-mid">{categorize(f)}</td>
                  <td className="py-2 text-uq-ink">{f.message}</td>
                  <td className="py-2 font-mono text-[9px] text-uq-lavender">{f.element_code ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>
    </div>
  );
}
