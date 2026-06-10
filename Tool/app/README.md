# Agentic CAR Reporting Platform — run guide

Governed, deterministic SAMA **CAR-SA-01** reporting with a supervised agentic
layer. See `docs/ARCHITECTURE.md`, `docs/FSD.md`, `docs/TDD.md`.

## Backend (FastAPI, Python 3.11+)

```bash
cd tool/app/api
python -m venv .venv
.venv\Scripts\activate            # Windows  (source .venv/bin/activate on *nix)
pip install -e .                  # installs deps from pyproject.toml

cp .env.example .env              # set DATABASE_URL (PostgreSQL) and optional ANTHROPIC_API_KEY
alembic upgrade head              # create schema (PostgreSQL)
python -m scripts.seed_db         # seed the demo instance with the Schedule 2 anomaly

uvicorn app.main:app --reload     # http://localhost:8000   (docs at /docs)
```

Zero-setup local option: set `DATABASE_URL=sqlite:///./car_demo.db` in `.env`
(the seed script creates the schema automatically for SQLite).

Run the tests:

```bash
pytest            # 10 calc unit tests + 7 governance integration tests
```

## Frontend (Next.js 14, TypeScript)

```bash
cd tool/app/web
npm install
cp .env.local.example .env.local  # NEXT_PUBLIC_API_BASE=http://localhost:8000
npm run dev                       # http://localhost:3000
```

> **OneDrive note:** `next dev` can crash with `EINVAL: readlink ... .next` when the
> project lives under a OneDrive-synced path (OneDrive intercepts the dev server's
> `.next` cleanup). If that happens, use the production server instead:
> `npm run build && npx next start -p 3000`. Moving the repo outside OneDrive also fixes it.

## Navigation (information architecture)
Four-section left nav — a governed **data-to-report control cockpit**:
- **Overview** — platform command center: pack catalogue, instances, source-connection
  health, data-readiness vs report-readiness, uncertified/preview/signed-off counts.
- **Data Foundation** — the shared governed data layer in three sub-areas: **Source Systems**
  (named vendors — SAP S/4HANA, Oracle FCCS, Murex, Finastra, Moody's, SAS, Collateral —
  with health/freshness/coverage), **Canonical Elements** (raw → processed drilldown,
  governed manual overrides shown side-by-side with the system value, element maker-checker
  rolling up to Finance/Risk certification), and **Rule Engine** (plain-English rules; editing
  a parameter auto-recomputes the draft).
- **Report Pack** — CAR workspace: **CAR Overview · Narrative · Exceptions · Draft CAR Report**.
  The draft auto-computes (no Run button); Draft CAR Report shows Cover, Summary and the six
  full-named schedules with per-element business meaning + plain-English computation + lineage,
  **schedule → Summary sign-off**, and **ungated Excel/PDF export** with a Draft/Signed-Off badge.
- **Admin** — source-system config, pack & canonical-element registries, ownership matrix,
  parameters, prompt/model governance, regulatory-change intake, roles/permissions, and the
  **audit trail**.

A top-bar **Maker / Checker / Admin** switcher gates which actions are enabled. Two-tier
governance: Data Foundation certification gates values into the report; Report Pack sign-off
attests each schedule (and re-opens automatically if certified data later changes).

## Demo walkthrough
1. Open the instance → **Overview**: CET1 7.73%, buffer **Breach** (anomaly present).
2. **Certification**: Finance + Risk certified (gate open). Editing data re-blocks it.
3. **Schedules**: inspect Schedule 2 — the inflated corporate-exposure line.
4. **Exceptions**: 3 failing rules incl. `CREDIT_CONCENTRATION_ANOMALY`; the
   remediation proposal (105m → 10.5m) sits **pending Checker approval**.
5. Approve it → recalculation clears the breach and all failing rules.
6. **Reasoning**: full agent trace (evidence, confidence, model version).
7. **Narrative**: EN + AR drafts → approve.
8. **Export & Audit**: sign off (gated on zero failures) → download the Excel
   (written into the SAMA template with repaired cross-references) and PDF.

## Notes
- Agents use live Anthropic Claude when `ANTHROPIC_API_KEY` is set; otherwise a
  governed deterministic fallback (the platform always runs).
- `next` shows a security-advisory deprecation notice; upgrading to the latest
  patched Next release is recommended as a follow-up.
