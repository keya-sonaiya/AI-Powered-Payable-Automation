# AP Agent Demo — Build Progress

## Architecture decisions locked in (later phases must not deviate)
- n8n IS containerized in docker-compose (resolves the original spec's contradiction)
- 3-way match checks quantity variance AND amount variance, as separate guardrails
- policy_engine.py has zero LLM/network calls — pure Python, unit-testable
- PurchaseOrder has a status field; closed POs auto-exception (rule PO_CLOSED)
- Duplicate detection key is (vendor_id, invoice_number) — not invoice_number alone
- Ollama Cloud: https://ollama.com + POST /api/chat + messages array + model
  "gpt-oss:120b" (Phase 2 implements this — do NOT use /api/generate)
- Migrations: Base.metadata.create_all() on startup, no Alembic
- CORS: Phase 2's main.py must add CORSMiddleware for FRONTEND_ORIGIN

## Phase 1 — Foundation: DONE
Built:
- docker-compose.yml (postgres, backend, frontend, n8n — all containerized, networked, env-wired)
- .env.example (every env var used across all 3 phases, commented)
- README.md (architecture rules; setup section deferred to Phase 3)
- API_CONTRACT.md (empty placeholder for Phase 2)
- backend/requirements.txt, backend/Dockerfile (installs tesseract-ocr + poppler-utils for later OCR use)
- backend/app/config.py (pydantic-settings, reads every env var)
- backend/app/db/database.py (engine, SessionLocal, Base, get_db dependency)
- backend/app/db/models.py (Vendor, PurchaseOrder, Receipt, Invoice, AuditLog — exact fixed pattern)
- backend/app/db/schema.sql (raw DDL mirroring models.py)
- backend/app/services/policy_engine.py (exact fixed pattern; unit-tested manually, see below)
- backend/app/services/ocr_service.py (Tesseract wrapper; docstring flags the async-offload requirement for Phase 2)
- backend/policies/ap_policy.md (one clause per heading, keyed to each rule_applied value, for clean Chroma retrieval)
- mock_data/generate_mock_data.py, mock_data/requirements.txt (fixed pattern: no dead branches, duplicates tagged up front)
- mock_data/output/mock_dataset.json (generated and validated — see counts below)
- TODO placeholders for every Phase 2/3 file (main.py, all routers, llm_service.py,
  matching_engine.py, vector_store.py, schemas/invoice.py, n8n workflow JSON, frontend/package.json + Dockerfile)
- __init__.py files for all backend Python packages

Verified:
- Mock data generator ran clean and produced valid JSON: **200 invoices**, mix —
  clean_match 110 (55.0%), amount_mismatch 20 (10.0%), quantity_mismatch 20 (10.0%),
  no_matching_po 20 (10.0%), closed_po 10 (5.0%), duplicate 20 (10.0%). Matches the
  target mix exactly. 20 vendors, 180 purchase orders, 180 receipts generated
  alongside the invoices.
- policy_engine.evaluate() manually exercised against all 5 decision paths
  (auto_approved, fraud_flag/duplicate, exception/no PO, exception/closed PO,
  exception/quantity variance) — all returned the correct decision + rule_applied.

## Phase 2 — Backend Logic & API: DONE
Built:
- backend/app/services/matching_engine.py — find_matching_po_and_receipt(db, po_number)
  returns (None, None) rather than throwing when nothing matches; check_duplicate(db,
  vendor_id, invoice_number) keyed on (vendor_id, invoice_number); resolve_vendor_id()
  added (not in the original file list — see "Design decisions added in Phase 2" below)
- backend/app/services/vector_store.py — Chroma embedded/local client, splits
  ap_policy.md into one clause per `##` heading, tags each with its rule_applied value
  parsed from the heading's parenthetical. get_relevant_clauses(rule_applied, k) tries
  an exact metadata match first, falls back to semantic query — and IS actually called
  from llm_service.explain_decision(), unlike the original spec's diagram
- backend/app/services/llm_service.py — extract_invoice_fields() + explain_decision(),
  using the corrected Ollama Cloud API (POST {OLLAMA_HOST}/api/chat, messages array,
  model "gpt-oss:120b", "format": "json" for extraction)
- backend/app/schemas/invoice.py — exhaustive Pydantic models for every endpoint
- backend/app/routers/ingest.py — POST /ingest: OCR (asyncio.to_thread) or raw_text ->
  LLM extraction -> vendor resolution -> duplicate check -> PO/receipt match ->
  policy_engine.evaluate() -> LLM explanation -> Invoice + AuditLog persisted in one
  transaction (db.flush() for the FK, then a single db.commit())
- backend/app/routers/invoices.py — GET /invoices (paginated, filter by status/vendor),
  GET /invoices/{id}
- backend/app/routers/audit.py — GET /audit-log (paginated, filter by invoice_id/decision)
- backend/app/routers/metrics.py — GET /metrics (touchless rate, decision counts, avg
  cycle time via Postgres EXTRACT(EPOCH FROM ...), decisions-over-time series)
- backend/app/main.py — router registration, CORSMiddleware(FRONTEND_ORIGIN),
  Base.metadata.create_all() + seed_if_empty() on startup
- backend/app/db/seed.py — NEW FILE, not in the original list (see below)
- n8n/workflows/invoice_intake_workflow.json — real, importable n8n export: Schedule
  Trigger -> Read Binary File (mock_dataset.json) -> Extract From File (fromJson) ->
  Code node (renders each mock invoice's structured fields into synthetic OCR-style
  text) -> HTTP Request (POST http://backend:8000/ingest). Includes a Sticky Note
  flagging the one assumption (the Extract From File destination key) worth
  double-checking against the importer's exact n8n version.
- API_CONTRACT.md — exhaustive: every endpoint's method, path, example request/response,
  status codes, and the full enum of decision/rule_applied values

Design decisions added in Phase 2 (not in the original file list, but required for the
pipeline to actually run — flagging clearly since later phases should know these exist):
- **backend/app/db/seed.py + main.py startup hook**: nothing in the original spec loaded
  mock vendors/POs/receipts into Postgres, but matching_engine and the duplicate check
  need them there before any invoice can be POSTed to /ingest. On startup, if the
  `vendors` table is empty, seed.py loads vendors/purchase_orders/receipts (NOT
  invoices — those flow through the real /ingest pipeline) from MOCK_DATA_PATH
  (`/mock_data/output/mock_dataset.json` inside the container; docker-compose already
  mounted `./mock_data` there in Phase 1). Silently no-ops if that file doesn't exist
  yet (e.g. generator hasn't been run), so /health still comes up.
- **matching_engine.resolve_vendor_id()**: the LLM extracts a `vendor_name` string, not
  a `vendor_id` — something has to turn that into the FK matching_engine/policy_engine
  need. Tries exact then fuzzy (`ILIKE %name%`) match against `vendors.name`, falling
  back to the matched PO's own `vendor_id` (a real foreign-key fact, more reliable than
  a fuzzy string match) when a PO was found by `po_number`.
- **n8n Code node renders invoices as synthetic OCR text**, not raw JSON: mock_dataset.json
  invoices all have `raw_ocr_text: null` (see Phase 1 notes) by design — Phase 2 populates
  it. So the workflow builds a plain-text invoice block (`"INVOICE\nInvoice Number:
  ...\nVendor: ...\n..."`) per mock invoice and POSTs it as `{"raw_text": ...}`, which is
  what actually exercises the LLM extraction step end-to-end instead of bypassing it by
  feeding /ingest already-structured JSON.
- Added `chroma_persist_dir` and `mock_data_path` to config.py/`.env.example`, following
  the existing "every env var declared in config.py" convention.

Verified (mocking Ollama/Chroma network calls, real SQLAlchemy models + policy_engine +
matching_engine + seed against a throwaway SQLite DB, via FastAPI's TestClient):
- Startup seeds 20 vendors / 180 POs / 180 receipts from mock_dataset.json.
- All 6 decision paths produce the correct decision + rule_applied end-to-end through
  POST /ingest (not just policy_engine.evaluate() in isolation, as in Phase 1): a genuine
  auto_approved (clean match, amount ≤ $5,000), AMOUNT_VARIANCE_OR_THRESHOLD_EXCEEDED,
  QUANTITY_VARIANCE_EXCEEDS_GUARDRAIL, NO_MATCHING_PO, PO_CLOSED, and posting the same
  invoice twice correctly returns auto_approved then DUPLICATE_INVOICE_NUMBER/fraud_flag
  on the second POST.
- GET /invoices, GET /audit-log, GET /metrics all return correctly-shaped responses
  against the invoices ingested above.
- n8n workflow JSON validated as well-formed JSON (not re-verified against a running n8n
  instance — flagged via the Sticky Note in the workflow itself).

**Important note on the demo's touchless rate:** most `clean_match`-scenario invoices in
the seed-42 mock dataset exceed the $5,000 auto-approval ceiling (94 of 110), so they
correctly land in `exception` under `AMOUNT_VARIANCE_OR_THRESHOLD_EXCEEDED` even at 0%
variance — this is `ap_policy.md`'s stated guardrail working as designed, not a bug. Only
~16 invoices are actually eligible for `auto_approved`, so the dashboard's touchless rate
will read close to 8%, not the ~55% the scenario mix might suggest. Documented in
API_CONTRACT.md too — Phase 3 should show this rate as-is rather than "fixing" it.

## Phase 3 — Frontend & Wiring: DONE
Built entirely from `API_CONTRACT.md` + this file, per the Phase 3 prompt's instruction
— no backend Python was read to build it.

- Design direction: a "ledger book" identity (hairline rules, banded rows, ink-stamp
  decision badges) instead of generic SaaS-card chrome, since the audience is finance/
  audit. Fraunces (display) + IBM Plex Sans (body) + IBM Plex Mono (tabular figures —
  amounts, dates, ids). Written up as design tokens in `app/globals.css` before any
  component was built.
- `frontend/lib/types.ts` — TS types mirroring API_CONTRACT.md exactly (Decision,
  RuleApplied, Invoice, AuditLogEntry, Metrics, IngestRequest/Response,
  parseMatchResult() for the JSON-string match_result field).
- `frontend/lib/api.ts` — the only place fetch() calls to FastAPI live (architecture
  rule 3). Handles the ApiError shape, and resolves a DIFFERENT base URL depending on
  execution context — see "Design decision added in Phase 3" below.
- `app/page.tsx` — dashboard: hero touchless-rate stamp (with the ~8%-is-correct
  caption baked in, not left for someone to rediscover), a ledger stat row, the two
  Recharts panels, a "send a sample invoice" demo panel, and a preview of the 6 most
  recent audit rows linking to the full trail.
- `app/audit/page.tsx` — full audit trail: server component reading `searchParams`
  for decision/invoice_id/offset, `FilterBar`/`Pagination` client components push
  filter and page changes into the URL (so the page is linkable/shareable, not just
  client state).
- `components/` — StampBadge, HeroMetric, LedgerStats, DecisionsOverTimeChart (stacked
  bar), ExceptionBreakdownChart (horizontal bar), AuditLogTable (expandable rows,
  parses match_result), ReplayPanel (POSTs to /ingest directly), FilterBar, Pagination,
  StatusPanel (error/empty states), NavLinks. Each with its own CSS Module.
- Finalized `frontend/Dockerfile`: real production build (`next build` + `next start`),
  not the Phase 1 dev-server placeholder — there's no source volume mount for frontend
  in docker-compose (unlike backend), so a live-reload dev server would gain nothing.
- Finalized `docker-compose.yml`'s frontend service and `.env.example`'s frontend
  section (see design decision below) and `README.md`'s full Setup section.

Design decision added in Phase 3 (not anticipated by the original spec, but required
for the pipeline to actually run in Docker):
- **Two different API base URLs, not one.** `NEXT_PUBLIC_API_URL` is inlined into the
  BROWSER bundle at Next.js build time (Next's own behavior for `NEXT_PUBLIC_*` vars) —
  it has to be the host-mapped port (`http://localhost:8000`) since the browser is
  outside docker's network. But the dashboard and audit pages are server components
  that fetch on the frontend CONTAINER itself before sending HTML down — "localhost"
  there means the frontend container, not the backend. Added `API_INTERNAL_URL=http://
  backend:8000`, read only server-side (`typeof window === "undefined"` branch in
  `lib/api.ts`), for that path. `frontend/Dockerfile` takes `NEXT_PUBLIC_API_URL` as a
  build ARG (not just a runtime env var) for this reason — changing it after
  `docker compose build` needs a rebuild, documented in both `.env.example` and
  `README.md`.

Verified:
- `npx tsc --noEmit` — clean, no type errors.
- `npx next lint` — clean, no warnings.
- `npm run build` — compiles successfully, generates both routes (`/` dynamic,
  `/audit` dynamic), when Google Fonts are reachable. In this build sandbox
  fonts.googleapis.com was network-blocked, so this was confirmed by temporarily
  swapping `app/layout.tsx` to system fonts, building clean, then restoring the real
  Google Fonts version unchanged — not by weakening the actual deliverable. A normal
  `docker build` with internet access will fetch these directly; flagging it here so
  it isn't mistaken for a bug if a similarly restricted environment builds this image.
- The frontend's error states (`ErrorPanel` in both `app/page.tsx` and
  `app/audit/page.tsx`) were exercised by running `next dev` against a deliberately
  dead backend URL and curling both routes: both rendered "Couldn't load this data" /
  "Could not reach the backend at ..." cleanly, no unhandled exceptions.

## Known gaps / notes for whoever picks this up next
- The `mock_dataset.json` invoice records carry a `_scenario` field (e.g. "clean_match",
  "duplicate") purely for generator self-reporting/debugging — Phase 2's ingest logic
  should ignore/strip it rather than treat it as a real invoice field, since it won't
  exist on real OCR'd invoices.
- The "duplicate" scenario in the generator falls back to a clean match if a vendor
  hasn't had a prior invoice yet in the shuffle order (can't duplicate what doesn't
  exist) — actual duplicate count could theoretically be a hair below 10% in rare seed
  configurations, though with seed 42 and 200 invoices it landed exactly on 20/20.
- backend/Dockerfile installs tesseract-ocr and poppler-utils at build time so Phase 2
  doesn't need an image rebuild just to get OCR working — worth mentioning if asked
  about container size trade-offs.
- No Alembic, no auth, no persistent Chroma volume plumbing yet — all deliberate demo
  simplifications, not oversights.

## Phase 4 — Integration & Smoke Test: DONE (core build partially verified)
Started in a sandbox with no Docker daemon, so the stack was run natively
instead (local Postgres 16, backend venv with the exact requirements.txt,
Tesseract/poppler installed) — same application code, no shortcuts on logic.
Reached and fixed two real, reproduced bugs before running out of environment
(no real `OLLAMA_API_KEY`, no egress to install/verify HuggingFace model
downloads for Chroma). **Read `HANDOVER.md` at the repo root before
continuing — it has the full priority-ordered remaining checklist.**

Fixed and confirmed:
- **`backend/app/db/seed.py`** — startup crashed every time with
  `ForeignKeyViolation` on `purchase_orders.vendor_id`. Reproduced in
  isolation: SQLAlchemy 2.0's `insertmanyvalues` batching doesn't reliably
  respect cross-table FK order when Vendor/PurchaseOrder/Receipt inserts are
  all queued into a single flush with explicit PKs. Fixed by adding
  `db.flush()` between each entity type's insert loop, still one transaction/
  one final commit. Confirmed clean boot + correct seed counts (20 vendors /
  180 POs / 180 receipts) against a real Postgres.
- **`backend/app/services/llm_service.py`** — `POST /ingest` without
  `OLLAMA_API_KEY` set raised an unhandled `httpx.HTTPStatusError`, returning
  a raw 500 instead of the clean 502 `API_CONTRACT.md` already documents.
  Fixed: fails fast with a clear 502 message if the key is unset, and wraps
  the real Ollama call so HTTP errors / connection errors / malformed
  responses all become clean 502s. Confirmed: `curl -X POST /ingest` with no
  key now returns `502 {"detail": "OLLAMA_API_KEY is not configured..."}`.

Not yet verified (needs Docker and/or a real OLLAMA_API_KEY + network access
this sandbox didn't have — full detail and suspected root causes in
HANDOVER.md):
- A real Ollama Cloud round-trip (extraction + explanation) — never
  confirmed against the live API's actual response shape.
- `vector_store.py`'s Chroma retrieval — suspected bug: the default Chroma
  embedding function downloads a model from HuggingFace on first use, which
  may hang/fail without container network access to huggingface.co; never
  reached this code path since extraction failed first without a working key.
- The other 5 decision paths through a live `/ingest` (amount mismatch,
  quantity mismatch, no matching PO, closed PO, duplicate/fraud_flag).
- The n8n workflow import against a real `n8nio/n8n:latest` container.
- The frontend's real `next build` against live Google Fonts (Phase 3 only
  verified this by temporarily swapping to system fonts, then reverting —
  the real font-fetch build has never actually succeeded).
- The frontend's happy path against a live backend (dashboard/audit pages
  with real data, filters, the replay panel).

