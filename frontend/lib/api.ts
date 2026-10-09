import type {
  ApiErrorBody,
  AuditLogResponse,
  IngestRequest,
  IngestResponse,
  InvoiceListResponse,
  Invoice,
  Metrics,
  Decision,
} from "./types";

// Architecture rule: the frontend calls FastAPI ONLY. Never n8n, never Ollama.
//
// Two different base URLs are needed because this runs in two places:
//  - Server components (page.tsx, audit/page.tsx) execute inside the frontend
//    CONTAINER, on the docker-compose network, where the backend is reachable
//    at API_INTERNAL_URL (http://backend:8000) — "localhost" there would mean
//    the frontend container itself.
//  - Client components (ReplayPanel's /ingest call) execute in the person's
//    BROWSER, outside docker's network, where the backend is only reachable
//    via its host-mapped port: NEXT_PUBLIC_API_URL (http://localhost:8000).
// NEXT_PUBLIC_* vars are inlined into the browser bundle at build time, so if
// you deploy this somewhere other than localhost, rebuild the frontend image
// with NEXT_PUBLIC_API_URL set to the backend's public URL.
const API_BASE =
  typeof window === "undefined"
    ? process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
    : process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
      // Dashboard data changes as invoices are ingested — never serve a stale cache.
      cache: "no-store",
    });
  } catch {
    throw new ApiError(0, `Could not reach the backend at ${API_BASE}. Is it running?`);
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as ApiErrorBody;
      if (body?.detail) detail = body.detail;
    } catch {
      // response wasn't JSON — fall back to statusText
    }
    throw new ApiError(res.status, detail);
  }

  return (await res.json()) as T;
}

export function getMetrics(): Promise<Metrics> {
  return request<Metrics>("/metrics");
}

export interface InvoiceQuery {
  status?: Decision;
  vendor_id?: number;
  limit?: number;
  offset?: number;
}

export function getInvoices(query: InvoiceQuery = {}): Promise<InvoiceListResponse> {
  const params = new URLSearchParams();
  if (query.status) params.set("status", query.status);
  if (query.vendor_id !== undefined) params.set("vendor_id", String(query.vendor_id));
  params.set("limit", String(query.limit ?? 50));
  params.set("offset", String(query.offset ?? 0));
  return request<InvoiceListResponse>(`/invoices?${params.toString()}`);
}

export function getInvoice(id: number): Promise<Invoice> {
  return request<Invoice>(`/invoices/${id}`);
}

export interface AuditLogQuery {
  invoice_id?: number;
  decision?: Decision;
  limit?: number;
  offset?: number;
}

export function getAuditLog(query: AuditLogQuery = {}): Promise<AuditLogResponse> {
  const params = new URLSearchParams();
  if (query.invoice_id !== undefined) params.set("invoice_id", String(query.invoice_id));
  if (query.decision) params.set("decision", query.decision);
  params.set("limit", String(query.limit ?? 50));
  params.set("offset", String(query.offset ?? 0));
  return request<AuditLogResponse>(`/audit-log?${params.toString()}`);
}

/** Used by the "replay a sample invoice" demo button — POSTs straight to /ingest,
 *  exactly like the n8n workflow does, so the demo doesn't depend on n8n running. */
export function ingestInvoice(payload: IngestRequest): Promise<IngestResponse> {
  return request<IngestResponse>("/ingest", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
