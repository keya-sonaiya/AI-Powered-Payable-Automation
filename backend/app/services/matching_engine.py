"""
3-way matching helpers. Every function here takes the request-scoped
SQLAlchemy session (injected by FastAPI's get_db dependency) as its first
argument — this module never opens its own DB connection, keeping FastAPI
the single source of truth.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import Invoice, PurchaseOrder, Receipt, Vendor


def find_matching_po_and_receipt(
    db: Session, po_number: Optional[str]
) -> tuple[Optional[dict], Optional[dict]]:
    """
    Returns (po_dict, receipt_dict). Either or both may be None — a missing
    PO or receipt is a normal, expected outcome (see NO_MATCHING_PO in
    ap_policy.md), not a pipeline error, so this never throws.
    """
    if not po_number:
        return None, None

    po = db.query(PurchaseOrder).filter(PurchaseOrder.po_number == po_number).first()
    if po is None:
        return None, None

    po_dict = {
        "id": po.id,
        "po_number": po.po_number,
        "vendor_id": po.vendor_id,
        "amount": po.amount,
        "quantity": po.quantity,
        "unit_price": po.unit_price,
        "status": po.status,
    }

    # One receipt per PO in the mock dataset; order_by(id) keeps behavior
    # deterministic if that assumption ever changes.
    receipt = (
        db.query(Receipt)
        .filter(Receipt.po_id == po.id)
        .order_by(Receipt.id)
        .first()
    )
    receipt_dict = None
    if receipt is not None:
        receipt_dict = {
            "id": receipt.id,
            "po_id": receipt.po_id,
            "quantity_received": receipt.quantity_received,
            "received_date": receipt.received_date,
        }

    return po_dict, receipt_dict


def check_duplicate(
    db: Session, vendor_id: Optional[int], invoice_number: Optional[str]
) -> bool:
    """
    Duplicate detection keyed on (vendor_id, invoice_number) — not
    invoice_number alone — since different vendors may legitimately reuse
    the same invoice numbering scheme.
    """
    if not vendor_id or not invoice_number:
        return False

    existing = (
        db.query(Invoice.id)
        .filter(
            Invoice.vendor_id == vendor_id,
            Invoice.invoice_number == invoice_number,
        )
        .first()
    )
    return existing is not None


def resolve_vendor_id(
    db: Session, vendor_name: Optional[str], po_number: Optional[str] = None
) -> Optional[int]:
    """
    Best-effort vendor resolution from the LLM-extracted vendor name (exact
    then fuzzy match against Vendor.name). Falls back to the matching PO's
    own vendor_id when available, since that's a foreign-key fact rather
    than a string match and is more reliable when the LLM's OCR-derived
    vendor name is noisy.
    """
    vendor = None
    if vendor_name and vendor_name.strip():
        cleaned = vendor_name.strip()
        vendor = db.query(Vendor).filter(Vendor.name.ilike(cleaned)).first()
        if vendor is None:
            vendor = db.query(Vendor).filter(Vendor.name.ilike(f"%{cleaned}%")).first()

    if vendor is None and po_number:
        po = db.query(PurchaseOrder).filter(PurchaseOrder.po_number == po_number).first()
        if po is not None:
            vendor = db.query(Vendor).filter(Vendor.id == po.vendor_id).first()

    return vendor.id if vendor is not None else None