Verified during the Docker smoke-test attempt:
- Docker Desktop Linux engine became available and `postgres:16-alpine` pulled
  successfully. The full compose command was initially blocked by the final
  n8n image layer (282.5/283.3 MB), so the core services were started as
  `docker compose up --build postgres backend frontend`.
- The frontend production image built successfully in Docker, including the
  real `next/font/google` imports. Next.js reported `Compiled successfully`,
  completed type checking, generated all 5 static pages, and exported the
  image. The Google Fonts concern is therefore not a failure in this Docker
  environment, though the build still depends on external font access.
- The backend image did not reach container startup in this run. Its first
  build spent several minutes resolving/downloading Chroma's large dependency
  graph; a cached retry was still installing packages when the smoke test was
  stopped. Consequently, `/health`, the Postgres seed counts, live Ollama,
  Chroma retrieval, the six live decision paths, n8n, and the frontend happy
  path remain unverified here.

Final Phase 4 status: **No** — a clean `docker compose up --build` plus the
documented setup was not proven fully end-to-end in this environment. The
remaining work needs a successful backend dependency/image build (the run was
blocked by slow PyPI downloads while installing Chroma dependencies), then a
live backend/Postgres smoke test and a real `OLLAMA_API_KEY`. The n8n image
pull must also complete before its workflow can be imported and exercised.

