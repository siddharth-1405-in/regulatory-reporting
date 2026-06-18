# Architecture — Agentic CAR Reporting Platform

A governed, deterministic CAR-SA-01 reporting product with a supervised agentic
layer. **Every regulatory figure is computed by deterministic code.** AI is
confined to analysis, diagnosis, proposal, narrative and circular parsing — it
never calculates, certifies, signs off, exports or mutates material report state
without Checker approval.

## Layers

```
Frontend (Next.js 14, TS, Tailwind, TanStack Table, React Query)
  └── Uniqus design language (purple/magenta, Montserrat/Inter, dense cockpit)
        │  REST /api/*
Backend (FastAPI, Python 3.11)
  ├── registry/car_sa01     canonical element registry (truth) — elements,
  │                         parameters, cell_map (repairs broken workbook refs)
  ├── calc/                 deterministic engine (pure functions, Decimal)
  ├── services/             report instance, ingestion, dq, ownership,
  │                         certification, calc orchestration, validation,
  │                         lineage, remediation, export, audit, config
  ├── agents/               anomaly · remediation · narrative · circular_parsing
  │                         (LangGraph-ready; Claude with deterministic fallback)
  └── models/               SQLAlchemy 2.x  →  PostgreSQL (Alembic)
```

## Why the registry is the source of truth
The supplied `SAMA_CAR_SA01_Template.xlsx` has **internally inconsistent
cross-sheet formulas** (Summary points at a stale Schedule-1 layout; Total RWA
sums the wrong cells; the Schedule 6 nil check subtracts the wrong row). The
engine therefore computes semantically from the canonical registry and the
Excel export writes computed **values** into the template, repairing those
references (`registry/car_sa01/cell_map.py`).

## Workflow (Draft → signed off)
An instance starts in **Draft** — data ingested and quality-checked, but **not
certified** (all elements "Ready for submission"). The maker submits report-ready
elements; a Checker signs them off, which **rolls up** to Finance/Risk domain
certification, opens the calc gate, and **auto-recomputes** the draft (no "Run"
button). Schedule → Summary sign-off in the Report Pack is a separate attestation
layered on top. The seeded demo deliberately ships in this Draft state so the
full governed workflow is demonstrated end to end.

## Governance invariants (enforced in services)
- **Certification gate** — no `CalcRun` until Finance **and** Risk certify their
  owned elements (`certification_service.is_calc_allowed`). Element sign-off
  (`data_layer_service.approve`) rolls up to domain certification, then triggers
  `calc_service.ensure_current` (recompute + governed agents).
- **Invalidation** — any input change invalidates the owning domain's
  certification, re-blocks calculation, and auto-reopens affected schedule sign-offs.
- **Agent containment** — agents write only `agent_run` / `remediation_proposal`
  / `narrative`. A `RemediationProposal` is applied only when a **Checker**
  approves it (`remediation_service.approve`), which re-certifies and recalculates.
  The narrative is regenerated **in place** (one EN + one AR row); once approved it
  is injected at the top of the PDF and Excel exports.
- **Export is ungated** — Excel and PDF can be produced at any time; the output
  carries a **Draft / Signed Off** badge (no hard gate on sign-off).
- **Audit** — every material action is appended to `audit_log`.

## The seeded scenario
A Q4-2025 instance carries a Schedule 2 corporate-exposure data error
(105,000,000 vs ~9,500,000 at 100% risk weight). This inflates Total RWA to
187.5bn, drops the CET1 ratio to 7.73%, **breaches** the combined buffer, and
trips three validations including `CREDIT_CONCENTRATION_ANOMALY`. The anomaly
agent surfaces it, the remediation agent proposes a correction (pending), and
Checker approval restores compliance and clears all failing rules.

See `docs/FSD.md`, `docs/TDD.md`, and `tool/app/README.md` (run instructions).
