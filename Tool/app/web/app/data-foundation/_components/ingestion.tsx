"use client";
import { useQuery } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { Download, Plug, Upload } from "lucide-react";
import { Drawer } from "@/components/Drawer";
import { Badge, Button, Panel, StatusDot } from "@/components/ui";
import { api, endpoints, type SourceSystem } from "@/lib/api";
import { relTime } from "@/lib/format";

export function DataIngestion() {
  const { data = [] } = useQuery({ queryKey: ["sources"], queryFn: () => api.get<SourceSystem[]>(endpoints.sources) });
  const [drill, setDrill] = useState<SourceSystem | null>(null);
  const { data: datasets = [] } = useQuery({
    queryKey: ["datasets", drill?.code], enabled: !!drill,
    queryFn: () => api.get<any[]>(endpoints.sourceDatasets(drill!.code)),
  });
  const used = data.filter((s) => s.used_in_car);
  const avail = data.filter((s) => !s.used_in_car);
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploaded, setUploaded] = useState<string | null>(null);

  return (
    <div className="grid grid-cols-[1fr_340px] gap-4 items-start">
      {/* Option A — connect to source systems */}
      <Panel eyebrow="Option A · Live connection" title="Connect to a source system"
        actions={<Badge tone="ok"><StatusDot tone="ok" /> {used.length} connected</Badge>}>
        <p className="text-[11px] text-uq-muted mb-2.5">Report inputs are pulled directly from governed enterprise systems. Open a system to review the datasets and fields it supplies.</p>
        <div className="grid grid-cols-2 gap-2.5">
          {used.map((s) => (
            <button key={s.code} onClick={() => setDrill(s)} className="text-left rounded-row border border-uq-border p-2.5 hover:border-uq-magenta hover:bg-uq-alt-light transition">
              <div className="flex items-center justify-between mb-1">
                <span className="font-display font-extrabold text-[12.5px] text-uq-dark-purple">{s.name}</span>
                <Badge tone={s.status === "connected" ? "ok" : "crit"}><StatusDot tone={s.status === "connected" ? "ok" : "crit"} /> {s.status}</Badge>
              </div>
              <div className="text-[10px] text-uq-muted mb-1">{s.vendor} · {s.category}</div>
              <div className="text-[10.5px] text-uq-mid leading-snug mb-1.5">{s.coverage}</div>
              <div className="flex items-center justify-between text-[9px] text-uq-muted uppercase tracking-wider">
                <span>{s.car_elements} elements</span>
                <span>ingested {s.last_ingest_at ? relTime(s.last_ingest_at) : "—"}</span>
              </div>
            </button>
          ))}
        </div>
        {avail.length > 0 && (
          <>
            <div className="eyebrow mt-3 mb-1.5">Available — not connected for this report</div>
            <div className="flex flex-wrap gap-1.5">
              {avail.map((s) => (
                <span key={s.code} className="rounded-row border border-uq-border px-2 py-1 text-[10px] text-uq-muted bg-uq-near-white">
                  <Plug className="inline w-3 h-3 mr-1 -mt-0.5" />{s.name} · {s.vendor}
                </span>
              ))}
            </div>
          </>
        )}
      </Panel>

      {/* Option B — controlled template intake */}
      <Panel eyebrow="Option B · Controlled intake" title="Upload via template">
        <p className="text-[11px] text-uq-muted mb-3">The governed fallback when no live source connection is used. Download the standard intake template, complete it, and upload it for validation.</p>
        <div className="flex flex-col gap-2">
          <a href={endpoints.sources} download
            onClick={(e) => { e.preventDefault(); alert("Demo: the CAR-SA-01 intake template would download here."); }}>
            <Button variant="soft" className="w-full justify-center flex items-center gap-1.5"><Download className="w-3.5 h-3.5" /> Download intake template</Button>
          </a>
          <input ref={fileRef} type="file" accept=".xlsx,.csv" className="hidden"
            onChange={(e) => setUploaded(e.target.files?.[0]?.name ?? null)} />
          <Button className="w-full justify-center flex items-center gap-1.5" onClick={() => fileRef.current?.click()}>
            <Upload className="w-3.5 h-3.5" /> Upload completed template
          </Button>
        </div>
        <div className="rounded-row bg-uq-alt-light p-2.5 mt-3 text-[10.5px] text-uq-mid">
          {uploaded
            ? <span><span className="font-semibold text-uq-dark-purple">{uploaded}</span> received — queued for the Data Validation stage.</span>
            : "Uploads are treated as a controlled reporting intake: every template is validated before it can feed the report-ready data elements."}
        </div>
      </Panel>

      <Drawer open={!!drill} onClose={() => setDrill(null)} eyebrow={drill?.vendor} title={`${drill?.name} · datasets`} width={520}>
        {drill && (
          <div>
            <div className="text-[11px] text-uq-mid mb-3">{drill.coverage}</div>
            <table className="w-full text-[11px]">
              <thead><tr className="text-left text-uq-purple">{["Element", "Schedule", "Source field"].map((h) => <th key={h} className="font-display font-extrabold uppercase text-[9px] tracking-wider pb-1.5 border-b border-uq-border">{h}</th>)}</tr></thead>
              <tbody>
                {datasets.map((d) => (
                  <tr key={d.element_code} className="border-b border-uq-border/40">
                    <td className="py-1.5 text-uq-ink">{d.label}<div className="font-mono text-[9px] text-uq-lavender">{d.element_code}</div></td>
                    <td className="py-1.5 text-uq-muted">{d.sheet_name}</td>
                    <td className="py-1.5 font-mono text-[9px] text-uq-purple">{d.source_field}</td>
                  </tr>
                ))}
                {datasets.length === 0 && <tr><td colSpan={3} className="py-6 text-center text-uq-muted">Contributes rule inputs (ratings / aggregation), not a primary record.</td></tr>}
              </tbody>
            </table>
          </div>
        )}
      </Drawer>
    </div>
  );
}