## Phase 4 (continued) — Static code review, no execution

A later session picked this up without Docker or a working `OLLAMA_API_KEY`
either, and was asked to review the actual code as it stands now (not the
plan) rather than attempt another partial run. This section reports what the
code actually contains today, since it has moved on from what HANDOVER.md's
checklist describes in a few places without PROGRESS.md being updated to
match. **Nothing below was executed — this is a read-through, not a test.**
Treat items marked "unconfirmed" as still genuinely open.

**HANDOVER.md item 2a (real Ollama round-trip) — code is more complete than
the checklist suggests, but still unconfirmed against the live API:**
`llm_service.py` now has retry/backoff on `429` (honoring `Retry-After`),
a semaphore limiting concurrent calls to `ollama_max_concurrency` (Ollama
Cloud rate-limits parallel chats), and every failure mode (missing key,
connection error, non-2xx, unexpected response shape) converts to a clean
`502`/`503` instead of a raw exception. Response parsing reads
`data["message"]["content"]`, matching the documented `/api/chat` shape.
This all reads correctly, but no request has actually been sent to
`https://ollama.com` in any session so far — the true unknown (does the real
response shape match `message.content` exactly) is still open.

**HANDOVER.md item 2b (Chroma retrieval) — likely already resolved, evidence
in this repo, but not re-confirmed:** `vector_store.py` does real work now:
parses `ap_policy.md` by `##` heading, tags each clause with its
`rule_applied` value from a parenthetical, and `get_relevant_clauses()` tries
an exact metadata match before falling back to semantic search. More
importantly: **this delivered repo's `backend/chroma_data/` directory
contains real HNSW index files** (`data_level0.bin`, `header.bin`, etc.) —
meaning the default embedding function's model download and the embed step
already succeeded at least once in some prior environment. HANDOVER.md's
"suspected bug" (HuggingFace download blocked/hangs) may simply not apply
wherever that run happened. Still worth a real `get_relevant_clauses()` call
per rule to eyeball the retrieved text, but the doomsday case HANDOVER.md
worried about looks unlikely to be live.

