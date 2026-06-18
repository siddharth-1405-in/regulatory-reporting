# Technical Design Document
## Agentic CAR Regulatory Reporting Platform — current build

> Describes the system **as implemented**. Single canonical TDD — the duplicate
> under `Tool/` has been removed. Companion docs: `docs/FSD.md`, `docs/ARCHITECTURE.md`,
> run guide `Tool/app/README.md`, session source-of-truth `CLAUDE.md`.

## 1. Stack (as built)
### Frontend (`Tool/app/web`)
- Next.js 14 (App Router) · TypeScript · Tailwind CSS · TanStack Query/Table · lucide-react
- Custom Uniqus-token UI components (`components/ui.tsx`) — not shadcn
- `/api/*` proxied to the backend via `next.config.mjs` rewrites
- **OneDrive note:** `next dev` breaks on a OneDrive-synced path; use the production build (`rm -rf .next && npm run build && npx next start`).

### Backend (`Tool/app/api`)
- FastAPI · Python 3.11+ · SQLAlchemy 2.x · Alembic · Pydantic v2
- openpyxl (Excel) · **fpdf2** (PDF — pure Python, no OS deps; replaced WeasyPrint)
- LangGraph-ready agents · Anthropic Claude (with deterministic fallback)

### Data
- PostgreSQL (database `car`); SQLite for tests (`conftest.py`)
- Connection in `Tool/app/api/.env`: `DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/car`; optional `ANTHROPIC_API_KEY`

## 2. Backend layout (`Tool/app/api/app/`)
- `registry/car_sa01/` — **the heart**: `elements.py` (168 elements: 142 input + derived), `parameters.py` (risk weights/CCFs/betas/×12.5/buffers/minimums/CCB bands), `cell_map.py` (export targets + repairs), `sources.py`, `rules.py`, `sample_data.py` (baseline + the Schedule-2 anomaly).
- `calc/` — deterministic engine: `engine.py` + `calc_schedule_1..6` + `calc_summary` + `types.py`. Pure functions, `Decimal`, no DB.
- `services/` — `report_instance_service`, `ingestion_service`, `dq_service`, `ownership_service`, `certification_service` (domain gate + element roll-up + invalidation), `calc_service` (`run_calculation`, `ensure_current`), `validation_service`, `lineage_service`, `data_layer_service` (catalogue, override, drilldown, element maker-checker, **S5 derived rows**), `sources_service`, `rules_service` (**incl. S5 buffer-rate rules**), `report_signoff_service` (schedule/Summary sign-off; display order Cover, Summary, S1–S6), `exceptions_service` (dedup by rule_code), `remediation_service`, `export_service` (Excel + PDF + narrative injection), `audit_service`, `config_service`.
- `agents/` — `base.py` (Claude/stub + mandatory run-record fields), `anomaly_agent`, `remediation_agent`, `narrative_agent` (CFO-grade EN/AR), `circular_parsing_agent`, `orchestrator.py` (narrative overwrite-in-place).
- `routers/` — `api.py` (instances/ingest/template/upload/cert/calc/validation/lineage/agents/export/audit/config), `data_layer.py` (`/data-foundation/...`), `platform.py` (`/platform/overview`, `/packs`), `sources.py`, `rules.py`, `report.py` (status/schedule/signoff/exceptions, **S5 schedule view**). Wired in `main.py`.
- `models/models.py` — see §6. `alembic/versions/` — `0001_initial`, `0002_element_governance`, `0003_target_state`.

## 3. Calculation engine
Modules run in dependency order:
```
S1 (capital) ─┐
S2 (credit)   ├─► Summary (Total RWA, ratios)
S3 (market)   │      ├─► S5 (buffers)
S4 (op risk) ─┘      └─► S6 (reconciliation)
```
`engine.compute(inputs, params, buffers)` returns a `CarResult` (`schedules`, flat `values`, `metrics`, `flags`). `calc_service.result_to_dict` serialises it (Decimals → float) into `calc_run.results`.

