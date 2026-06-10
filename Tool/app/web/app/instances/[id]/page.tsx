import { redirect } from "next/navigation";

// Legacy route — the per-instance workspace now lives under Report Pack.
export default function LegacyInstanceRedirect({ params }: { params: { id: string } }) {
  redirect(`/report-pack/car/${params.id}`);
}