**HANDOVER.md item 2c (all 6 decision paths) — logic reads correct on paper,
still unconfirmed live:** `policy_engine.py` unchanged from the version
already unit-tested in Phase 1/2; `ingest.py` wires `resolve_vendor_id` →
`check_duplicate` → `find_matching_po_and_receipt` → `policy_engine.evaluate`
→ `explain_decision` → one `db.commit()` correctly, including converting
extracted values through `_to_decimal()` so a `None`/malformed amount can't
crash the request (falls back to `Decimal("0")`, which correctly routes to
an exception rather than a 500). Not re-run against real data this session.

**HANDOVER.md item 2d (n8n workflow) — still genuinely open, not touched:**
The Sticky Note in `invoice_intake_workflow.json` still flags the same
unresolved assumption from Phase 2 — the "Extract From File" node's output
key. No session has actually imported this into a running n8n yet to check.

**HANDOVER.md item 2e (frontend Google Fonts) — the "self-host as a real
fix" suggestion was NOT applied; still a live network dependency:**
`app/layout.tsx` still imports `Fraunces`, `IBM_Plex_Sans`, `IBM_Plex_Mono`
from `next/font/google` directly — fonts are still fetched from
`fonts.googleapis.com`/`fonts.gstatic.com` at `docker build` time, not
self-hosted under `frontend/public/fonts/`. This is not a regression from
what PROGRESS.md already recorded (a prior session's real Docker build did
succeed with live font access), but the portability risk HANDOVER.md flagged
is still exactly as described — no code change addressed it.