**Schedule 5 is fully derived** — `calc_schedule_5_buffers.compute` returns a values/flags dict (buffer rates, combined requirement, CET1 surplus, Pillar-1 surpluses, distribution band). It is presented as a schedule by `routers/report.py` (`_schedule5_view`), which builds display rows (rates/ratios as %, amounts as SAR '000) from those values, and as read-only "derived" rows in the Data Foundation grid (`data_layer_service`). Buffer rates are editable via the Rule Engine (`rules_service._buffer_rules` → `config_service` buffer scope → recompute).

### Key formulas
- **S1:** net CET1 = CET1 subtotal − deductions; Tier 1 = net CET1 + AT1; Total capital = Tier 1 + Tier 2.
- **S2:** on-balance RWA = exposure × RW; off-balance = exposure × CCF × RW; total = sum of subtotals.
- **S3:** charge = position × rate; market RWA = charge × 12.5.
- **S4:** charge = 3-yr avg gross income × beta; op RWA = charge × 12.5.
- **Cross:** Total RWA = credit + market + operational; ratios = capital ÷ Total RWA; S6 reconciliation diff must be nil; RWA composition = 100%.

## 4. Canonical element registry
Each workbook metric/line maps to: `element_code`, `label`, `sheet_name`, `section_name`, `source_domain`, `source_type` (`input`/`formula`/`cross_sheet`/`assumption`), `parameter_dependencies`, `export_cell`, `lineage_level`, plus `kind`/`rate`/`ccf` driving its rule. The registry — not the workbook — is the source of truth (the supplied workbook has broken cross-sheet formulas; see ARCHITECTURE.md).

## 5. Governance & auto-recompute
- **Certification gate:** no `CalcRun` until Finance **and** Risk are certified (`certification_service.is_calc_allowed`).
- **Element maker-checker → domain certification:** `data_layer_service.approve` certifies a domain when all its input elements are signed off, then calls `calc_service.ensure_current`.
- **Auto recompute (no Run button):** `ensure_current` recomputes when data is certified and the effective state (inputs + params + buffers, hashed) changed, and runs the governed agents when there is a failing validation and no open remediation. Triggered on element approve, rule-edit, and lazily on report GETs.
- **Two-tier sign-off:** Data Foundation certification gates the calc; Report Pack schedule → Summary sign-off is a separate attestation that auto-reopens if certified data later changes.
- **Invalidation:** input changes invalidate the owning domain's certification.

## 6. Data model (key tables)
`report_pack`, `report_instance`, `canonical_element`, `element_value` (raw, versioned), `element_governance` (status draft|submitted|certified|rejected|invalidated, override fields), `certification` (Finance/Risk domain), `calc_run` (results JSON + state hash), `validation_result`, `lineage_edge`, `agent_run`, `remediation_proposal`, `narrative` (one row per (instance, language) — overwritten in place on regenerate), `circular_change`, `source_system`, `schedule_signoff`, `config_parameter`, `audit_log`.

## 7. Agents
`anomaly_agent`, `remediation_agent`, `narrative_agent`, `circular_parsing_agent`. Each `agent_run` stores `evidence_used`, `reasoning_summary`, `confidence`, `impacted_metrics`, `proposed_action`, `approval_required`, `prompt_version`, `model_version`. No agent writes to calculation tables; remediation applies only on Checker approval. The narrative agent emits CFO/Board-grade EN + AR from the deterministic results; the orchestrator overwrites the existing narrative per language (version = revision count, status reset to draft for re-approval).

## 8. Validation rules
Cover completeness; credit/market/operational/total RWA integrity; ratio consistency; capital-ratio minimums; buffer consistency; Schedule 6 nil reconciliation; RWA composition = 100%; single-credit-class concentration (`CREDIT_CONCENTRATION_ANOMALY`). `exceptions_service.assemble` deduplicates failures by `rule_code` and attaches AI root-cause / recommendation.

## 9. Ingestion & template intake
- `GET /api/data-foundation/template` generates an intake `.xlsx` (data sheet pre-filled with input elements + an instructions sheet).
- `POST /api/instances/{id}/ingest/upload` parses an uploaded workbook: rejects **duplicate** element rows and **non-numeric** values (thousands commas allowed via `_parse_amount`), ingests valid values, and returns `{ingested, skipped, errors}`.

## 10. Export
- **Excel** (`build_excel`): opens `SAMA_CAR_SA01_Template.xlsx`, writes computed input + derived **values** into the correct cells (registry + repaired `cell_map`), overwriting the template's stale formulas. The approved English narrative is added as a top "Executive Narrative" sheet.
- **PDF** (`build_pdf`, fpdf2): multi-page A4 — approved Executive Narrative → Cover + Summary → Schedules 1–6; Uniqus purple header, Draft / Signed-Off + buffer badge, page footer. All text is latin-1-sanitised so stray characters can't crash the export; `pdf.output()` returns bytes. Falls back to HTML only if fpdf2 is unavailable.
- Export is **ungated**; the output reflects Draft vs Signed Off via a badge.

## 11. Tests (`Tool/app/api/tests/`, 30 total, `pytest`)
- `test_calc_engine.py` (formulas + anomaly), `test_integration.py` (cert gating, remediation approval, invalidation, export), `test_data_layer.py` (element lifecycle, role enforcement, roll-up, reopen, catalogue incl. S5 derived rows), `test_target_state.py` (source mapping, rule-edit auto-recompute, governed override, two-tier sign-off precondition + reopen-on-change). SQLite via `conftest.py`.

## 12. Seeded scenario
A Q4-2025 instance is seeded in **Draft** (data ingested + quality-checked, all elements "Ready for submission", not certified). It carries a Schedule 2 corporate-exposure error (`105,000,000` vs `~9,500,000` at 100% RW). Driving the workflow — Maker submits → Checker signs off → domains certify → auto-compute — inflates Total RWA to ≈187.5M ('000), drops CET1 to 7.73%, **breaches** the combined buffer, and trips three validations incl. `CREDIT_CONCENTRATION_ANOMALY`. The anomaly agent surfaces it and the remediation agent proposes a correction (pending Checker); approval restores compliance.

## 13. Practical constraints
Exact CAR logic coverage over platform breadth; architecture extensible but implementation lean; built for local execution first. See `docs/FSD.md` §10 for the demo-grade / not-yet-built gaps (no real auth, synthetic sources, etc.).
