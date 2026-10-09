"""
GET /metrics — touchless rate %, exception/fraud counts, average cycle time
(AuditLog.created_at - Invoice.created_at), and a decisions-over-time series
for the dashboard's chart. Read-only aggregation queries only.
"""
from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import AuditLog, Invoice
from app.schemas.invoice import DecisionsOverTimePoint, MetricsResponse

router = APIRouter()

_STATUSES = ("auto_approved", "exception", "fraud_flag")


@router.get("/metrics", response_model=MetricsResponse)
def get_metrics(db: Session = Depends(get_db)):
    total = db.query(func.count(Invoice.id)).scalar() or 0

    counts_by_status = dict(
        db.query(Invoice.status, func.count(Invoice.id)).group_by(Invoice.status).all()
    )
    auto_approved = counts_by_status.get("auto_approved", 0)
    exception = counts_by_status.get("exception", 0)
    fraud_flag = counts_by_status.get("fraud_flag", 0)

    touchless_rate = (auto_approved / total * 100) if total else 0.0

    avg_cycle_seconds = (
        db.query(func.avg(func.extract("epoch", AuditLog.created_at - Invoice.created_at)))
        .join(Invoice, AuditLog.invoice_id == Invoice.id)
        .scalar()
    )

    rows = (
        db.query(
            func.date(Invoice.created_at).label("day"),
            Invoice.status,
            func.count(Invoice.id),
        )
        .group_by("day", Invoice.status)
        .order_by("day")
        .all()
    )
    by_day: dict = defaultdict(lambda: {s: 0 for s in _STATUSES})
    for day, status, count in rows:
        if status in _STATUSES:
            by_day[day][status] = count

    decisions_over_time = [
        DecisionsOverTimePoint(date=day, **counts)
        for day, counts in sorted(by_day.items(), key=lambda kv: kv[0])
    ]

    return MetricsResponse(
        total_invoices=total,
        touchless_rate_pct=round(touchless_rate, 1),
        auto_approved_count=auto_approved,
        exception_count=exception,
        fraud_flag_count=fraud_flag,
        avg_cycle_time_seconds=round(avg_cycle_seconds, 3) if avg_cycle_seconds is not None else None,
        decisions_over_time=decisions_over_time,
    )
