# AP Agent Demo Cheatsheet

## 60-second architecture walkthrough

1. n8n reads invoice files and orchestrates the intake request. It contains no matching or policy logic.
2. FastAPI is the only application service that talks to Postgres. `/ingest` performs OCR when needed, asks Ollama to extract fields, resolves the vendor, matches the PO and receipt, and calls the pure-Python policy engine.
3. The policy engine owns the decision: `auto_approved`, `exception`, or `fraud_flag`. Ollama never decides.
4. FastAPI asks Chroma for the policy clause matching the rule, then asks Ollama for plain-English explanation text.
5. Invoice and AuditLog are committed in one transaction. Next.js calls FastAPI for dashboard metrics, invoices, and audit history.

## Start the stack

```powershell
Copy-Item .env.example .env
# Set OLLAMA_API_KEY in .env, then:
docker compose up --build
```

URLs:

- Dashboard: http://localhost:3000
- Audit trail: http://localhost:3000/audit
- Backend health: http://localhost:8000/health
- n8n: http://localhost:5678

## Smoke-test commands

Check the seed data after Postgres is healthy:

```powershell
docker compose exec postgres psql -U apagent -d ap_agent_demo -c "select count(*) from vendors; select count(*) from purchase_orders; select count(*) from receipts;"
```

Expected counts are `20`, `180`, and `180`.

Submit a clean invoice through the real extraction path:

```powershell
curl.exe -s -X POST http://localhost:8000/ingest `
  -H "Content-Type: application/json" `
  -d '{"raw_text":"INVOICE\nInvoice Number: INV-31726318\nVendor: Shields-Brown\nPO Number: PO-100001\nQuantity: 293\nAmount: $14611.91"}'
```

This record is a clean match, but its amount is above the $5,000 auto-approval ceiling, so the policy may correctly return an exception. Use a clean mock record at or below that threshold to demonstrate `auto_approved`.

Inspect the API surfaces:

```powershell
curl.exe -s http://localhost:8000/metrics
curl.exe -s "http://localhost:8000/invoices?limit=10"
curl.exe -s "http://localhost:8000/audit-log?limit=10"
```

For the missing-key error contract, temporarily clear `OLLAMA_API_KEY`, restart the backend, and expect HTTP `502`, not `500`:

```powershell
curl.exe -s -w "`n%{http_code}`n" -X POST http://localhost:8000/ingest `
  -H "Content-Type: application/json" `
  -d '{"raw_text":"INVOICE\nInvoice Number: INV-X\nVendor: Acme\nPO Number: PO-100001\nAmount: $100.00"}'
```

## Decision paths to demonstrate

Use records from `mock_data/output/mock_dataset.json` and render their fields into the same OCR-style text payload:

- Clean match: `auto_approved` when amount is within tolerance and at most $5,000.
- Amount mismatch: `exception` with `AMOUNT_VARIANCE_OR_THRESHOLD_EXCEEDED`.
- Quantity mismatch: `exception` with `QUANTITY_VARIANCE_EXCEEDS_GUARDRAIL`.
- Unknown PO: `exception` with `NO_MATCHING_PO`.
- Closed PO: `exception` with `PO_CLOSED`.
- Same invoice number and vendor twice: first normal, second `fraud_flag` with `DUPLICATE_INVOICE_NUMBER`.

## Interview follow-ups

**Why does Ollama not make the decision?**
The policy engine must be deterministic, auditable, and unit-testable; the model only extracts fields and writes explanations.

**Why are there two API URLs in the frontend configuration?**
The browser reaches `localhost:8000`, while server-side Next.js rendering reaches `backend:8000` over the Docker network.

**How is duplicate detection scoped?**
By `(vendor_id, invoice_number)`, so two vendors can legitimately use the same invoice number.

**What makes the audit trail reliable?**
The invoice and its AuditLog row are persisted in one database transaction after the decision and explanation are complete.
