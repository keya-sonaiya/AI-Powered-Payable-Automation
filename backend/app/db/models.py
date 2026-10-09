"""
ORM models — the full data model for the project (Phase 1 scope). All 3
phases share this schema; do not add columns later without updating
schema.sql to match.
"""
from sqlalchemy import Column, Integer, String, Numeric, Date, ForeignKey, Text, TIMESTAMP
from sqlalchemy.sql import func

from .database import Base


class Vendor(Base):
    __tablename__ = "vendors"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    tax_id = Column(String)
    payment_terms = Column(String)


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    id = Column(Integer, primary_key=True)
    po_number = Column(String, unique=True, nullable=False)
    vendor_id = Column(Integer, ForeignKey("vendors.id"))
    amount = Column(Numeric)
    quantity = Column(Numeric)              # needed for a real 3-way match
    unit_price = Column(Numeric)
    status = Column(String, default="open")  # "open" | "closed"


class Receipt(Base):
    __tablename__ = "receipts"
    id = Column(Integer, primary_key=True)
    po_id = Column(Integer, ForeignKey("purchase_orders.id"))
    quantity_received = Column(Numeric)
    received_date = Column(Date)


class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True)
    invoice_number = Column(String, nullable=False)
    vendor_id = Column(Integer, ForeignKey("vendors.id"))
    po_number = Column(String)
    amount = Column(Numeric)
    quantity = Column(Numeric)
    unit_price = Column(Numeric)
    raw_ocr_text = Column(Text)
    extracted_json = Column(Text)
    status = Column(String)  # pending | auto_approved | exception |
                              # fraud_flag | needs_manual_review
    created_at = Column(TIMESTAMP, server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    match_result = Column(Text)  # JSON: amount + quantity variance, PO status
    policy_rule_applied = Column(String)
    llm_explanation = Column(Text)
    decision = Column(String)
    created_at = Column(TIMESTAMP, server_default=func.now())
