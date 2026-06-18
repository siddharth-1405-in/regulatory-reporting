# Functional Specification Document
## Agentic CAR Regulatory Reporting Platform — current build

> **Status:** working end-to-end prototype/MVP for one report pack (SAMA **CAR-SA-01**)
> on real PostgreSQL. 30 backend tests pass; both servers run. This document
> describes the tool **as it is built today**, not just intended scope. It is the
> single canonical FSD — the previous duplicate under `Tool/` has been removed.
> Companion docs: `docs/TDD.md`, `docs/ARCHITECTURE.md`, run guide `Tool/app/README.md`,
> session source-of-truth `CLAUDE.md`.

## 1. Purpose
A governed **data-to-report control cockpit** for bank regulatory reporting:
`source systems → ingest → canonical data elements → rule engine → maker-checker →
report pack → preview → schedule/summary sign-off → export`.

Built from these reference artifacts:
- `reference_artifacts/SAMA_CAR_SA01_Template.xlsx` — **the source of truth for all schedules** (Cover, Summary, S1–S6)
- `reference_artifacts/Regulatory_Data_Ownership_Matrix.xlsx` — Finance/Risk ownership + regulatory change log
- `Tool/design_handoff_auditor_cockpit/` — Uniqus design language (purple `#492079` / magenta `#B31E7C`, Montserrat + Inter, dense cards)

**Non-negotiable principle:** every regulatory number is produced by **deterministic
code**. AI (Anthropic Claude) is confined to analysis, diagnosis, remediation
proposals, narrative and circular parsing — it never calculates, certifies, signs
off, exports, or mutates report state without a human **Checker**.

## 2. Scope
### In scope (built)
- One executable report pack: **CAR-SA-01** — Cover, Summary, and Schedules 1–6, computed deterministically from the canonical registry.
- Finance / Risk ownership and certification driven by the ownership matrix.
- Two-tier governance: element-level maker-checker → domain certification → schedule → Summary sign-off.
- Excel export into the SAMA template (with repaired cross-sheet cells) and a real multi-page PDF export, both carrying the approved executive narrative at the top.

### Out of scope
- Live filing to the regulator; XBRL.
- Live production source-system connectors (sources are modeled with synthetic seeded data).
- Additional executable report packs (LCR/NSFR/ORR appear in the catalogue as **planned**).

## 3. Users / roles
Role is selected in a top-bar switcher (Maker / Checker / Admin) and sent to the API as the actor/role. *(MVP: not real auth — see Status.)*
- **Maker** — prepares data, uploads templates, submits report-ready elements for sign-off, edits rule parameters, re-creates narrative.
- **Checker** — signs off data elements (→ domain certification), signs off schedules and the Summary, approves/rejects remediation, approves the narrative.
- **Admin** — both, plus parameter / mapping / prompt governance.

## 4. Information architecture (4-section nav)
Persistent shell with the role switcher.

| Section | Contents |
|---|---|
| **Overview** (`/`) | Command center: KPI strip, **Regulatory Report Portfolio** (single row; the active CAR pack is clickable → its report pack, planned packs show a "next rollout" tooltip), primary pathways, active reporting cycles. |
| **Data Foundation** (`/data-foundation`) | **4-step workflow:** Data Ingestion → Data Validation → Rule Engine → Report-Ready Data & Sign-off. (Sources, template download/upload, quality checks, plain-English editable rules, governed element maker-checker.) |
| **Report Pack** (`/report-pack/car/[id]`) | Tabs: **CAR Overview · Narrative · Exceptions · Draft CAR Report**. Draft auto-computes (no Run button). |
| **Admin** (`/admin`) | Source config, registries, ownership matrix, parameters, prompt/model governance, regulatory-change intake, roles, audit trail. |

## 5. Workflow (as built)
1. A reporting instance is seeded/created in **Draft** — data is ingested and quality-checked, but **not yet certified**; all data elements start "Ready for submission".
2. **Data Ingestion** — pull from modeled source systems, or download the intake template, fill it, and upload it. Upload validation rejects duplicate data-element rows and non-numeric values (thousands commas are allowed) and reports skipped rows.
3. **Data Validation** — completeness, format/structure and duplicate quality checks, with AI-assisted recommendations.
4. **Rule Engine** — plain-English transformation rules; editable parameters (risk weights, CCFs, charge rates, betas, **Schedule 5 buffer rates**). Editing a parameter auto-recomputes the draft.
5. **Report-Ready Data & Sign-off** — Maker selects elements and **Submits for sign-off**; Checker **Signs off** (or returns for correction). Counts (Ready / Submitted / Signed-off) update in real time; the submit control disappears once everything is signed off.
6. Element sign-off **rolls up** to Finance/Risk domain certification, which opens the calculation gate. The draft then **auto-computes** (deterministic engine) and the governed agents run (anomaly → remediation proposal → narrative).
7. In the **Report Pack**: review CAR Overview, Exceptions (read-only AI root-cause + recommendation), and the Draft CAR Report (Cover, Summary, S1–S6).
8. **Sign-off**: each schedule, then the Summary (Summary requires all schedules signed). If certified data later changes, an affected sign-off auto-reopens.
9. **Narrative**: re-create (overwrites in place — one EN + one AR draft, no version pile-up), then approve.
10. **Export**: Excel and PDF (ungated; the output carries a Draft / Signed-Off badge and the approved English narrative at the top).

