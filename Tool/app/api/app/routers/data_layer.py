"""Data Layer API — governed canonical element workspace (element-level MVC)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..services import calc_service
from ..services import data_layer_service as dl

router = APIRouter(prefix="/api/instances/{iid}/data-foundation")


class BulkRequest(BaseModel):
    element_codes: list[str]
    role: str = "Maker"
    actor: str = "maker"
    reason: str = ""


def _guard(fn):
    try:
        return fn()
    except dl.RolePermissionError as e:
        raise HTTPException(403, str(e))


@router.get("/catalogue")
def catalogue(iid: int, db: Session = Depends(get_db)):
    data = dl.catalogue(db, iid)
    db.commit()
    return {"elements": data, "summary": dl.status_summary(db, iid)}


@router.get("/signoff-queue")
def signoff_queue(iid: int, db: Session = Depends(get_db)):
    q = dl.signoff_queue(db, iid)
    db.commit()
    return q


@router.get("/drilldown/{code}")
def drilldown(iid: int, code: str, db: Session = Depends(get_db)):
    return dl.drilldown(db, iid, code)


def _bulk(iid, body, db, fn):
    changed = _guard(lambda: fn(db, iid, body.element_codes, body.role, body.actor))
    db.commit()
    return {"changed": changed}


@router.post("/submit")
def submit(iid: int, body: BulkRequest, db: Session = Depends(get_db)):
    return _bulk(iid, body, db, dl.submit)


@router.post("/approve")
def approve(iid: int, body: BulkRequest, db: Session = Depends(get_db)):
    res = _guard(lambda: dl.approve(db, iid, body.element_codes, body.role, body.actor))
    # auto-recompute the draft once data becomes certified (no explicit Run action)
    calc_service.ensure_current(db, iid, actor=body.actor)
    db.commit()
    return res


@router.post("/reject")
def reject(iid: int, body: BulkRequest, db: Session = Depends(get_db)):
    rejected = _guard(lambda: dl.reject(db, iid, body.element_codes, body.role, body.actor, body.reason))
    db.commit()
    return {"rejected": rejected}
