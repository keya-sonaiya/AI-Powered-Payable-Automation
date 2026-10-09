"""
Seeds vendors / purchase_orders / receipts from mock_data/output/mock_dataset.json
on startup, if the vendors table is empty.

This is a Phase 2 addition beyond the original file list: matching_engine.py
and the duplicate check need vendors/POs/receipts already in Postgres before
any invoice can be POSTed to /ingest, and nothing else in the pipeline was
responsible for loading them. Invoices are deliberately NOT seeded here —
they flow through the real /ingest pipeline (via the n8n workflow), so the
demo actually exercises OCR-text handling, LLM extraction, matching, and the
policy engine end-to-end, instead of arriving pre-decided.
"""
from __future__ import annotations

import json
import os
from datetime import date

from app.config import settings
from app.db.database import SessionLocal
from app.db.models import PurchaseOrder, Receipt, Vendor


def seed_if_empty() -> None:
    db = SessionLocal()
    try:
        if db.query(Vendor.id).first() is not None:
            return  # already seeded

        if not os.path.exists(settings.mock_data_path):
            # mock_data/generate_mock_data.py hasn't been run / mounted yet —
            # nothing to seed, and /ingest will just report NO_MATCHING_PO /
            # unresolved-vendor for everything until it has.
            return

        with open(settings.mock_data_path, encoding="utf-8") as f:
            dataset = json.load(f)

        for v in dataset.get("vendors", []):
            db.add(Vendor(
                id=v["id"],
                name=v["name"],
                tax_id=v.get("tax_id"),
                payment_terms=v.get("payment_terms"),
            ))
        # Flush vendors before adding POs. With autoflush=False and explicit
        # PKs on every table, SQLAlchemy 2.0's insertmanyvalues batching does
        # NOT reliably reorder cross-table inserts by FK dependency when
        # everything is queued into a single flush — reproduced locally: POs
        # were sent to Postgres before their referenced vendor rows, raising
        # ForeignKeyViolation. Flushing per entity type forces the correct
        # order without changing the single-transaction/single-commit shape.
        db.flush()

        for po in dataset.get("purchase_orders", []):
            db.add(PurchaseOrder(
                id=po["id"],
                po_number=po["po_number"],
                vendor_id=po["vendor_id"],
                amount=po["amount"],
                quantity=po.get("quantity"),
                unit_price=po.get("unit_price"),
                status=po.get("status", "open"),
            ))
        db.flush()  # POs must exist before receipts (receipts.po_id FK)

        for r in dataset.get("receipts", []):
            received_date = r.get("received_date")
            if isinstance(received_date, str):
                received_date = date.fromisoformat(received_date)
            db.add(Receipt(
                id=r["id"],
                po_id=r["po_id"],
                quantity_received=r["quantity_received"],
                received_date=received_date,
            ))

        db.commit()
    finally:
        db.close()
