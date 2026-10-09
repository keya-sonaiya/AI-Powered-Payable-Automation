# AP Agent Demo — Operating Handover

## Status

**Complete and verified end-to-end.** Docker Compose runs Postgres, FastAPI,
the Next.js frontend, and n8n. A live Ollama Cloud API key is required for
invoice extraction and audit explanations.

## Start or resume

1. Create `.env` from `.env.example` and set `OLLAMA_API_KEY`.
2. Generate `mock_data/output/mock_dataset.json` if it is missing:

   ```powershell
   cd mock_data
   pip install -r requirements.txt
   python generate_mock_data.py
   cd ..
   ```

3. Start the stack:

   ```powershell
   docker compose up --build -d
   ```

4. In n8n (http://localhost:5678), import and activate
   `n8n/workflows/invoice_intake_workflow.json` when it is not already
   present. It must contain the following loop:

   ```text
   Render invoice as OCR text
     → Process one invoice at a time
     → POST /ingest
     → Process one invoice at a time
   ```

5. Use http://localhost:3000 for the dashboard and
   http://localhost:3000/audit for the audit trail.

## What has been verified

- The database seeds 20 vendors, 180 purchase orders, and 180 receipts.
- Live ingestion completed LLM extraction, Chroma policy retrieval, matching,
  deterministic policy evaluation, explanation generation, and atomic Invoice
  plus AuditLog persistence.
- Persisted audits include all six expected rule outcomes: clean approval,
  amount/threshold exception, quantity exception, missing PO, closed PO, and
  duplicate fraud flag. Non-zero amount and quantity variances were confirmed.
- Chroma returned the relevant `Auto-Approval Threshold` clause from the
  running backend.
- n8n 2.39 was imported and activated; sequential n8n-originated requests
  received successful `POST /ingest` responses while invoice totals increased.
- The production frontend build succeeded. Dashboard, audit, and filtered-audit
  routes return live FastAPI data and update every five seconds while visible.
- n8n scheduling and audit timestamp rendering use `Asia/Kolkata` / IST
  (UTC+05:30).

## Reliability controls

- The n8n loop is batch-size one. It prevents the 200-item mock replay from
  creating an Ollama Cloud request burst.
- `OLLAMA_MAX_CONCURRENCY=1` serializes Cloud requests and retries 429 rate
  limits with exponential backoff.
- `INGEST_MAX_CONCURRENCY=1` limits whole ingests. Queued requests do not
  check out a PostgreSQL connection, preventing SQLAlchemy QueuePool starvation
  of the dashboard and audit endpoints.

## Operations

- Apply a changed `GENERIC_TIMEZONE` after any active replay finishes:

  ```powershell
  docker compose up -d --no-deps n8n
  ```

- Apply frontend source or `NEXT_PUBLIC_API_URL` changes:

  ```powershell
  docker compose up -d --build frontend
  ```

  A browser hard refresh loads a newly deployed client bundle once.

- Replaying the same mock data intentionally creates duplicate-invoice fraud
  flags. The demo does not have idempotent replay or a run-reset endpoint.

## Security and known limitations

`.gitignore` excludes `.env`, local Chroma data, Python caches, and frontend
build/dependency artifacts. If an API key was ever shared outside its intended
secret store, the account owner should rotate it in Ollama and update `.env`.

The remaining limitations are deliberate for a demo: no authentication,
Alembic migrations, persistent Chroma volume, async job queue, or idempotent
replay/reset capability. Serial intake prioritizes reliability over throughput,
so a 200-invoice run takes several minutes.
