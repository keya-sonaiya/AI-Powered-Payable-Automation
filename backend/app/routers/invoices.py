"""GET /invoices (paginated, filterable), GET /invoices/{id}."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Invoice
from app.schemas.invoice import InvoiceListResponse, InvoiceOut

router = APIRouter()


@router.get("/invoices", response_model=InvoiceListResponse)
def list_invoices(
    status: Optional[str] = Query(
        None, description="Filter by decision status: auto_approved | exception | fraud_flag"
    ),
    vendor_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(Invoice)
    if status:
        q = q.filter(Invoice.status == status)
    if vendor_id is not None:
        q = q.filter(Invoice.vendor_id == vendor_id)

    total = q.count()
    items = q.order_by(Invoice.created_at.desc()).offset(offset).limit(limit).all()

    return InvoiceListResponse(total=total, limit=limit, offset=offset, items=items)


@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice
