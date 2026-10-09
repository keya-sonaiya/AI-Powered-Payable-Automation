"""GET /audit-log (paginated, filterable) — the full decision trail per invoice."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import AuditLog
from app.schemas.invoice import AuditLogListResponse

router = APIRouter()


@router.get("/audit-log", response_model=AuditLogListResponse)
def get_audit_log(
    invoice_id: Optional[int] = Query(None),
    decision: Optional[str] = Query(
        None, description="Filter by decision: auto_approved | exception | fraud_flag"
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(AuditLog)
    if invoice_id is not None:
        q = q.filter(AuditLog.invoice_id == invoice_id)
    if decision:
        q = q.filter(AuditLog.decision == decision)

    total = q.count()
    items = q.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()

    return AuditLogListResponse(total=total, limit=limit, offset=offset, items=items)
