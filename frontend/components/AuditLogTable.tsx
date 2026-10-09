"use client";

import { Fragment, useState } from "react";
import type { AuditLogEntry } from "../lib/types";
import { parseMatchResult } from "../lib/types";
import InlineMarkdown, { stripInlineMarkdown } from "./InlineMarkdown";
import StampBadge from "./StampBadge";
import styles from "./AuditLogTable.module.css";

function formatDate(iso: string): string {
  // PostgreSQL returns naive timestamps. They represent UTC in this demo, so
  // make that explicit before converting them for the UI; otherwise browsers
  // interpret the value in their own local timezone.
  const utcIso = /(?:Z|[+-]\d{2}:?\d{2})$/.test(iso) ? iso : `${iso}Z`;
  const d = new Date(utcIso);
  return d.toLocaleString("en-IN", {
    timeZone: "Asia/Kolkata",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "short",
  });
}

function DetailRow({ entry }: { entry: AuditLogEntry }) {
  const match = parseMatchResult(entry.match_result);
  return (
    <tr className={styles.detailRow}>
      <td colSpan={6}>
        <dl className={styles.detailGrid}>
          <div>
            <dt>Rule applied</dt>
            <dd>{entry.policy_rule_applied}</dd>
          </div>
          <div>
            <dt>Invoice</dt>
            <dd>#{entry.invoice_id}</dd>
          </div>
          <div>
            <dt>Matched PO</dt>
            <dd>{match?.po ? `${match.po.po_number} (${match.po.status})` : "none"}</dd>
          </div>
          <div>
            <dt>Amount variance</dt>
            <dd>
              {match?.amount_variance_pct !== null && match?.amount_variance_pct !== undefined
                ? `${(Number(match.amount_variance_pct) * 100).toFixed(1)}%`
                : "n/a"}
            </dd>
          </div>
          <div>
            <dt>Matched receipt</dt>
            <dd>{match?.receipt ? `qty ${match.receipt.quantity_received}` : "none"}</dd>
          </div>
          <div>
            <dt>Quantity variance</dt>
            <dd>
              {match?.quantity_variance_pct !== null && match?.quantity_variance_pct !== undefined
                ? `${(Number(match.quantity_variance_pct) * 100).toFixed(1)}%`
                : "n/a"}
            </dd>
          </div>
        </dl>
        <p className={styles.explanationFull}>
          <InlineMarkdown text={entry.llm_explanation} />
        </p>
      </td>
    </tr>
  );
}

export default function AuditLogTable({ entries }: { entries: AuditLogEntry[] }) {
  const [openId, setOpenId] = useState<number | null>(null);

  if (entries.length === 0) {
    return <div className={styles.empty}>No audit rows match these filters yet.</div>;
  }

  return (
    <table className={styles.table}>
      <thead>
        <tr>
          <th aria-hidden="true"></th>
          <th>Invoice</th>
          <th>Decision</th>
          <th>Rule applied</th>
          <th>Explanation</th>
          <th>Logged</th>
        </tr>
      </thead>
      <tbody>
        {entries.map((entry) => {
          const isOpen = openId === entry.id;
          const preview = stripInlineMarkdown(entry.llm_explanation);
          return (
            <Fragment key={entry.id}>
              <tr
                className={styles.row}
                onClick={() => setOpenId(isOpen ? null : entry.id)}
                aria-expanded={isOpen}
              >
                <td className={styles.chevron}>{isOpen ? "\u2212" : "+"}</td>
                <td className="mono">#{entry.invoice_id}</td>
                <td>
                  <StampBadge decision={entry.decision} />
                </td>
                <td className="mono">{entry.policy_rule_applied}</td>
                <td className={styles.explanation}>
                  {preview.length > 90
                    ? `${preview.slice(0, 90)}\u2026`
                    : <InlineMarkdown text={entry.llm_explanation} />}
                </td>
                <td className="mono">{formatDate(entry.created_at)}</td>
              </tr>
              {isOpen && <DetailRow entry={entry} />}
            </Fragment>
          );
        })}
      </tbody>
    </table>
  );
}
