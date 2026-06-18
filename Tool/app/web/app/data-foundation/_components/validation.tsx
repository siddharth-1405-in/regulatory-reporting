"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, RefreshCw, Upload, XCircle } from "lucide-react";
import { useRef } from "react";
import { AiBadge, Badge, Button, Panel } from "@/components/ui";
import { api, endpoints } from "@/lib/api";

type Finding = { severity: "error" | "warn" | "info"; message: string; element_code: string | null };

const CATEGORIES = ["Completeness", "Format & structure", "Duplicates"] as const;

function categorize(f: Finding): string {
  const m = f.message.toLowerCase();
  if (m.includes("incomplete") || m.includes("no ") || m.includes("missing") || m.includes("provided")) return "Completeness";
  if (m.includes("duplicate")) return "Duplicates";
  return "Format & structure";
}

const CATEGORY_DESC: Record<string, string> = {
  "Completeness": "All required data elements are present and non-null",
  "Format & structure": "Values conform to expected types, units, and date formats",
  "Duplicates": "No duplicate entries exist for the same data element",
};

const AI_RECS: Record<string, string> = {
  "Completeness": "Review source system connectivity or re-upload template with missing values populated.",
  "Format & structure": "Check that numeric values are in SAR '000 and dates follow DD/MM/YYYY format.",
  "Duplicates": "Remove duplicate rows from the upload template and re-upload.",
};

export function DataValidation({ id, onProceed }: { id: number; onProceed?: () => void }) {
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);

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
  const allClear = hasRun && issues.length === 0;

  const handleReupload = async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    await fetch(`/api${endpoints.ingestUpload(id)}`, { method: "POST", body: form });
    run.mutate();
  };

  return (
    <div className="flex flex-col gap-4">
      <Panel eyebrow="Data validation" title="Validation summary"
        actions={
          <div className="flex items-center gap-2">
            <AiBadge label="AI-assisted" />
            <Button variant="soft" onClick={() => run.mutate()} disabled={run.isPending}>
              <RefreshCw className={`w-3 h-3 mr-1 inline ${run.isPending ? "animate-spin" : ""}`} />
              {run.isPending ? "Running…" : hasRun ? "Re-run validation" : "Run validation"}
            </Button>
          </div>
        }>
        <p className="text-[11px] text-uq-muted mb-3">Every ingested input is checked for completeness, structure and duplicates before it can become a report-ready data element. Resolve issues by correcting source data or re-uploading the template.</p>
        <div className="grid grid-cols-3 gap-3 mb-4">
          <div className="panel p-3 flex items-center gap-2.5">
            <CheckCircle2 className="w-7 h-7 text-ok shrink-0" />
            <div><div className="font-display font-extrabold text-[22px] text-uq-dark-purple num">{hasRun ? `${categoriesClear}/${CATEGORIES.length}` : "—"}</div><div className="kpi-label">Quality checks passed</div></div>
          </div>
          <div className="panel p-3 flex items-center gap-2.5">
            <XCircle className={`w-7 h-7 shrink-0 ${errors.length ? "text-crit" : "text-uq-lavender"}`} />
            <div><div className={`font-display font-extrabold text-[22px] num ${errors.length ? "text-crit" : "text-uq-dark-purple"}`}>{errors.length}</div><div className="kpi-label">Exceptions found</div></div>
          </div>
          <div className="panel p-3 flex items-center gap-2.5">
            <AlertTriangle className={`w-7 h-7 shrink-0 ${warns.length ? "text-warn" : "text-uq-lavender"}`} />
            <div><div className={`font-display font-extrabold text-[22px] num ${warns.length ? "text-warn2" : "text-uq-dark-purple"}`}>{warns.length + errors.length}</div><div className="kpi-label">Records checked</div></div>
          </div>
        </div>

        <div className="eyebrow mb-1.5">Quality checks</div>
        <div className="grid grid-cols-3 gap-2 mb-1">
          {CATEGORIES.map((c) => {
            const n = byCategory(c);
            return (
              <div key={c} className={`rounded-row border p-2.5 ${n ? "border-uq-magenta/40 bg-uq-blush/40" : "border-uq-border"}`}>
                <div className={`font-display font-extrabold text-[18px] num ${n ? "text-uq-magenta" : "text-ok"}`}>{n || "✓"}</div>
                <div className="text-[10px] text-uq-muted font-display font-bold uppercase tracking-wider leading-tight mt-0.5">{c}</div>
                <div className="text-[9px] text-uq-muted mt-0.5 leading-snug">{CATEGORY_DESC[c]}</div>
              </div>
            );
          })}
        </div>
      </Panel>

      <Panel eyebrow="Detail" title="Records requiring attention"
        actions={
          <div className="flex items-center gap-2">
            <Badge tone={issues.length ? "warn" : "ok"}>{issues.length} open</Badge>
            {hasRun && issues.length > 0 && (
              <>
                <input ref={fileRef} type="file" accept=".xlsx,.csv" className="hidden"
                  onChange={(e) => { const f = e.target.files?.[0]; if (f) handleReupload(f); }} />
                <Button variant="ghost" onClick={() => fileRef.current?.click()} className="flex items-center gap-1">
                  <Upload className="w-3 h-3" /> Re-upload data
                </Button>
              </>
            )}
          </div>
        }>
        {!hasRun && <div className="py-8 text-center text-[11px] text-uq-muted">Run validation to check the ingested data.</div>}
        {allClear && <div className="py-8 text-center text-[12px] text-ok">All quality checks passed — inputs are ready for the Rule Engine.</div>}
        {issues.length > 0 && (
          <table className="w-full text-[11px]">
            <thead><tr className="text-left text-uq-purple">{["Severity", "Quality check", "Finding", "Element", "AI Recommendation"].map((h) => <th key={h} className="font-display font-extrabold uppercase text-[9px] tracking-wider pb-2 border-b border-uq-border">{h}</th>)}</tr></thead>
            <tbody>
              {issues.map((f, i) => {
                const cat = categorize(f);
                return (
                  <tr key={i} className="border-b border-uq-border/50 align-top">
                    <td className="py-2"><Badge tone={f.severity === "error" ? "crit" : "warn"}>{f.severity === "error" ? "Exception" : "Attention"}</Badge></td>
                    <td className="py-2 text-uq-mid">{cat}</td>
                    <td className="py-2 text-uq-ink">{f.message}</td>
                    <td className="py-2 font-mono text-[9px] text-uq-lavender">{f.element_code ?? "—"}</td>
                    <td className="py-2 text-[10px] text-uq-mid italic">
                      <span className="flex items-start gap-1"><AiBadge /><span>{AI_RECS[cat]}</span></span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </Panel>
    </div>
  );
}
