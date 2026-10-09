"""
POST /ingest — single entry point n8n calls for every simulated invoice
intake channel (email / portal / EDI). Runs the full pipeline: OCR (if a
file_path was given, offloaded to a thread — see ocr_service's docstring),
LLM extraction, 3-way matching, policy_engine.evaluate() for the actual
decision, an LLM explanation grounded in the retrieved policy clause, then
persists the Invoice + AuditLog rows in a single transaction so the two can
never drift out of sync.
"""
from __future__ import annotations

import asyncio
import json
from decimal import Decimal, InvalidOperation
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.db.database import get_db
from app.db.models import AuditLog, Invoice
from app.schemas.invoice import IngestRequest, IngestResponse
from app.services import llm_service, matching_engine, ocr_service, policy_engine

router = APIRouter()

# Guard the *whole* ingest, rather than only the outbound LLM request. Once a
# matching query starts, SQLAlchemy holds a PostgreSQL connection until the
# invoice and audit-log transaction commits. A burst of n8n requests otherwise
# exhausts the default QueuePool (5 persistent + 10 overflow connections).
_ingest_semaphore = asyncio.Semaphore(settings.ingest_max_concurrency)


def _to_decimal(value) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


async def _process_ingest(payload: IngestRequest, db: Session) -> IngestResponse:
    if not payload.raw_text and not payload.file_path:
        raise HTTPException(status_code=400, detail="Provide raw_text or file_path")

    raw_text = payload.raw_text
    if not raw_text:
        # Blocking Tesseract call — offloaded per ocr_service.py's docstring,
        # never awaited directly inside this async def.
        raw_text = await asyncio.to_thread(ocr_service.extract_text, payload.file_path)

    extracted = await llm_service.extract_invoice_fields(raw_text)

    vendor_id = matching_engine.resolve_vendor_id(
        db, extracted.get("vendor_name"), extracted.get("po_number")
    )
    is_duplicate = matching_engine.check_duplicate(
        db, vendor_id, extracted.get("invoice_number")
    )
    po, receipt = matching_engine.find_matching_po_and_receipt(
        db, extracted.get("po_number")
    )

    policy_invoice = {
        "amount": _to_decimal(extracted.get("amount")) or Decimal("0"),
        "quantity": _to_decimal(extracted.get("quantity")),
    }
    policy_po = None
    if po is not None:
        policy_po = {"amount": _to_decimal(po["amount"]), "status": po["status"]}
    policy_receipt = None
    if receipt is not None:
        policy_receipt = {"quantity_received": _to_decimal(receipt["quantity_received"])}

    decision = policy_engine.evaluate(policy_invoice, policy_po, policy_receipt, is_duplicate)

    explanation = await llm_service.explain_decision(
        extracted, {"po": po, "receipt": receipt}, decision
    )

    invoice_row = Invoice(
        invoice_number=extracted.get("invoice_number") or "UNKNOWN",
        vendor_id=vendor_id,
        po_number=extracted.get("po_number"),
        amount=_to_decimal(extracted.get("amount")),
        quantity=_to_decimal(extracted.get("quantity")),
        unit_price=_to_decimal(extracted.get("unit_price")),
        raw_ocr_text=raw_text,
        extracted_json=json.dumps(extracted, default=str),
        status=decision["decision"],
    )
    db.add(invoice_row)
    db.flush()  # populate invoice_row.id for the AuditLog FK, before commit

    match_result = {
        "po": po,
        "receipt": receipt,
        "amount_variance_pct": decision.get("amount_variance_pct"),
        "quantity_variance_pct": decision.get("quantity_variance_pct"),
    }

    audit_row = AuditLog(
        invoice_id=invoice_row.id,
        match_result=json.dumps(match_result, default=str),
        policy_rule_applied=decision["rule_applied"],
        llm_explanation=explanation,
        decision=decision["decision"],
    )
    db.add(audit_row)
    db.commit()
    db.refresh(invoice_row)

    return IngestResponse(
        invoice_id=invoice_row.id,
        vendor_id=vendor_id,
        extracted=extracted,
        decision=decision,
        explanation=explanation,
    )


@router.post("/ingest", response_model=IngestResponse)
async def ingest_invoice(payload: IngestRequest, db: Session = Depends(get_db)):
    # Waiting requests do not check out a database connection: get_db creates
    # a Session lazily, and _process_ingest is the first code that queries it.
    async with _ingest_semaphore:
        return await _process_ingest(payload, db)
