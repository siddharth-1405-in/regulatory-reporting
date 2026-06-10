"""Lineage — element-to-element dependency edges for headline metrics.

Built deterministically from the registry: inputs feed schedule totals, schedule
totals feed Total RWA / capital, which feed ratios and buffer status.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import LineageEdge
from ..registry.car_sa01 import elements as reg

# schedule total each input kind contributes to
_KIND_TO_TOTAL = {
    "cet1_gross": "S1_CET1_NET", "cet1_deduction": "S1_CET1_NET",
    "at1_gross": "S1_AT1_TOTAL", "at1_deduction": "S1_AT1_TOTAL",
    "t2_gross": "S1_T2_TOTAL", "t2_deduction": "S1_T2_TOTAL",
    "credit_onbal": "S2_CREDIT_RWA", "credit_offbal": "S2_CREDIT_RWA",
    "market_rate": "S3_MARKET_RWA", "market_direct": "S3_MARKET_RWA",
    "oprisk_gi": "S4_OPRISK_RWA",
}

_STATIC_EDGES = [
    ("S1_CET1_NET", "S1_TIER1_TOTAL"), ("S1_AT1_TOTAL", "S1_TIER1_TOTAL"),
    ("S1_TIER1_TOTAL", "S1_TOTAL_CAPITAL"), ("S1_T2_TOTAL", "S1_TOTAL_CAPITAL"),
    ("S2_CREDIT_RWA", "SUM_TOTAL_RWA"), ("S3_MARKET_RWA", "SUM_TOTAL_RWA"),
    ("S4_OPRISK_RWA", "SUM_TOTAL_RWA"),
    ("S1_CET1_NET", "SUM_CET1_RATIO"), ("SUM_TOTAL_RWA", "SUM_CET1_RATIO"),
    ("S1_TIER1_TOTAL", "SUM_TIER1_RATIO"), ("SUM_TOTAL_RWA", "SUM_TIER1_RATIO"),
    ("S1_TOTAL_CAPITAL", "SUM_TOTAL_RATIO"), ("SUM_TOTAL_RWA", "SUM_TOTAL_RATIO"),
    ("SUM_CET1_RATIO", "S5_CET1_SURPLUS"),
    ("S2_CREDIT_RWA", "S6_CREDIT_PCT"), ("S3_MARKET_RWA", "S6_MARKET_PCT"),
    ("S4_OPRISK_RWA", "S6_OPRISK_PCT"),
]


def build_edges() -> list[tuple[str, str]]:
    edges: list[tuple[str, str]] = []
    for e in reg.INPUT_ELEMENTS:
        total = _KIND_TO_TOTAL.get(e.kind or "")
        if e.kind == "oprisk_gi":
            total = "S4_OPRISK_RWA"
        if total:
            edges.append((e.element_code, total))
    edges.extend(_STATIC_EDGES)
    return edges


def persist(db: Session, instance_id: int) -> None:
    db.query(LineageEdge).filter(LineageEdge.instance_id == instance_id).delete()
    for frm, to in build_edges():
        db.add(LineageEdge(instance_id=instance_id, from_code=frm, to_code=to))
    db.flush()


def trace_upstream(db: Session, instance_id: int, code: str, depth: int = 4) -> list[str]:
    """Codes that feed the given element (breadth-first, bounded)."""
    edges = db.query(LineageEdge).filter(LineageEdge.instance_id == instance_id).all()
    incoming: dict[str, list[str]] = {}
    for e in edges:
        incoming.setdefault(e.to_code, []).append(e.from_code)
    seen, frontier = set(), [code]
    for _ in range(depth):
        nxt = []
        for c in frontier:
            for src in incoming.get(c, []):
                if src not in seen:
                    seen.add(src)
                    nxt.append(src)
        frontier = nxt
    return sorted(seen)
