import { ApiError, getAuditLog } from "../../lib/api";
import type { Decision } from "../../lib/types";
import AuditLogTable from "../../components/AuditLogTable";
import FilterBar from "../../components/FilterBar";
import LiveDataRefresh from "../../components/LiveDataRefresh";
import Pagination from "../../components/Pagination";
import { ErrorPanel } from "../../components/StatusPanel";

const VALID_DECISIONS: Decision[] = ["auto_approved", "exception", "fraud_flag"];

export default async function AuditPage({
  searchParams,
}: {
  searchParams: { decision?: string; invoice_id?: string; offset?: string };
}) {
  const decision = VALID_DECISIONS.includes(searchParams.decision as Decision)
    ? (searchParams.decision as Decision)
    : undefined;
  const invoiceId = searchParams.invoice_id ? Number(searchParams.invoice_id) : undefined;
  const offset = searchParams.offset ? Number(searchParams.offset) : 0;
  const limit = 25;

  try {
    const auditLog = await getAuditLog({
      decision,
      invoice_id: invoiceId,
      offset,
      limit,
    });

    return (
      <main className="shell">
        <LiveDataRefresh />
        <div className="section" style={{ borderBottom: "none" }}>
          <p className="eyebrow">Full decision trail</p>
          <h1 className="section-title" style={{ fontSize: 28 }}>
            Audit trail
          </h1>
          <FilterBar />
          <AuditLogTable entries={auditLog.items} />
          <Pagination total={auditLog.total} limit={auditLog.limit} offset={auditLog.offset} />
        </div>
      </main>
    );
  } catch (err) {
    return (
      <main className="shell">
        <LiveDataRefresh />
        <div className="section" style={{ borderBottom: "none" }}>
          <ErrorPanel
            message={err instanceof ApiError ? err.message : "Unexpected error loading the audit trail."}
          />
        </div>
      </main>
    );
  }
}
