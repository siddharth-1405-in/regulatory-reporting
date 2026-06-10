"""Export — Excel (into the SAMA template) and PDF (HTML) from the same outputs.

Excel: opens SAMA_CAR_SA01_Template.xlsx, writes the deterministic input and
computed VALUES into the correct cells (via the registry + repaired cell map),
overwriting the template's stale cross-sheet formulas so the exported file is
fully populated and internally consistent. PDF: renders the same structured
result to a styled HTML document (converted to PDF when WeasyPrint is available).

Export is gated: the caller must ensure the instance is signed off.
"""
from __future__ import annotations

import io
import re

from openpyxl import load_workbook
from sqlalchemy.orm import Session

from ..core.config import CAR_TEMPLATE
from ..models import ReportInstance
from ..registry.car_sa01 import elements as reg
from ..registry.car_sa01.cell_map import CELL_MAP
from . import calc_service

MONEY_FMT = "#,##0"
PCT_FMT = "0.00%"
PCT_CELLS = {("Summary", "E7"), ("Summary", "E9"), ("Summary", "E11"),
             ("Schedule 5", "E8"), ("Schedule 5", "E9"), ("Schedule 5", "E10"),
             ("Schedule 6", "D25"), ("Schedule 6", "D26"), ("Schedule 6", "D27")}

_S6_ROW = {base: row for base, _label, row in reg._S6_LINES}
_S4_ROW = {base: row for base, _label, _codes, _beta, row in reg.S4_BUSINESS_LINES}


def _row_of(cell: str) -> int:
    return int(re.search(r"\d+", cell).group())


def _set(ws, cell: str, value, fmt: str | None = None):
    c = ws[cell]
    c.value = value
    if fmt:
        c.number_format = fmt


