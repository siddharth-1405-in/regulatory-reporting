"""Export cell map: canonical element_code -> [(sheet, cell), ...].

A single computed value can legitimately land in more than one workbook cell
(e.g. Net CET1 appears on Schedule 1!E33 AND Summary!C7). This map therefore
allows multiple targets per element and deliberately REPAIRS the workbook's
broken cross-sheet references:

  * Summary capital amounts (C7..C11) and Total RWA (D7/D12) are written as
    computed values rather than relying on the template's stale links.
  * Summary & Schedule 5 ratios (E7/E9/E11, E8/E9/E10) are populated.
  * Schedule 6 reconciliation difference (E21) is the correct nil check
    (already mapped via the registry derived element).

Values always come from the deterministic engine; this module only says where.
"""
from __future__ import annotations

from . import elements as reg

# Additional workbook cells a computed value should ALSO be written to,
# beyond its primary registry export_cell. These fix the broken Summary links.
_EXTRA_TARGETS: dict[str, list[tuple[str, str]]] = {
    "S1_CET1_NET": [("Summary", "C7")],
    "S1_AT1_TOTAL": [("Summary", "C8")],
    "S1_TIER1_TOTAL": [("Summary", "C9")],
    "S1_T2_TOTAL": [("Summary", "C10")],
    "S1_TOTAL_CAPITAL": [("Summary", "C11")],
    "SUM_TOTAL_RWA": [("Summary", "D7")],            # primary D12 from registry
    "SUM_CET1_RATIO": [("Schedule 5", "E8")],         # primary E7 (Summary) from registry
    "SUM_TIER1_RATIO": [("Schedule 5", "E9")],
    "SUM_TOTAL_RATIO": [("Schedule 5", "E10")],
}


def build_cell_map() -> dict[str, list[tuple[str, str]]]:
    out: dict[str, list[tuple[str, str]]] = {}
    for e in reg.ALL_ELEMENTS:
        if e.export_cell:
            out.setdefault(e.element_code, []).append((e.sheet_name, e.export_cell))
    for code, targets in _EXTRA_TARGETS.items():
        for t in targets:
            out.setdefault(code, [])
            if t not in out[code]:
                out[code].append(t)
    return out


CELL_MAP = build_cell_map()


def cells_for(code: str) -> list[tuple[str, str]]:
    return CELL_MAP.get(code, [])
