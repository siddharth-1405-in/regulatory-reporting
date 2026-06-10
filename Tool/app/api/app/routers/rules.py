"""Rule engine API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..services import rules_service
from ..services.data_layer_service import RolePermissionError

router = APIRouter(prefix="/api/instances/{iid}/rules")


class EditRuleRequest(BaseModel):
    key: str
    value: float
    role: str = "Maker"
    actor: str = "maker"


@router.get("")
def list_rules(iid: int, db: Session = Depends(get_db)):
    return rules_service.list_rules(db, iid)


@router.post("/edit")
def edit_rule(iid: int, body: EditRuleRequest, db: Session = Depends(get_db)):
    try:
        res = rules_service.edit_rule(db, instance_id=iid, key=body.key, value=body.value,
                                      role=body.role, actor=body.actor)
    except RolePermissionError as e:
        raise HTTPException(403, str(e))
    db.commit()
    return res
