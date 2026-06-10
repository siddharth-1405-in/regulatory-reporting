# Technical Design Document
## Agentic AI Regulatory Reporting Platform — CAR MVP

## Objective
Build a practical, locally runnable full-stack CAR MVP with exact workbook coverage, deterministic calculations, governed AI, and clean extensibility for future report packs.

## Reference inputs
Code must read and use these artifacts directly:
- `reference_artifacts/SAMA_CAR_SA01_Template.xlsx`
- `reference_artifacts/Regulatory_Data_Ownership_Matrix.xlsx`
- `design_handoff_auditor_cockpit/`

## Recommended stack
### Frontend
- Next.js 14+
- TypeScript
- Tailwind CSS
- shadcn/ui
- TanStack Table
- React Query

### Backend
- FastAPI
- Python 3.11+
- SQLAlchemy 2.x
- Alembic
- Pydantic v2
- LangGraph
- Anthropic Claude API

### Data / export
- PostgreSQL
- openpyxl for Excel export
- HTML-to-PDF for PDF export

## Architecture
### Layers
- Platform services
- Shared agent layer
- CAR report pack

### Rule
All CAR values must be produced by deterministic code. AI is only for analysis, diagnosis, proposal, narrative, and circular parsing.

## Folder expectation
```text
project/
  app/
    web/
    api/
  reference_artifacts/
    SAMA_CAR_SA01_Template.xlsx
    Regulatory_Data_Ownership_Matrix.xlsx
  design_handoff_auditor_cockpit/
  docs/
    FSD.md
    TDD.md
    PROMPT.md
```

## Core backend modules
- report_instance_service
- ingestion_service
- dq_service
- ownership_service
- certification_service
- calc_engine
- validation_service
- lineage_service
- agent_service
- export_service
- audit_service
- config_service

## Canonical model requirement
Create a canonical CAR element registry. Each workbook metric/line item should map to:
- element_code
- label
- sheet_name
- section_name
- source_domain
- source_type (`input`, `formula`, `cross_sheet`, `assumption`)
- parameter_dependencies
- export_target
- lineage_level

This registry is required so the workbook can be implemented exactly and future report packs can reuse the same pattern.

## Calculation modules
Implement as separate deterministic modules:
- calc_summary
- calc_schedule_1_capital
- calc_schedule_2_credit_rwa
- calc_schedule_3_market_risk
- calc_schedule_4_operational_risk
- calc_schedule_5_buffers
- calc_schedule_6_reconciliation

## Required formulas
### Schedule 1
- Net CET1 = CET1 subtotal - CET1 deductions
- Total AT1 = AT1 gross - AT1 deductions
- Total Tier 1 = Net CET1 + Total AT1
- Total Tier 2 = Tier 2 gross - Tier 2 deductions
- Total regulatory capital = Total Tier 1 + Total Tier 2

### Schedule 2
- On-balance RWA = exposure × risk weight
- Off-balance equivalent = exposure × CCF
- Off-balance RWA = equivalent × risk weight
- Total credit risk RWA = on-balance subtotal + off-balance subtotal

### Schedule 3
- Capital charge = position/notional × charge rate where applicable
- Market risk RWA = total market capital charge × 12.5

### Schedule 4
- Average gross income = average of 3 years
- Capital charge = average gross income × beta
- Operational risk RWA = total operational capital charge × 12.5

### Summary / Schedule 5 / Schedule 6
- Total RWA = credit + market + operational
- CET1 ratio = CET1 / total RWA
- Tier 1 ratio = Tier 1 / total RWA
- Total capital ratio = total regulatory capital / total RWA
- Buffer requirements = total RWA × configured thresholds
- Schedule 6 capital reconciliation difference must be nil
- Schedule 6 RWA composition must total 100%

## Ownership and certification design
- Read ownership assignments from `Regulatory_Data_Ownership_Matrix.xlsx`
- At minimum support Finance and Risk domains
- Calculation blocked until required certifications complete
- Upstream data changes invalidate affected certifications and downstream outputs

## Agent design
Implement four agents:
- anomaly_agent
- remediation_agent
- narrative_agent
- circular_parsing_agent

Each run must store:
- evidence_used
- reasoning_summary
- confidence
- impacted_metrics
- proposed_action
- approval_required
- prompt_version
- model_version

No agent writes directly to core calculation tables.

## Validation rules
- Cover completeness
- Total credit risk RWA integrity
- Market risk RWA integrity
- Operational risk RWA integrity
- Total RWA integrity
- Ratio consistency
- Buffer consistency
- Schedule 6 nil reconciliation difference
- RWA composition = 100%

## Export
### Excel
Use `SAMA_CAR_SA01_Template.xlsx` as the export template and build a mapping registry from canonical elements and derived outputs to workbook cells.

### PDF
Generate from the same structured outputs used for Excel.

## Testing
- Unit tests for formula modules and validations
- Integration tests for certification gating, remediation approval, recalculation, export
- One seeded Schedule 2 anomaly that materially affects total RWA and buffer status

## Practical constraints
- Prioritize exact CAR logic coverage over broad platform complexity
- Keep architecture extensible but implementation lean
- Avoid unnecessary infrastructure for MVP
- Build for local execution first
