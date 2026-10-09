// Mirrors API_CONTRACT.md exactly. This file is the single place the
// frontend's understanding of the backend's shapes lives — if the contract
// changes, update here first and let TypeScript find every call site.

export type Decision = "auto_approved" | "exception" | "fraud_flag";

export type RuleApplied =
  | "WITHIN_TOLERANCE_AND_THRESHOLD"
  | "AMOUNT_VARIANCE_OR_THRESHOLD_EXCEEDED"
  | "QUANTITY_VARIANCE_EXCEEDS_GUARDRAIL"
  | "NO_MATCHING_PO"
  | "PO_CLOSED"
  | "DUPLICATE_INVOICE_NUMBER"
  | "PO_AMOUNT_INVALID";

export interface Invoice {
  id: number;
  invoice_number: string;
  vendor_id: number | null;
  po_number: string | null;
  amount: number;
  quantity: number | null;
  unit_price: number | null;
  status: Decision;
  created_at: string;
}

export interface InvoiceListResponse {
  total: number;
  limit: number;
  offset: number;
  items: Invoice[];
}

export interface AuditLogEntry {
  id: number;
  invoice_id: number;
  match_result: string; // JSON string — parse with parseMatchResult()
  policy_rule_applied: RuleApplied;
  llm_explanation: string;
  decision: Decision;
  created_at: string;
}

export interface AuditLogResponse {
  total: number;
  limit: number;
  offset: number;
  items: AuditLogEntry[];
}

export interface MatchResult {
  po: {
    id: number;
    po_number: string;
    vendor_id: number;
    amount: string;
    quantity: string;
    unit_price: string;
    status: string;
  } | null;
  receipt: {
    id: number;
    po_id: number;
    quantity_received: string;
    received_date: string;
  } | null;
  amount_variance_pct: string | null;
  quantity_variance_pct: string | null;
}

export interface DecisionsOverTimePoint {
  date: string;
  auto_approved: number;
  exception: number;
  fraud_flag: number;
}

export interface Metrics {
  total_invoices: number;
  touchless_rate_pct: number;
  auto_approved_count: number;
  exception_count: number;
  fraud_flag_count: number;
  avg_cycle_time_seconds: number;
  decisions_over_time: DecisionsOverTimePoint[];
}

export interface IngestRequest {
  raw_text?: string | null;
  file_path?: string | null;
}

export interface IngestResponse {
  invoice_id: number;
  vendor_id: number | null;
  extracted: {
    invoice_number: string;
    vendor_name: string;
    po_number: string | null;
    amount: number;
    quantity: number | null;
    unit_price: number | null;
    invoice_date: string | null;
  };
  decision: {
    decision: Decision;
    rule_applied: RuleApplied;
    amount_variance_pct: number | null;
    quantity_variance_pct: number | null;
  };
  explanation: string;
}

export interface ApiErrorBody {
  detail: string;
}

/** Parses AuditLogEntry.match_result, which the API stores/returns as a JSON string. */
export function parseMatchResult(raw: string): MatchResult | null {
  try {
    return JSON.parse(raw) as MatchResult;
  } catch {
    return null;
  }
}
