# API Contract

**Status: complete (Phase 2).** Phase 3 builds the entire Next.js frontend
from this file alone (plus `PROGRESS.md` and `.env.example`) — without
reading any backend Python. Base URL: `NEXT_PUBLIC_API_URL`
(`http://localhost:8000` by default).

All decision values are one of: `"auto_approved"`, `"exception"`,
`"fraud_flag"`. All `rule_applied` values are one of:
`WITHIN_TOLERANCE_AND_THRESHOLD`, `AMOUNT_VARIANCE_OR_THRESHOLD_EXCEEDED`,
`QUANTITY_VARIANCE_EXCEEDS_GUARDRAIL`, `NO_MATCHING_PO`, `PO_CLOSED`,
`DUPLICATE_INVOICE_NUMBER`, `PO_AMOUNT_INVALID` (see
`backend/policies/ap_policy.md` for what each means).

Errors: on failure, every endpoint returns FastAPI's default shape
`{"detail": "<message>"}` with a 4xx/5xx status code (e.g. 400 for a bad
`/ingest` payload, 404 for an unknown invoice id, 422 for a request that
fails Pydantic validation, 502 if the Ollama Cloud call itself fails).

---

## POST /ingest

The pipeline entry point. Called by the n8n workflow (or manually / via
curl for testing) — this is the ONLY way new invoices enter the system.

**Request body**

```json
{
  "raw_text": "INVOICE\nInvoice Number: INV-12345\nVendor: Acme Corp\nPO Number: PO-100042\nAmount: $2450.00\nQuantity: 50\nUnit Price: $49.00",
  "file_path": null
}
```

Provide exactly one of `raw_text` (already-OCR'd or synthetic invoice text)
or `file_path` (a PDF/image path the backend will OCR via Tesseract). If
`raw_text` is present, `file_path` is ignored. Providing neither returns
`400`.

**Response `200`**

```json
{
  "invoice_id": 201,
  "vendor_id": 4,
  "extracted": {
    "invoice_number": "INV-12345",
    "vendor_name": "Acme Corp",
    "po_number": "PO-100042",
    "amount": 2450.0,
    "quantity": 50,
    "unit_price": 49.0,
    "invoice_date": null
  },
  "decision": {
    "decision": "auto_approved",
    "rule_applied": "WITHIN_TOLERANCE_AND_THRESHOLD",
    "amount_variance_pct": 0.0,
    "quantity_variance_pct": 0.0
  },
  "explanation": "This invoice was auto-approved because its amount exactly matches purchase order PO-100042 (0% variance) and falls under the $5,000 auto-approval ceiling, satisfying the WITHIN_TOLERANCE_AND_THRESHOLD guardrail."
}
```

`vendor_id` is `null` if the vendor couldn't be resolved from the extracted
vendor name or the matched PO. `amount_variance_pct` / `quantity_variance_pct`
are `null` when the decision short-circuited before a variance could be
computed (`fraud_flag`/duplicate, `NO_MATCHING_PO`, `PO_CLOSED`,
`PO_AMOUNT_INVALID`).

---

## GET /invoices

Paginated invoice list, newest first.

**Query params** (all optional)
| Param | Type | Notes |
|---|---|---|
| `status` | string | Filter: `auto_approved` \| `exception` \| `fraud_flag` |
| `vendor_id` | int | Filter by vendor |
| `limit` | int | Default 50, max 200 |
| `offset` | int | Default 0 |

**Response `200`**

```json
{
  "total": 200,
  "limit": 50,
  "offset": 0,
  "items": [
    {
      "id": 201,
      "invoice_number": "INV-12345",
      "vendor_id": 4,
      "po_number": "PO-100042",
      "amount": 2450.0,
      "quantity": 50,
      "unit_price": 49.0,
      "status": "auto_approved",
      "created_at": "2026-09-17T14:32:01.123456"
    }
  ]
}
```

## GET /invoices/{invoice_id}

**Response `200`**: a single object with the same shape as one item in
`/invoices`' `items` array above. **`404`** if the id doesn't exist.

---

## GET /audit-log

Paginated audit trail, newest first — the full decision trail per invoice
(match result, rule applied, LLM explanation).

**Query params** (all optional)
| Param | Type | Notes |
|---|---|---|
| `invoice_id` | int | Filter to one invoice's audit row(s) |
| `decision` | string | Filter: `auto_approved` \| `exception` \| `fraud_flag` |
| `limit` | int | Default 50, max 200 |
| `offset` | int | Default 0 |

**Response `200`**

```json
{
  "total": 200,
  "limit": 50,
  "offset": 0,
  "items": [
    {
      "id": 201,
      "invoice_id": 201,
      "match_result": "{\"po\": {\"id\": 42, \"po_number\": \"PO-100042\", \"vendor_id\": 4, \"amount\": \"2450.00\", \"quantity\": \"50.00\", \"unit_price\": \"49.00\", \"status\": \"open\"}, \"receipt\": {\"id\": 42, \"po_id\": 42, \"quantity_received\": \"50.00\", \"received_date\": \"2026-08-01\"}, \"amount_variance_pct\": \"0\", \"quantity_variance_pct\": \"0\"}",
      "policy_rule_applied": "WITHIN_TOLERANCE_AND_THRESHOLD",
      "llm_explanation": "This invoice was auto-approved because its amount exactly matches purchase order PO-100042 (0% variance) and falls under the $5,000 auto-approval ceiling, satisfying the WITHIN_TOLERANCE_AND_THRESHOLD guardrail.",
      "decision": "auto_approved",
      "created_at": "2026-09-17T14:32:01.456789"
    }
  ]
}
```

`match_result` is a JSON **string** (not a nested object) — the frontend
must `JSON.parse()` it if it wants to render the PO/receipt/variance detail
rather than showing the raw string. It mirrors `AuditLog.match_result`'s
storage as `TEXT` in Postgres.

---

## GET /metrics

Dashboard summary. No query params.

**Response `200`**

```json
{
  "total_invoices": 200,
  "touchless_rate_pct": 8.0,
  "auto_approved_count": 16,
  "exception_count": 164,
  "fraud_flag_count": 20,
  "avg_cycle_time_seconds": 0.042,
  "decisions_over_time": [
    { "date": "2026-09-17", "auto_approved": 16, "exception": 164, "fraud_flag": 20 }
  ]
}
```

`touchless_rate_pct` = `auto_approved_count / total_invoices * 100`, rounded
to 1 decimal. `avg_cycle_time_seconds` is the average gap between an
invoice's `created_at` and its audit log row's `created_at` (both written in
the same transaction, so this is near-instant per invoice — it's a
placeholder for "processing latency," not a meaningful cycle-time metric in
this demo since there's no async queueing between ingest and decision).
`decisions_over_time` has one entry per calendar day that has invoices, each
day's counts summing to that day's invoice volume.

**Note on `touchless_rate_pct`:** with the mock dataset (seed 42), only 16
of the 110 `clean_match`-scenario invoices are actually ≤ $5,000 and thus
eligible for `WITHIN_TOLERANCE_AND_THRESHOLD` auto-approval — the rest
correctly land in `exception` under `AMOUNT_VARIANCE_OR_THRESHOLD_EXCEEDED`
purely because of the $5,000 ceiling, even with 0% variance. So the
dashboard's touchless rate will read closer to 8% than 55% — expected
behavior per `ap_policy.md`, not a bug, but worth calling out on the
dashboard (e.g. a caption) so it doesn't look broken. See PROGRESS.md.

---

## GET /health

Liveness check, no auth, no params.

**Response `200`**: `{"status": "ok"}`
