const BASE = "/api";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail: any = null;
    try { detail = await res.json(); } catch {}
    const err: any = new Error(`${res.status} ${res.statusText}`);
    err.detail = detail?.detail ?? detail;
    err.status = res.status;
    throw err;
  }
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(p: string) => req<T>(p),
  post: <T>(p: string, body?: unknown) =>
    req<T>(p, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
};

const DF = (id: number) => `/instances/${id}/data-foundation`;
export const endpoints = {
  // platform
  overview: "/platform/overview",
  packs: "/platform/packs",
  // sources + rules
  sources: "/sources",
  sourceDatasets: (code: string) => `/sources/${code}/datasets`,
  rules: (id: number) => `/instances/${id}/rules`,
  ruleEdit: (id: number) => `/instances/${id}/rules/edit`,
  // data foundation
  catalogue: (id: number) => `${DF(id)}/catalogue`,
  signoffQueue: (id: number) => `${DF(id)}/signoff-queue`,
  dfDrilldown: (id: number, code: string) => `${DF(id)}/drilldown/${code}`,
  dlEdit: (id: number) => `${DF(id)}/edit`,
  dlClearOverride: (id: number) => `${DF(id)}/clear-override`,
  dlFreeze: (id: number) => `${DF(id)}/freeze`,
  dlReopen: (id: number) => `${DF(id)}/reopen`,
  dlSubmit: (id: number) => `${DF(id)}/submit`,
  dlApprove: (id: number) => `${DF(id)}/approve`,
  dlReject: (id: number) => `${DF(id)}/reject`,
  // report pack
  reportStatus: (id: number) => `/instances/${id}/report/status`,
  reportSchedule: (id: number, key: string) => `/instances/${id}/report/schedule/${key}`,
  reportSignoff: (id: number, key: string) => `/instances/${id}/report/schedule/${key}/signoff`,
  reportExceptions: (id: number) => `/instances/${id}/report/exceptions`,
  exceptionMakerAction: (id: number) => `/instances/${id}/report/exceptions/maker-action`,
  exceptionCheckerDecision: (id: number) => `/instances/${id}/report/exceptions/checker-decision`,
  instances: "/instances",
  instance: (id: number) => `/instances/${id}`,
  certifications: (id: number) => `/instances/${id}/certifications`,
  calc: (id: number) => `/instances/${id}/calc`,
  validation: (id: number) => `/instances/${id}/validation`,
  agents: (id: number) => `/instances/${id}/agents`,
  remediations: (id: number) => `/instances/${id}/remediations`,
  narratives: (id: number) => `/instances/${id}/narratives`,
  circulars: (id: number) => `/instances/${id}/circulars`,
  dq: (id: number) => `/instances/${id}/dq`,
  audit: (id: number) => `/instances/${id}/audit`,
  inputs: (id: number) => `/instances/${id}/inputs`,
};

// ---- shared types -----------------------------------------------------------
export type Instance = {
  id: number; period_label: string; period_end: string; bank_name: string;
  currency: string; units: string; status: string; created_at: string;
};
export type Metrics = Record<string, number>;
export type Flags = Record<string, string>;
export type CalcResult = {
  schedules: Record<string, { lines: Line[]; subtotals: Record<string, number>; totals: Record<string, number> }>;
  values: Record<string, number>; metrics: Metrics; flags: Flags;
};
export type Line = { element_code: string; label: string; section: string; inputs: Record<string, number>; result: number };
export type Validation = { rule_code: string; status: "pass" | "warn" | "fail"; message: string; elements: string[]; remediation_hint: string };
export type AgentRun = {
  id: number; agent_type: string; reasoning_summary: string; confidence: number;
  evidence_used: any[]; impacted_metrics: string[]; proposed_action: string;
  approval_required: boolean; prompt_version: string; model_version: string;
  status: string; output: any; created_at: string;
};
export type Remediation = { id: number; element_code: string; current_value: number; proposed_value: number; rationale: string; status: string; checker?: string; agent_run_id: number };
export type Narrative = { id: number; language: string; version: number; body: string; citations: any; confidence: number; status: string };
export type Pack = { code: string; name: string; regulator: string; frequency: string; status: string; schedules: number };
export type PlatformOverview = {
  metrics: { active_reports: number; uncertified_data: number; in_remediation: number; ready_for_preview: number; signed_off: number; active_packs: number };
  source_health: { connected: number; used_in_car: number; total: number; degraded: number };
  sources: SourceSystem[];
  packs: Pack[];
  instances: { id: number; pack: string; period_label: string; period_end: string; bank_name: string; status: string; report_status: string; buffer_status: string | null; failing_rules: number; blocking_domains: string[]; open_remediations: number; data_readiness: number; report_readiness: number }[];
};
export type ElementStatus = "draft" | "edited" | "frozen" | "submitted" | "certified" | "rejected" | "invalidated";
export type DataElement = {
  element_code: string; label: string; sheet_name: string; section: string;
  domain: string; business_meaning: string; source_system: string; source_code: string;
  source_field: string; source_type: string;
  raw_value: number; override_value: number | null; value: number;
  status: ElementStatus; editable: boolean; has_override: boolean;
  last_updated_by: string; last_approved_by: string | null;
  dependent_packs: string[]; dependent_schedules: string[];
};
export type Catalogue = { elements: DataElement[]; summary: Record<string, number> };
export type SourceSystem = { code: string; name: string; vendor: string; category: string; status: string; used_in_car: boolean; steward: string; coverage: string; last_ingest_at: string | null; car_elements: number };
export type RuleRow = { element_code: string; label: string; sheet_name: string; domain: string; rule_name: string; rule_type: string; plain_english: string; editable_params: { key: string; label: string; value: number; format: string }[]; origin: string; editable: boolean; tag: string };
export type ScheduleView = { key: string; label: string; status: string; can_signoff: boolean; blocked_reason: string; domains: string[]; signed_by: string | null; signed_at: string | null; comment: string };
export type ReportStatus = { report_status: string; metrics: Metrics | null; flags: Flags | null; last_computed: string | null; schedules: ScheduleView[] };
export type ScheduleDetail = { key: string; lines: (Line & { business_meaning: string; computation: string })[]; totals: Record<string, number>; values: Record<string, number>; available: boolean };
export type ExceptionProposal = { id: number; element_code: string; current_value: number; proposed_value: number; rationale: string; status: string; maker_rationale: string; checker: string | null; checker_comment: string };
export type ExceptionItem = { rule_code: string; issue: string; impacted_schedule: string; impacted_elements: string[]; remediation_hint: string; ai_root_cause: string; ai_recommendation: string; proposal: ExceptionProposal | null };
export type Drilldown = { element_code: string; label: string; business_meaning: string; source: { source_name: string; source_field: string }; raw_value: number | null; override_value: number | null; effective_value: number; processed_value: number | null; rule: RuleRow; steps: { step: string; detail: string; value: number | null }[]; domain: string; status: string; lineage_upstream: string[] };
