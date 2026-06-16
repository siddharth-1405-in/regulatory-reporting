"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { ArrowRight } from "lucide-react";
import { useRole } from "@/components/RoleContext";
import { Badge, Button, Panel } from "@/components/ui";
import { api, endpoints, type Catalogue } from "@/lib/api";

export function SubmissionSignoff({ id }: { id: number }) {
  const qc = useQueryClient();
  const router = useRouter();
  const { role, actor } = useRole();
  const isChecker = role === "Checker" || role === "Admin";

  const { data: cat } = useQuery({ queryKey: ["catalogue", id], queryFn: () => api.get<Catalogue>(endpoints.catalogue(id)) });
  const { data: queue = [] } = useQuery({ queryKey: ["signoff", id], queryFn: () => api.get<any[]>(endpoints.signoffQueue(id)) });
  const refresh = () => {
    ["catalogue", "signoff"].forEach((k) => qc.invalidateQueries({ queryKey: [k, id] }));
    qc.invalidateQueries({ queryKey: ["overview"] });
    qc.invalidateQueries({ queryKey: ["reportStatus", id] });
  };
  const act = useMutation({
    mutationFn: ({ ep, codes }: { ep: string; codes: string[] }) => api.post(ep, { element_codes: codes, role, actor }),
    onSuccess: refresh, onError: (e: any) => alert(e?.detail ?? "Action not permitted."),
  });

  const s = cat?.summary ?? {};
  const total = Object.values(s).reduce((a, b) => a + b, 0) || 1;
  const certified = s["certified"] ?? 0;
  const pct = Math.round((certified / total) * 100);
  const allSignedOff = certified === total && total > 0;
  const queueCodes = queue.map((q) => q.element_code);

  return (
    <div className="grid grid-cols-[1fr_320px] gap-4 items-start">
      <Panel eyebrow="Submission & sign-off" title="Checker review queue"
        actions={isChecker && queue.length > 0 && <Button onClick={() => act.mutate({ ep: endpoints.dlApprove(id), codes: queueCodes })}>Approve all ({queue.length})</Button>}>
        <p className="text-[11px] text-uq-muted mb-3">Makers submit report-ready data elements; Checkers sign off. Sign-off rolls up to Finance / Risk certification, which gates the report pack. Returned items are corrected upstream, not overwritten here.</p>
        {queue.length === 0
          ? <div className="py-10 text-center text-[12px] text-uq-muted">{allSignedOff ? "All report-ready data elements are signed off." : "No elements awaiting Checker review. Submit report-ready elements from the previous stage."}</div>
          : <table className="w-full text-[11px]">
            <thead><tr className="text-left text-uq-purple">{["Data element", "Domain", "Steward", "Submitted by", ""].map((h) => <th key={h} className="font-display font-extrabold uppercase text-[9px] tracking-wider pb-2 border-b border-uq-border">{h}</th>)}</tr></thead>
            <tbody>
              {queue.map((qr) => (
                <tr key={qr.element_code} className="border-b border-uq-border/50">
                  <td className="py-2 text-uq-ink">{qr.label}<div className="font-mono text-[9px] text-uq-lavender">{qr.element_code}</div></td>
                  <td className="py-2 text-uq-mid">{qr.domain}</td>
                  <td className="py-2 text-uq-muted">{qr.steward}</td>
                  <td className="py-2 text-uq-muted">{qr.submitted_by ?? "—"}</td>
                  <td className="py-2 text-right whitespace-nowrap">
                    {isChecker && <>
                      <Button className="mr-1" onClick={() => act.mutate({ ep: endpoints.dlApprove(id), codes: [qr.element_code] })}>Approve</Button>
                      <Button variant="ghost" onClick={() => act.mutate({ ep: endpoints.dlReject(id), codes: [qr.element_code] })}>Return</Button>
                    </>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>}
      </Panel>

      <div className="flex flex-col gap-4">
        <Panel eyebrow="Workflow" title="Readiness">
          <div className="flex items-end justify-between mb-1.5">
            <span className="font-display font-extrabold text-[28px] text-uq-dark-purple num">{pct}%</span>
            <Badge tone={allSignedOff ? "ok" : pct > 0 ? "warn" : "neutral"}>{allSignedOff ? "Signed off" : "In progress"}</Badge>
          </div>
          <div className="w-full h-[6px] rounded-pill bg-uq-light-lavender overflow-hidden mb-3">
            <div className={`h-full ${allSignedOff ? "bg-ok" : "bg-uq-magenta"}`} style={{ width: `${pct}%` }} />
          </div>
          <div className="flex flex-col gap-1.5">
            {[["Ready for submission", s["draft"] ?? 0], ["Submitted (pending checker)", s["submitted"] ?? 0], ["Returned for correction", (s["rejected"] ?? 0) + (s["invalidated"] ?? 0)], ["Signed off", certified]].map(([l, n]) => (
              <div key={l as string} className="flex items-center justify-between text-[11px]">
                <span className="text-uq-mid">{l as string}</span>
                <span className="num font-semibold text-uq-dark-purple">{n as number}</span>
              </div>
            ))}
          </div>
        </Panel>

        <Panel eyebrow="Next" title="Continue to reporting">
          <p className="text-[11px] text-uq-muted mb-2.5">Once data is signed off, the report-ready data elements feed the report pack for review, narrative and output.</p>
          <Button className="w-full justify-center flex items-center gap-1.5" disabled={certified === 0}
            onClick={() => router.push(`/report-pack/car/${id}`)}>
            Go to Report Pack <ArrowRight className="w-3.5 h-3.5" />
          </Button>
          {certified === 0 && <div className="text-[9.5px] text-uq-muted mt-1.5 text-center">Sign off at least one data element to proceed.</div>}
        </Panel>
      </div>
    </div>
  );
}
