"""Source systems API."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..services import sources_service

router = APIRouter(prefix="/api/sources")


@router.get("")
def list_sources(db: Session = Depends(get_db)):
    data = sources_service.catalogue(db)
    db.commit()
    return data


@router.get("/{code}/datasets")
def datasets(code: str, db: Session = Depends(get_db)):
    return sources_service.datasets_for(db, code)
