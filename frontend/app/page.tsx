import Link from "next/link";
import { ApiError, getAuditLog, getMetrics } from "../lib/api";
import HeroMetric from "../components/HeroMetric";
import LedgerStats from "../components/LedgerStats";
import DecisionsOverTimeChart from "../components/DecisionsOverTimeChart";
import ExceptionBreakdownChart from "../components/ExceptionBreakdownChart";
import AuditLogTable from "../components/AuditLogTable";
import LiveDataRefresh from "../components/LiveDataRefresh";
import ReplayPanel from "../components/ReplayPanel";
import { ErrorPanel, EmptyPanel } from "../components/StatusPanel";
import styles from "./page.module.css";

export default async function DashboardPage() {
  try {
    const [metrics, recentAudit] = await Promise.all([
      getMetrics(),
      getAuditLog({ limit: 6 }),
    ]);

    if (metrics.total_invoices === 0) {
      return (
        <main className="shell">
          <LiveDataRefresh />
          <div className="section" style={{ borderBottom: "none" }}>
            <p className="eyebrow">AP Agent Demo</p>
            <h1 className="section-title" style={{ fontSize: 28 }}>
              No invoices yet
            </h1>
            <EmptyPanel
              title="The ledger is empty"
              body="Run the mock data generator and either start the n8n intake workflow or send a sample invoice below to see decisions appear."
            />
            <div style={{ marginTop: 24 }}>
              <ReplayPanel />
            </div>
          </div>
        </main>
      );
    }

    return (
      <main className="shell">
        <LiveDataRefresh />
        <section className="section">
          <p className="eyebrow">Payables agent — {metrics.total_invoices} invoices processed</p>
          <HeroMetric
            ratePct={metrics.touchless_rate_pct}
            approvedCount={metrics.auto_approved_count}
            totalCount={metrics.total_invoices}
          />
          <LedgerStats
            entries={[
              { label: "Total invoices", value: metrics.total_invoices },
              { label: "Auto-approved", value: metrics.auto_approved_count, tone: "approve" },
              { label: "Exceptions", value: metrics.exception_count, tone: "exception" },
              { label: "Fraud flags", value: metrics.fraud_flag_count, tone: "fraud" },
              {
                label: "Avg. cycle time",
                value: `${metrics.avg_cycle_time_seconds.toFixed(3)}s`,
              },
            ]}
          />
        </section>

        <section className="section">
          <div className="two-col">
            <DecisionsOverTimeChart data={metrics.decisions_over_time} />
            <ExceptionBreakdownChart
              approvedCount={metrics.auto_approved_count}
              exceptionCount={metrics.exception_count}
              fraudCount={metrics.fraud_flag_count}
            />
          </div>
        </section>

        <section className="section">
          <p className="eyebrow">Try the pipeline</p>
          <h2 className="section-title">Send a sample invoice</h2>
          <ReplayPanel />
        </section>

        <section className="section">
          <div className={styles.viewAllRow}>
            <div>
              <p className="eyebrow">Latest activity</p>
              <h2 className="section-title" style={{ marginBottom: 0 }}>
                Audit trail
              </h2>
            </div>
            <Link className={styles.viewAll} href="/audit">
              View full audit trail &rarr;
            </Link>
          </div>
          <AuditLogTable entries={recentAudit.items} />
        </section>
      </main>
    );
  } catch (err) {
    return (
      <main className="shell">
        <LiveDataRefresh />
        <div className="section" style={{ borderBottom: "none" }}>
          <ErrorPanel
            message={err instanceof ApiError ? err.message : "Unexpected error loading the dashboard."}
          />
        </div>
      </main>
    );
  }
}
