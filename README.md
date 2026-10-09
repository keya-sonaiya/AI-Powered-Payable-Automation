# AP Agent Demo

A self-hosted portfolio demo that mirrors an accounts-payable agent pipeline:
invoice intake → OCR-shaped text → LLM extraction → three-way matching →
deterministic policy guardrails → audit trail → dashboard.

## Architecture

1. FastAPI is the only service that reads or writes PostgreSQL.
2. n8n orchestrates invoice intake only; it calls `POST /ingest` and contains
   no business decision logic.
3. Next.js calls FastAPI only, never n8n or Ollama directly.
4. Ollama Cloud (`gpt-oss:120b`) extracts invoice fields and writes auditor
   explanations. The deterministic Python policy engine makes every decision.
5. Invoice and audit-log records are written in one database transaction.
6. The three-way match independently evaluates PO amount, received quantity,
   and billed quantity.

## Setup

Prerequisites: Docker Desktop with Docker Compose, plus an Ollama Cloud API
key for live extraction and explanations.

1. **Configure the environment**

   ```powershell
   Copy-Item .env.example .env
   ```

   Set `OLLAMA_API_KEY` in `.env`. The defaults work for a local Compose run.
   The default n8n schedule and audit display timezone is `Asia/Kolkata`
   (UTC+05:30). `NEXT_PUBLIC_API_URL` is baked into the browser bundle, so a
   change to it requires a frontend rebuild.

2. **Generate the mock dataset**

   ```powershell
   cd mock_data
   pip install -r requirements.txt
   python generate_mock_data.py
   cd ..
   ```

   This creates `mock_data/output/mock_dataset.json` with 200 invoices, 20
   vendors, 180 POs/receipts, and clean, amount-mismatch, quantity-mismatch,
   missing-PO, closed-PO, and duplicate scenarios.

3. **Build and start the stack**

   ```powershell
   docker compose up --build -d
   ```

   - Dashboard: http://localhost:3000
   - Backend API and docs: http://localhost:8000/docs
   - n8n editor: http://localhost:5678

4. **Import and activate the n8n workflow**

   In n8n, choose **Workflows → Import from File** and select
   `n8n/workflows/invoice_intake_workflow.json`, then activate it. Confirm the
   workflow contains this loop:

   ```text
   Render invoice as OCR text
     → Process one invoice at a time
     → POST /ingest
     → Process one invoice at a time
   ```

   The batch size of one is intentional. It prevents Ollama Cloud request
   bursts and PostgreSQL connection-pool exhaustion. A 200-invoice replay
   takes several minutes.

5. **Explore the dashboard**

   - The dashboard shows decision metrics, charts, and the latest audit rows.
   - The **Send a sample invoice** panel sends a request through the same
     FastAPI ingest pipeline as n8n.
   - The audit trail supports pagination and filtering; expand a row to see
     matched PO/receipt facts, amount and quantity variance, and the LLM
     explanation.
   - Dashboard and audit data refresh automatically every five seconds while
     the tab is visible. Audit timestamps are rendered in IST (UTC+05:30).

## Operational notes

- If `GENERIC_TIMEZONE` changes, recreate n8n after an active replay finishes:

  ```powershell
  docker compose up -d --no-deps n8n
  ```

- After changing frontend source or `NEXT_PUBLIC_API_URL`, rebuild it:

  ```powershell
  docker compose up -d --build frontend
  ```

  Use one browser hard refresh to load a newly deployed client bundle.

- Replaying the same mock dataset intentionally creates duplicate-invoice
  fraud flags after the first run. This demo has no idempotency or run-reset
  endpoint.

## Deliberate demo limitations

- No authentication or authorization.
- No Alembic migrations; schema creation uses `Base.metadata.create_all()`.
- Chroma has no mounted persistent volume and re-embeds its small policy file
  on backend restart.
- The serial workflow favors reliable upstream usage over high throughput.

See [HANDOVER.md](HANDOVER.md) for operating and verification details,
[PROGRESS.md](PROGRESS.md) for the build history, and
[API_CONTRACT.md](API_CONTRACT.md) for endpoint shapes.
