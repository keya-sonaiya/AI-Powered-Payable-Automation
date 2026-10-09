"""
Pydantic request/response models for every endpoint. Kept exhaustive —
API_CONTRACT.md is written from these, and Phase 3 builds the entire
frontend from that doc alone, without reading backend Python.
"""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ── /ingest ──────────────────────────────────────────────────────────────

class IngestRequest(BaseModel):
    raw_text: Optional[str] = Field(
        None, description="Raw OCR text for the invoice. Provide this OR file_path."
    )
    file_path: Optional[str] = Field(
        None, description="Path to a PDF/image to OCR. Ignored if raw_text is provided."
    )


class ExtractedInvoiceFields(BaseModel):
    invoice_number: Optional[str] = None
    vendor_name: Optional[str] = None
    po_number: Optional[str] = None
    amount: Optional[float] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    invoice_date: Optional[str] = None


class DecisionResult(BaseModel):
    decision: str  # auto_approved | exception | fraud_flag
    rule_applied: str
    amount_variance_pct: Optional[float] = None
    quantity_variance_pct: Optional[float] = None


class IngestResponse(BaseModel):
    invoice_id: int
    vendor_id: Optional[int] = None
    extracted: ExtractedInvoiceFields
    decision: DecisionResult
    explanation: str


# ── /invoices ────────────────────────────────────────────────────────────

class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_number: str
    vendor_id: Optional[int] = None
    po_number: Optional[str] = None
    amount: Optional[float] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    status: str
    created_at: datetime


class InvoiceListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[InvoiceOut]


# ── /audit-log ───────────────────────────────────────────────────────────

class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_id: int
    match_result: Optional[str] = None
    policy_rule_applied: Optional[str] = None
    llm_explanation: Optional[str] = None
    decision: str
    created_at: datetime


class AuditLogListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[AuditLogOut]


# ── /metrics ─────────────────────────────────────────────────────────────

class DecisionsOverTimePoint(BaseModel):
    date: date
    auto_approved: int = 0
    exception: int = 0
    fraud_flag: int = 0


class MetricsResponse(BaseModel):
    total_invoices: int
    touchless_rate_pct: float
    auto_approved_count: int
    exception_count: int
    fraud_flag_count: int
    avg_cycle_time_seconds: Optional[float] = None
    decisions_over_time: list[DecisionsOverTimePoint]


# ── shared error shape (FastAPI's default {"detail": str} applies) ───────

class ErrorResponse(BaseModel):
    detail: str
