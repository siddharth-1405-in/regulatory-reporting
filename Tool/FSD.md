# Functional Specification Document
## Agentic AI Regulatory Reporting Platform — CAR MVP

## Purpose
Build a governed regulatory reporting MVP for **SAMA Capital Adequacy Return (CAR-SA-01)** using these reference artifacts:
- `reference_artifacts/SAMA_CAR_SA01_Template.xlsx`
- `reference_artifacts/Regulatory_Data_Ownership_Matrix.xlsx`
- `design_handoff_auditor_cockpit/` for UI, interaction, density, and audit-control design guidance

If this FSD conflicts with the canonical PRD, the PRD governs.

## Product definition
The MVP is a **deterministic CAR reporting tool with a governed agentic AI layer**.
- Deterministic core: ingestion, mapping, certification, CAR calculations, validations, lineage, approvals, export
- Agentic AI layer: anomaly detection, root-cause/remediation proposal, EN/AR narrative, circular impact analysis
- No AI agent may calculate regulatory values, certify data, sign off, or export without human approval

## Scope
### In scope
- One executable report pack: **CAR-SA-01**
- Exact workbook structure reproduced as product modules and export sections:
  - Cover
  - Summary
  - Schedule 1 Regulatory Capital Composition
  - Schedule 2 Credit Risk RWA
  - Schedule 3 Market Risk Capital Charge and RWA
  - Schedule 4 Operational Risk Capital Charge and RWA
  - Schedule 5 Capital Buffers and Combined Capital Requirement
  - Schedule 6 Reconciliation
- Finance and Risk ownership/certification driven by `Regulatory_Data_Ownership_Matrix.xlsx`
- Excel export matching CAR workbook structure
- PDF export with same report content

### Out of scope
- Live filing to regulator
- XBRL
- Real production source-system integrations
- Additional executable report packs beyond CAR

## Users
- Viewer: read-only access
- Maker: prepare return, run ingestion/calculation/agents
- Checker: certify, approve/reject remediation, approve narrative, sign off
- Admin: maintain parameters, mappings, prompt versions

## Workflow
1. Create CAR report instance for reporting period
2. Ingest synthetic Finance and Risk data
3. Run DQ checks
4. Map data to canonical CAR model
5. Finance certifies owned elements
6. Risk certifies owned elements
7. System blocks calculation until required certifications complete
8. Run deterministic CAR calculations
9. Run validations
10. Run anomaly/remediation agents if issues exist
11. Checker approves or rejects remediation
12. Generate EN/AR narrative
13. Final sign-off
14. Export Excel and PDF

## CAR logic that must be implemented
### Summary
- CET1 capital
- AT1 capital
- Tier 1 capital
- Tier 2 capital
- Total regulatory capital
- Total RWA
- CET1 ratio
- Tier 1 ratio
- Total capital ratio
- Minimum comparisons and buffer status

### Schedule 1
- CET1 gross lines, deductions, net CET1
- AT1 gross lines, deductions, total AT1
- Tier 2 gross lines, deductions, total Tier 2
- Total Tier 1 = CET1 + AT1
- Total regulatory capital = Tier 1 + Tier 2

### Schedule 2
- All on-balance and off-balance exposure classes from the CAR workbook
- On-balance RWA = exposure × risk weight
- Off-balance equivalent = exposure × CCF
- Off-balance RWA = off-balance equivalent × risk weight
- Total credit risk RWA = on-balance subtotal + off-balance subtotal

### Schedule 3
- All market risk lines from the CAR workbook
- Capital charge = position/notional × charge rate where applicable
- Market risk RWA = total capital charge × 12.5

### Schedule 4
- All operational risk business lines from the CAR workbook
- 3-year average gross income by business line
- Capital charge = average gross income × beta
- Operational risk RWA = total capital charge × 12.5

### Schedule 5
- Pillar 1 minimum CET1 / Tier 1 / Total Capital
- CCB / CCyB / D-SIB / other buffers
- Combined capital requirement
- Surplus / deficit
- Dividend distribution constraint bands

### Schedule 6
- Published FS to regulatory capital reconciliation
- Nil-difference check to Schedule 1 total regulatory capital
- RWA composition: credit / market / operational / total
- RWA composition must equal 100%

### Cross-schedule rules
- Total RWA = credit + market + operational
- CET1 ratio = CET1 / total RWA
- Tier 1 ratio = Tier 1 / total RWA
- Total capital ratio = total regulatory capital / total RWA
- Summary derives from S1–S4
- Schedule 5 derives from Summary and total RWA
- Schedule 6 derives from Schedule 1 and S2–S4

## Ownership and certification
- Ownership must be driven from `Regulatory_Data_Ownership_Matrix.xlsx`
- Minimum domains for MVP: Finance and Risk
- No calculation or assembly until required certifications are complete
- Any upstream data change invalidates affected certifications

## Agent layer
Implement four agents:
- Anomaly Agent
- Root-Cause & Remediation Agent
- Narrative Agent (English + Arabic)
- Circular Parsing Agent

Rules:
- Agent outputs must be grounded in approved data
- Agent outputs must show reasoning summary, evidence summary, confidence, impacted metrics
- Remediation requires Checker approval before any state change

## Minimum screens
- Report selection
- CAR workspace shell
- Ingestion & DQ
- Certification dashboard
- Cover / Summary / Schedule 1–6 views
- Exception workbench
- Reasoning-trace panel
- Lineage panel
- Narrative review
- Readiness dashboard
- Export/audit view
- Admin console

Use `design_handoff_auditor_cockpit/` as the mandatory design reference for layout, spacing, hierarchy, density, state visibility, and audit-focused UX.

## Acceptance criteria
- CAR workbook structure is reproduced as product modules and export sections
- Workbook logic is implemented deterministically
- Ownership and certification follow the ownership matrix
- Validation catches seeded Schedule 2 anomaly
- Remediation requires Checker approval
- Lineage exists for headline metrics
- Excel export follows CAR workbook structure
- Product architecture clearly supports future report packs
