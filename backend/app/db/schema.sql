-- Raw DDL mirroring app/db/models.py exactly. Kept as a reference/alternative
-- to SQLAlchemy's create_all() (which is what actually runs on startup —
-- see PROGRESS.md: no Alembic for this demo).

CREATE TABLE IF NOT EXISTS vendors (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    tax_id VARCHAR,
    payment_terms VARCHAR
);

CREATE TABLE IF NOT EXISTS purchase_orders (
    id SERIAL PRIMARY KEY,
    po_number VARCHAR UNIQUE NOT NULL,
    vendor_id INTEGER REFERENCES vendors(id),
    amount NUMERIC,
    quantity NUMERIC,
    unit_price NUMERIC,
    status VARCHAR DEFAULT 'open'
);

CREATE TABLE IF NOT EXISTS receipts (
    id SERIAL PRIMARY KEY,
    po_id INTEGER REFERENCES purchase_orders(id),
    quantity_received NUMERIC,
    received_date DATE
);

CREATE TABLE IF NOT EXISTS invoices (
    id SERIAL PRIMARY KEY,
    invoice_number VARCHAR NOT NULL,
    vendor_id INTEGER REFERENCES vendors(id),
    po_number VARCHAR,
    amount NUMERIC,
    quantity NUMERIC,
    unit_price NUMERIC,
    raw_ocr_text TEXT,
    extracted_json TEXT,
    status VARCHAR, -- pending | auto_approved | exception | fraud_flag | needs_manual_review
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    invoice_id INTEGER REFERENCES invoices(id),
    match_result TEXT,          -- JSON: amount + quantity variance, PO status
    policy_rule_applied VARCHAR,
    llm_explanation TEXT,
    decision VARCHAR,
    created_at TIMESTAMP DEFAULT now()
);