**HANDOVER.md item 2f (frontend happy path) — still unconfirmed**, since
this session had no live backend running to test against either.

**One real deviation from the original Phase 2 plan, not a bug but worth
knowing about:** earlier notes describe a malformed-LLM-JSON response
getting a distinct `needs_manual_review` invoice status. The code as it
exists now doesn't do that — `extract_invoice_fields()` silently falls back
to an all-`null` extraction on a JSON parse failure, which then flows
through as a normal `NO_MATCHING_PO` exception (since `po_number` is `None`).
It's a safe fallback (never crashes, never silently auto-approves), just a
quieter failure mode than originally planned — a real parse failure won't be
visibly distinguishable from "the invoice genuinely had no PO number" in the
dashboard's status column, only in `extracted_json`/`raw_ocr_text` on the
detail view.

**New issue not previously flagged: no `.gitignore` exists anywhere in this
repo.** The delivered zip includes a `.env` with a live, real
`OLLAMA_API_KEY` committed in plaintext, plus `backend/chroma_data/`'s
binary index files. Before this repo goes anywhere public (GitHub, a shared
drive), rotate that key and add a `.gitignore` covering at minimum `.env`,
`backend/chroma_data/`, `node_modules/`, `.next/`, `__pycache__/`, and
`frontend/tsconfig.tsbuildinfo`.

