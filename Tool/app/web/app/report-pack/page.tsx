"use client";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Badge, Button, Panel, StatusDot } from "@/components/ui";
import { api, endpoints, type PlatformOverview } from "@/lib/api";

const statusTone: Record<string, any> = {
  VALIDATED: "magenta", REMEDIATION: "warn", SIGNED_OFF: "ok", EXPORTED: "ok", DRAFT: "neutral", INGESTED: "purple",
};

export default function ReportPacks() {
  const router = useRouter();
  const { data } = useQuery({ queryKey: ["overview"], queryFn: () => api.get<PlatformOverview>(endpoints.overview) });
  const car = data?.packs.find((p) => p.code === "CAR-SA-01");
  const planned = data?.packs.filter((p) => p.status !== "active") ?? [];

  return (
    <div className="p-6 max-w-[1400px] mx-auto">
      <div className="eyebrow mb-1">Report Packs</div>
      <h1 className="font-display font-extrabold text-uq-dark-purple text-[22px] tracking-tight mb-4">Report-specific workspaces</h1>

      <Panel eyebrow="Active" title={`${car?.name} (${car?.code})`}
        actions={<Badge tone="ok"><StatusDot tone="ok" /> Active · {car?.schedules} schedules</Badge>} className="mb-4">
        <table className="w-full text-[12px]">
          <thead><tr className="text-left text-uq-purple">
            {["Period", "Bank", "Status", "Buffer", "Issues", ""].map((h) => <th key={h} className="font-display font-extrabold uppercase text-[9px] tracking-wider pb-2 border-b border-uq-border">{h}</th>)}
          </tr></thead>
          <tbody>
            {data?.instances.map((i) => (
              <tr key={i.id} className="border-b border-uq-border/60 hover:bg-uq-alt-light cursor-pointer" onClick={() => router.push(`/report-pack/car/${i.id}`)}>
                <td className="py-2.5 font-semibold text-uq-ink">{i.period_label}</td>
                <td className="text-uq-mid">{i.bank_name}</td>
                <td><Badge tone={statusTone[i.status] ?? "neutral"}>{i.status}</Badge></td>
                <td>{i.buffer_status ? <Badge tone={i.buffer_status === "Breach" ? "crit" : "ok"}>{i.buffer_status}</Badge> : "—"}</td>
                <td>{i.failing_rules > 0 ? <span className="text-crit text-[11px] font-semibold">{i.failing_rules} failing</span> : <span className="text-ok text-[11px]">clean</span>}</td>
                <td className="text-right"><Button variant="ghost">Open CAR ›</Button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>

      <div className="eyebrow mb-2">Planned packs · same canonical Data Layer</div>
      <div className="grid grid-cols-3 gap-3">
        {planned.map((p) => (
          <div key={p.code} className="panel p-3.5 opacity-80">
            <div className="flex items-center justify-between mb-1">
              <span className="font-display font-bold text-[13px] text-uq-dark-purple">{p.name}</span>
              <Badge tone="neutral">Planned</Badge>
            </div>
            <div className="text-[10px] text-uq-muted">{p.regulator} · {p.frequency} · {p.code}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
