# CLAUDE.md — Agentic CAR Regulatory Reporting Platform

Read this first in any new session. It is the single source of truth for what this
project is, how it's built, how to run it, and exactly what is and isn't done.

> **Status in one line:** a working end-to-end **prototype/MVP** for one report pack
> (SAMA **CAR-SA-01**) on real PostgreSQL — **30 backend tests pass**, both servers run.
> It is a demonstrable governed data-to-report cockpit, **not** yet production-deployable
> (no real auth, no live source connectors). See "Status" at the bottom.

---

## 1. What this is

A governed **data-to-report control cockpit** for bank regulatory reporting. Operating model:
`source systems → ingest → canonical data elements → rule engine → maker-checker → report pack → preview → schedule/summary sign-off → export`.

**Non-negotiable principle:** every regulatory number is produced by **deterministic code**.
AI (Anthropic Claude) is confined to analysis, diagnosis, remediation proposals, narrative and
circular parsing — it never calculates, certifies, signs off, exports, or mutates report state
without a human **Checker**.

Scope = **CAR-SA-01 only** (Cover, Summary, Schedule 1–6). Architecture supports more packs
(LCR/NSFR/etc. appear as "planned").

---

## 2. Tech stack

- **Backend:** FastAPI · Python 3.11+ · SQLAlchemy 2.x · Alembic · Pydantic v2 · openpyxl ·
  (LangGraph/Anthropic optional) — at `tool/app/api`
- **Frontend:** Next.js 14 (App Router) · TypeScript · Tailwind · TanStack Query/Table ·
  lucide-react — at `tool/app/web`
- **DB:** PostgreSQL (database `car`)
- **Design language:** Uniqus tokens (purple `#492079` / magenta `#B31E7C`, Montserrat + Inter,
  dense 14px-radius cards) — mirrored in `tool/app/web/tailwind.config.ts` from
  `Tool/design_handoff_auditor_cockpit/colors_and_type.css`.

---

## 3. How to run

**Database** (already created): `car` on local Postgres. Connection is in `tool/app/api/.env`:
```
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/car
# optional: ANTHROPIC_API_KEY=sk-ant-...   (without it, agents use deterministic fallback)
```

**Backend** (venv already exists at `tool/app/api/.venv`):
```bash
cd tool/app/api
.venv/Scripts/python.exe -m alembic upgrade head      # schema (0001,0002,0003)
.venv/Scripts/python.exe -m scripts.seed_db           # seed demo instance #1 (Q4 2025, with anomaly)
.venv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
.venv/Scripts/python.exe -m pytest -q                 # 30 tests
```