**Minor cleanup, not functional:** `backend/Dockerfile`'s final comment still
reads "main.py is a Phase 2 concern (TODO placeholder in Phase 1)" — stale,
since Phase 2 implemented it long ago. Harmless, but worth deleting next time
that file is touched so it doesn't confuse a future reader.

**Honest bottom line, unchanged from the prior entry:** still **no** proof of
a full `docker compose up --build` working end-to-end with a real Ollama key.
The code looks materially more production-shaped than the last written
status implied, but "looks correct on read-through" and "confirmed working"
are different claims — the next session with Docker and a valid
`OLLAMA_API_KEY` should still run HANDOVER.md's checklist for real, focusing
on 2a, 2d, and 2f since 2b and 2c are lower-risk based on this review.

## Known gaps / notes for whoever picks this up next (post-Phase-3)
- All items above (from Phase 1/2) still stand: no Alembic, no auth, no persistent
  Chroma volume, the `_scenario` field on mock invoices is generator-only, and the
  duplicate-scenario count could theoretically dip below 10% on rare seeds.
- Frontend build needs internet access to fetch its Google Fonts at `docker build`
  time. It passed here, but remains a portability risk in network-restricted
  environments.
- The frontend's happy-path (real data from a running backend) hasn't been exercised
  in this session — no Postgres/backend was booted here. Only its error path (backend
  unreachable, see above) and its build/typecheck/lint were verified. Worth a full
  `docker compose up --build` smoke test — dashboard numbers matching `/metrics`,
  audit filters actually filtering, the replay button actually landing a new row —
  before presenting this as a finished demo.