def build_excel(db: Session, instance_id: int) -> bytes:
    inst = db.get(ReportInstance, instance_id)
    run = calc_service.latest_run(db, instance_id)
    if run is None:
        raise ValueError("no calculation run to export")
    results = run.results
    values = results["values"]
    inputs = calc_service.report_instance_service.load_inputs(db, instance_id)

    wb = load_workbook(CAR_TEMPLATE)

    # Cover identification
    cov = wb["Cover"]
    _set(cov, "C5", inst.bank_name)
    _set(cov, "C7", inst.period_label)
    _set(cov, "C8", inst.period_end.strftime("%d/%m/%Y"))

    # 1) raw input values into their registry cells
    for code, val in inputs.items():
        e = reg.REGISTRY.get(code)
        if e and e.export_cell and e.sheet_name in wb.sheetnames:
            _set(wb[e.sheet_name], e.export_cell, float(val), MONEY_FMT)

    # 2) per-line computed results (overwrite template formulas with values)
    for name, sched in results["schedules"].items():
        ws = wb[name] if name in wb.sheetnames else None
        if ws is None:
            continue
        for line in sched["lines"]:
            code, res = line["element_code"], line["result"]
            if name == "Schedule 2":
                row = _row_of(reg.get(code).export_cell)
                if "equivalent" in line["inputs"]:
                    _set(ws, f"E{row}", line["inputs"]["equivalent"], MONEY_FMT)
                _set(ws, f"G{row}", res, MONEY_FMT)
            elif name == "Schedule 3":
                _set(ws, f"E{_row_of(reg.get(code).export_cell)}", res, MONEY_FMT)
            elif name == "Schedule 4":
                _set(ws, f"G{_S4_ROW[code]}", res, MONEY_FMT)
            elif name == "Schedule 6":
                _set(ws, f"E{_S6_ROW[code]}", res, MONEY_FMT)

    # 3) derived totals + repaired cross-sheet cells via the cell map
    #    (one value may target multiple cells, e.g. Net CET1 -> S1!E33 & Summary!C7)
    for code, targets in CELL_MAP.items():
        if code not in values:
            continue
        for sheet, cell in targets:
            if sheet not in wb.sheetnames:
                continue
            fmt = PCT_FMT if (sheet, cell) in PCT_CELLS else MONEY_FMT
            _set(wb[sheet], cell, values[code], fmt)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def build_html(db: Session, instance_id: int) -> str:
    inst = db.get(ReportInstance, instance_id)
    run = calc_service.latest_run(db, instance_id)
    if run is None:
        raise ValueError("no calculation run to export")
    m = run.results["metrics"]
    flags = run.results["flags"]
    status_color = "#1F8A5B" if flags.get("buffer_status") == "Compliant" else "#C03A3A"
    from . import report_signoff_service
    report_status = report_signoff_service.report_status(db, instance_id)
    rs_color = "#1F8A5B" if report_status == "Signed Off" else "#492079"

    def pct(x): return f"{x*100:.2f}%"
    def money(x): return f"{x:,.0f}"

    rows = "".join(
        f"<tr><td>{label}</td><td class='num'>{val}</td></tr>"
        for label, val in [
            ("CET1 Capital", money(m["cet1"])), ("Tier 1 Capital", money(m["tier1"])),
            ("Total Regulatory Capital", money(m["total_capital"])),
            ("Credit Risk RWA", money(m["credit_rwa"])), ("Market Risk RWA", money(m["market_rwa"])),
            ("Operational Risk RWA", money(m["oprisk_rwa"])),
            ("<b>Total RWA</b>", f"<b>{money(m['total_rwa'])}</b>"),
            ("CET1 Ratio", pct(m["cet1_ratio"])), ("Tier 1 Ratio", pct(m["tier1_ratio"])),
            ("Total Capital Ratio", pct(m["total_ratio"])),
        ])

    return f"""<!doctype html><html><head><meta charset='utf-8'>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@600;800&family=Inter:wght@400;600&display=swap');
  body {{ font-family:'Inter',sans-serif; color:#333; margin:32px; }}
  .eyebrow {{ font-family:'Montserrat'; font-weight:800; font-size:10px; letter-spacing:.16em;
             text-transform:uppercase; color:#B31E7C; }}
  h1 {{ font-family:'Montserrat'; font-weight:800; color:#3B2162; font-size:22px; margin:4px 0 0; }}
  .sub {{ color:#666; font-size:12px; margin-bottom:18px; }}
  .status {{ display:inline-block; padding:4px 12px; border-radius:999px; color:#fff;
            background:{status_color}; font-family:'Montserrat'; font-weight:800; font-size:11px; }}
  table {{ border-collapse:collapse; width:100%; margin-top:14px; font-size:12px; }}
  th,td {{ text-align:left; padding:7px 10px; border-bottom:1px solid #ECE4F2; }}
  th {{ font-family:'Montserrat'; font-weight:800; color:#492079; font-size:10px;
        text-transform:uppercase; letter-spacing:.08em; }}
  td.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
  .bar {{ height:3px; background:linear-gradient(90deg,#3B2162,#492079 35%,#B31E7C 70%,#C879AB); margin:18px 0; }}
</style></head><body>
  <div class='eyebrow'>SAMA · Capital Adequacy Return · CAR-SA-01</div>
  <h1>{inst.bank_name}</h1>
  <div class='sub'>{inst.period_label} · period end {inst.period_end:%d %b %Y} · {inst.units}</div>
  <div class='bar'></div>
  <span class='status' style='background:{rs_color}'>Report: {report_status}</span>
  <span class='status'>Buffer status: {flags.get('buffer_status')}</span>
  <table><tr><th>Metric</th><th style='text-align:right'>Value (SAR '000 / %)</th></tr>{rows}</table>
  <p style='color:#888;font-size:10px;margin-top:24px'>Generated by the Agentic CAR Reporting Platform.
  All regulatory figures produced by the deterministic calculation engine; reconciliation difference
  {money(m['recon_diff'])}, RWA composition {pct(m['rwa_composition_pct'])}.</p>
</body></html>"""


def build_pdf(db: Session, instance_id: int) -> tuple[bytes, str]:
    """Returns (bytes, media_type). Uses WeasyPrint if available, else HTML."""
    html = build_html(db, instance_id)
    try:
        from weasyprint import HTML
        return HTML(string=html).write_pdf(), "application/pdf"
    except Exception:
        return html.encode("utf-8"), "text/html"