**Frontend:**
```bash
cd tool/app/web
npm install
rm -rf .next && npm run build && npx next start -p 3000   # http://localhost:3000
```
> **OneDrive gotcha:** `next dev` crashes with `EINVAL: readlink ... .next` because this repo is on
> a OneDrive-synced path. **Use the production build** (`next start`). Always `rm -rf .next` before
> `npm run build` (OneDrive breaks Next's `.next` cleanup). Moving the repo off OneDrive fixes both.

The frontend proxies `/api/*` → `http://localhost:8000` via `next.config.mjs` rewrites.

---

## 4. Information architecture (4-section nav)

Persistent shell (`tool/app/web/components/AppShell.tsx`) with a top-bar **Maker / Checker / Admin**
role switcher (`components/RoleContext.tsx`, stored in localStorage, sent as the API actor/role).

| Nav (route) | Contents |
|---|---|
| **Overview** (`/`) | Platform command center: pack catalogue, instances, **source-connection health**, **data-readiness vs report-readiness**, counts (uncertified / in-remediation / ready-for-preview / signed-off). No CAR ratios. |
| **Data Foundation** (`/data-foundation`) | 3 sub-tabs: **Source Systems** (vendor cards, health/freshness/coverage, drill to datasets), **Canonical Elements** (governed grid; raw value vs **override** side-by-side; raw→processed **drilldown** drawer; element maker-checker), **Rule Engine** (plain-English rules; edit param → auto-recompute; tags system/user-edited/override). |
| **Report Pack** (`/report-pack` → `/report-pack/car/[id]`) | Tabs **CAR Overview · Narrative · Exceptions · Draft CAR Report**. No Run buttons — draft auto-computes. Draft report: Cover, Summary, S1–S6 (full English names), per-element rows (business meaning + plain-English computation + lineage), **schedule→Summary sign-off**, **Preview**, **ungated Excel/PDF export** with Draft/Signed-Off badge. |
| **Admin** (`/admin`) | Source-system config, pack & canonical-element registries, ownership matrix, parameters, prompt/model governance, regulatory-change intake, roles/permissions, **audit trail**. |

`/instances/[id]` redirects to `/report-pack/car/[id]` (legacy).

---

## 5. Key architecture decisions (don't relitigate)

1. **Registry is the source of truth, not the workbook.** The supplied `SAMA_CAR_SA01_Template.xlsx`
   has **broken cross-sheet formulas** (Summary points at a stale Schedule-1 layout; Total RWA sums
   the wrong cells; Schedule 6 nil-check uses the wrong row). The engine computes semantically from
   the canonical registry; Excel export writes computed **values** and **repairs** those cells
   (`app/registry/car_sa01/cell_map.py`, multi-target per element).
2. **Two-tier governance.** Data Foundation element maker-checker rolls up into **Finance/Risk domain
   certification** (the calc gate). Report Pack adds separate **schedule→Summary sign-off** that can
   only happen once data is certified and **auto-reopens** if certified data later changes.
3. **Auto recompute + auto AI.** No "Run Calculation" button — `calc_service.ensure_current()`
   recomputes when data is certified and the effective state (inputs + rule params) changed; refreshes
   AI exceptions/narrative. Triggered on approve, rule-edit, and lazily on report GETs.
4. **Governed overrides.** A manual edit sets an `override_value` (raw system value preserved in
   `ElementValue`); the engine uses the override; UI shows both side-by-side; overrides go through
   maker-checker.
5. **Export is ungated** (status badge shows Draft vs Signed Off).
6. **Live Claude + deterministic fallback** so the app always runs without an API key.

---

## 6. Source-system mapping (synthetic, modeled — `app/registry/car_sa01/sources.py`)

Named vendors (demo subset is "connected"; others "available"):
**SAP S/4HANA** (capital, gross income, FS equity — Schedule 1/4/6), **Oracle FCCS** (consolidation,
minority, S6 adjustments), **Murex** (AT1/Tier 2 + market risk — S1 instruments, S3), **Finastra
Fusion** (credit exposures — S2), **Moody's Analytics** (rating buckets → risk weights), **SAS Risk**
(RWA/op-risk aggregation), **Collateral Management System** (secured/past-due). Available-not-used:
Temenos, Bloomberg, Microsoft Dynamics. These are **catalogue + synthetic data**, not live connectors.

## 7. Rule engine (`app/registry/car_sa01/rules.py`)

Plain-English rule + machine structure per registry `kind`: aggregation (capital), adjustment
(deductions), risk_weight (S2 on-balance), ccf_risk_weight (S2 off-balance), market_charge (S3),
operational/beta (S4), reconciliation (S6). Editable params (risk weight / CCF / charge rate / beta /
buffer) persist via `config_service` keys like `S2_ON_CORP_BBB.risk_weight`; editing auto-recomputes.

---

## 8. Backend layout (`tool/app/api/app/`)

- `registry/car_sa01/` — **the heart**: `elements.py` (168 elements: 142 input + derived),
  `parameters.py` (risk weights/CCFs/betas/×12.5/buffers/minimums), `cell_map.py` (export targets +
  repairs), `sources.py`, `rules.py`, `sample_data.py` (baseline + the Schedule-2 anomaly).
- `calc/` — deterministic engine: `engine.py` + `calc_schedule_1..6` + `calc_summary` + `types.py`.
- `services/` — `report_instance_service` (load_inputs prefers override), `ingestion_service`,
  `dq_service`, `ownership_service` (reads the matrix xlsx), `certification_service` (domain gate +
  element roll-up + invalidation), `calc_service` (`run_calculation`, `ensure_current`),
  `validation_service`, `lineage_service`, `data_layer_service` (Data Foundation: catalogue, override,
  drilldown, maker-checker), `sources_service`, `rules_service`, `report_signoff_service`,
  `exceptions_service`, `remediation_service`, `export_service` (Excel + HTML/PDF), `audit_service`,
  `config_service`.
- `agents/` — `base.py` (Claude/stub + mandatory run-record fields), `anomaly_agent`,
  `remediation_agent`, `narrative_agent` (EN/AR), `circular_parsing_agent`, `orchestrator.py`.
- `routers/` — `api.py` (instances/ingest/cert/calc/validation/lineage/agents/export/audit/config),
  `data_layer.py` (`/data-foundation/...`), `platform.py` (`/platform/overview`,`/packs`),
  `sources.py`, `rules.py`, `report.py` (status/schedule/signoff/exceptions). Wired in `main.py`.
- `models/models.py` — see §9. `alembic/versions/` — `0001_initial`, `0002_element_governance`,
  `0003_target_state`.

## 9. Data model (key tables)

`report_pack`, `report_instance` (status lifecycle), `canonical_element`, `element_value` (raw,
versioned), `element_governance` (status draft|edited|frozen|submitted|certified|rejected|invalidated,
**override_value/override_reason**), `certification` (Finance/Risk domain), `calc_run` (results JSON +
state hash), `validation_result`, `lineage_edge`, `agent_run` (evidence/reasoning/confidence/impacted/
proposed_action/approval_required/prompt_version/model_version), `remediation_proposal` (+ maker_rationale/
checker_comment), `narrative`, `circular_change`, `source_system`, `schedule_signoff`, `audit_log`,
`config_parameter`.

## 10. Tests (`tool/app/api/tests/`, 30 total, `pytest`)

`test_calc_engine.py` (10 — formulas + anomaly), `test_integration.py` (7 — cert gating, remediation
approval, invalidation, export), `test_data_layer.py` (7 — element lifecycle, role enforcement, roll-up,
reopen), `test_target_state.py` (6 — source mapping, rule-edit auto-recompute, governed override,
two-tier sign-off precondition + reopen-on-change). SQLite is used for tests (env set in `conftest.py`).

## 11. The seeded demo scenario

Instance #1 (Q4 2025) carries a **Schedule 2 data error**: corporate BBB exposure `105,000,000` vs
correct `~9,500,000` (100% risk weight). This inflates Total RWA → **187,468,750**, drops CET1 to
**7.73%**, **breaches** the buffer, and trips 3 validations incl. `CREDIT_CONCENTRATION_ANOMALY`. The
anomaly agent surfaces it, the remediation agent proposes a fix (pending Checker), and Checker approval
recomputes to compliant. Data starts certified; report sign-off (S1–S6→Summary) starts pending.

---

## 12. Status — what's done vs remaining

**✅ Done & working:** deterministic engine (8 sheets), registry + sources + rule engine + business
meaning, two-tier governance, overrides, auto-recompute, validation/lineage/audit, 4-section UI, role
switcher, Excel export into the SAMA template, the full anomaly→remediation→recompute story, 30 tests.

**⚠️ Demo-grade (works, not production):**
- **No real auth** — role is a UI switcher passed to the API; backend trusts it (spoofable). Needs
  login + server-enforced RBAC + per-user audit identity. *(Highest-priority gap.)*
- **Source systems are modeled with synthetic seeded data** — no live connectors/ETL.
- **AI agents** run deterministic fallback unless `ANTHROPIC_API_KEY` is set.
- **PDF export** falls back to **HTML** (WeasyPrint not installed here).
- Frontend served via production build (`next dev` broken on OneDrive).

**🔲 Not built / next (priority order):** (1) real auth + enforced RBAC; (2) ≥1 live source connector +
scheduled ingestion; (3) packaging/CI (Docker, CI/CD) + working PDF; (4) a 2nd report pack (LCR/NSFR) to
prove multi-pack scalability. Also later: multi-period/entity at scale, concurrency/locking, observability/
hardening, frontend E2E tests, notifications/realtime, XBRL/regulator filing (out of original scope).

---

## 13. Reference material & pointers

- Workbooks: `reference_artifacts/SAMA_CAR_SA01_Template.xlsx`, `Regulatory_Data_Ownership_Matrix.xlsx`
- Specs: `docs/FSD.md`, `docs/TDD.md`, `docs/ARCHITECTURE.md`; run guide: `tool/app/README.md`
- Design handoff: `Tool/design_handoff_auditor_cockpit/` (README + `colors_and_type.css`)
- Plan/working doc (history of the build): `~/.claude/plans/act-as-a-senior-linked-narwhal.md`
- Model note: build targets Anthropic Claude (`claude-opus-4-8` reasoning, `claude-haiku-4-5` narrative);
  configured in `app/core/config.py`.
