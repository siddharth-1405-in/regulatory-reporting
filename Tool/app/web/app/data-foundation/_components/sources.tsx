"use client";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Drawer } from "@/components/Drawer";
import { Badge, Panel, StatusDot } from "@/components/ui";
import { api, endpoints, type SourceSystem } from "@/lib/api";
import { relTime } from "@/lib/format";

export function SourceSystems() {
  const { data = [] } = useQuery({ queryKey: ["sources"], queryFn: () => api.get<SourceSystem[]>(endpoints.sources) });
  const [drill, setDrill] = useState<SourceSystem | null>(null);
  const { data: datasets = [] } = useQuery({
    queryKey: ["datasets", drill?.code], enabled: !!drill,
    queryFn: () => api.get<any[]>(endpoints.sourceDatasets(drill!.code)),
  });
  const used = data.filter((s) => s.used_in_car);
  const avail = data.filter((s) => !s.used_in_car);

  return (
    <div className="flex flex-col gap-4">
      <Panel eyebrow="Connected" title="Source systems feeding CAR" actions={<Badge tone="ok"><StatusDot tone="ok" /> {used.length} connected</Badge>}>
        <div className="grid grid-cols-3 gap-3">
          {used.map((s) => (
            <button key={s.code} onClick={() => setDrill(s)} className="text-left rounded-row border border-uq-border p-3 hover:bg-uq-alt-light transition">
              <div className="flex items-center justify-between mb-1">
                <span className="font-display font-extrabold text-[13px] text-uq-dark-purple">{s.name}</span>
                <Badge tone={s.status === "connected" ? "ok" : "crit"}><StatusDot tone={s.status === "connected" ? "ok" : "crit"} /> {s.status}</Badge>
              </div>
              <div className="text-[10px] text-uq-muted mb-1.5">{s.vendor} · {s.category}</div>
              <div className="text-[11px] text-uq-mid leading-snug mb-2">{s.coverage}</div>
              <div className="flex items-center justify-between text-[9.5px] text-uq-muted uppercase tracking-wider">
                <span>{s.car_elements} elements</span>
                <span>fresh {s.last_ingest_at ? relTime(s.last_ingest_at) : "—"}</span>
              </div>
              <div className="text-[9px] text-uq-lavender mt-1">Steward · {s.steward}</div>
            </button>
          ))}
        </div>
      </Panel>

      <Panel eyebrow="Catalogue" title="Available systems (not used in CAR demo)">
        <div className="grid grid-cols-4 gap-2">
          {avail.map((s) => (
            <div key={s.code} className="rounded-row border border-uq-border p-2.5 opacity-75">
              <div className="font-display font-bold text-[11.5px] text-uq-dark-purple">{s.name}</div>
              <div className="text-[10px] text-uq-muted">{s.vendor} · {s.category}</div>
              <Badge tone="neutral">available</Badge>
            </div>
          ))}
        </div>
      </Panel>

      <Drawer open={!!drill} onClose={() => setDrill(null)} eyebrow={drill?.vendor} title={`${drill?.name} · CAR datasets`} width={520}>
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
                {datasets.length === 0 && <tr><td colSpan={3} className="py-6 text-center text-uq-muted">Contributes rule inputs (ratings/aggregation), not a primary record.</td></tr>}
              </tbody>
            </table>
          </div>
        )}
      </Drawer>
    </div>
  );
}