## 6. CAR logic (implemented deterministically)
### Summary
CET1 / AT1 / Tier 1 / Tier 2 / Total regulatory capital; Total RWA; CET1, Tier 1 and Total capital ratios; SAMA minimum comparisons and buffer status.

### Schedule 1 — Regulatory Capital Composition
CET1 gross lines − deductions = net CET1; AT1 gross − deductions; Tier 2 gross − deductions; Total Tier 1 = CET1 + AT1; Total regulatory capital = Tier 1 + Tier 2.

### Schedule 2 — Credit Risk RWA
On-balance RWA = exposure × risk weight; off-balance equivalent = exposure × CCF, then × risk weight; Total credit RWA = on-balance + off-balance subtotals.

### Schedule 3 — Market Risk
Capital charge = position/notional × charge rate (where applicable); Market RWA = total charge × 12.5.

### Schedule 4 — Operational Risk
3-year average gross income per business line × beta = charge; Operational RWA = total charge × 12.5.

### Schedule 5 — Capital Buffers (fully derived)
Pillar 1 minimums (CET1 4.50% / Tier 1 6.00% / Total 8.00%); CCB / CCyB / D-SIB / other buffer rates; combined buffer requirement (% and × RWA amount); CET1 available for buffers; CET1 surplus/(deficit) over the combined requirement; per-tier Pillar 1 surpluses; dividend-distribution constraint band. **S5 has no maker-input elements** — buffer rates are edited in the Rule Engine; S5 surfaces as read-only "derived" rows in the data grid and as a full computed schedule in the Draft CAR Report.

### Schedule 6 — Reconciliation
Published-FS-to-regulatory-capital reconciliation (nil-difference check to S1 total capital); RWA composition (credit/market/operational) must total 100%.

### Cross-schedule rules
Total RWA = credit + market + operational; ratios = capital ÷ Total RWA; Summary derives from S1–S4; S5 from Summary + Total RWA; S6 from S1 and S2–S4.

## 7. Ownership and certification
- Ownership is read from `Regulatory_Data_Ownership_Matrix.xlsx`; domains: **Finance** and **Risk**.
- No calculation until required domains are certified (via element sign-off roll-up).
- Any upstream input change invalidates the owning domain's certification and re-blocks/recomputes downstream outputs and reopens affected sign-offs.

## 8. Agent layer (governed, advisory only)
Four agents — **Anomaly**, **Root-Cause & Remediation**, **Narrative (EN + AR)**, **Circular Parsing**. Live Claude with a deterministic fallback so the app always runs without an API key.
- Outputs are grounded in computed/certified data; each run records evidence, reasoning summary, confidence, impacted metrics, proposed action, approval-required, prompt version, model version.
- Remediation requires **Checker** approval before any state change.
- The Narrative is CFO/Board-grade (adequacy verdict, buffer headroom in bps, RWA drivers, reconciliation, distribution implication), regenerates in place, and — once approved — appears at the top of the PDF and Excel exports.

## 9. Acceptance criteria (met)
- CAR workbook structure reproduced as product modules and export sections (Cover, Summary, S1–S6).
- Workbook logic implemented deterministically; the registry — not the workbook's broken formulas — is the source of truth.
- Ownership and certification follow the ownership matrix; two-tier governance enforced.
- The seeded Schedule 2 anomaly is caught by validation, surfaced by the anomaly agent, and corrected via the Checker-approved workflow.
- Lineage exists for headline metrics and report-ready elements.
- Excel export writes into the SAMA template (repairing its broken cross-sheet cells); PDF export produces a real multi-page document.
- Architecture supports future report packs (registry-driven).

## 10. Status — what's demo-grade / not yet built
- **No real auth** — the role switcher is trusted by the backend (spoofable). Highest-priority gap.
- **Source systems are modeled with synthetic seeded data** — no live connectors/ETL.
- **AI agents** run the deterministic fallback unless `ANTHROPIC_API_KEY` is set.
- **Not built next:** real auth + enforced RBAC; ≥1 live source connector + scheduled ingestion; packaging/CI (Docker, CI/CD); a 2nd report pack (LCR/NSFR). Later: multi-period/entity at scale, concurrency/locking, observability, frontend E2E tests, XBRL/regulator filing.