- See `DEMO_CHEATSHEET.md` for the short architecture walkthrough and live-demo
  commands. The repository is not yet cleared for an end-to-end demo until the
  backend and n8n checks above are completed.

## Current delivery status — End-to-end verified (2026-09-17)

The older Phase 4 notes above are a retained historical record from before
Docker and a live Ollama configuration were available. This is the
authoritative current status.

**Final status: Yes** — the documented Docker Compose setup now runs the full
pipeline end-to-end.

Verified in the running stack:

- All four services are healthy: Postgres, backend, frontend, and n8n.
- Seed data is present (20 vendors, 180 POs, 180 receipts), and live ingests
  completed LLM extraction, Chroma policy retrieval, matching, deterministic
  decisioning, explanation generation, and atomic Invoice + AuditLog writes.
- The audit log includes all six expected decision rules. Stored match results
  include confirmed non-zero amount and quantity variances where applicable.
- n8n 2.39 imported and activated the batch-size-one workflow; backend logs
  recorded sequential successful n8n-originated `POST /ingest` calls.
- The production frontend image built and its dashboard, audit, and filtered
  audit routes return live FastAPI data.

Operational hardening added during live verification:

- Prevented Ollama Cloud 429 bursts with sequential n8n processing, an
  outbound-call semaphore, and retry/backoff.
- Prevented SQLAlchemy QueuePool exhaustion with `INGEST_MAX_CONCURRENCY=1`
  around the complete ingest lifecycle; queued requests do not check out a
  database connection.
- Added automatic visible-tab-only refresh to dashboard and audit pages.
- Set n8n to `Asia/Kolkata` and normalized audit timestamp presentation to
  IST (UTC+05:30).
- Added `.gitignore` for `.env`, local Chroma data, Python caches, and frontend
  dependencies/build artifacts.

Current deliberate limitations: no authentication, Alembic migrations,
persistent Chroma volume, async job queue, or idempotent replay/reset flow.
The serial 200-invoice replay takes several minutes in exchange for reliable
Ollama and database usage. If any API key was shared outside its secret store,
the account owner should rotate it and update `.env`.
