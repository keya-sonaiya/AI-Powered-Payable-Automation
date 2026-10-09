"use client";

import { useRouter, useSearchParams } from "next/navigation";
import styles from "./FilterBar.module.css";

export default function FilterBar() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const decision = searchParams.get("decision") || "";
  const invoiceId = searchParams.get("invoice_id") || "";

  function updateParam(key: string, value: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (value) {
      params.set(key, value);
    } else {
      params.delete(key);
    }
    params.delete("offset"); // any filter change resets pagination
    router.push(`/audit?${params.toString()}`);
  }

  const hasFilters = Boolean(decision || invoiceId);

  return (
    <div className={styles.bar}>
      <div className={styles.field}>
        <label htmlFor="decision-filter">Decision</label>
        <select
          id="decision-filter"
          value={decision}
          onChange={(e) => updateParam("decision", e.target.value)}
        >
          <option value="">All</option>
          <option value="auto_approved">Approved</option>
          <option value="exception">Exception</option>
          <option value="fraud_flag">Flagged</option>
        </select>
      </div>
      <div className={styles.field}>
        <label htmlFor="invoice-filter">Invoice ID</label>
        <input
          id="invoice-filter"
          type="number"
          placeholder="e.g. 201"
          defaultValue={invoiceId}
          onBlur={(e) => updateParam("invoice_id", e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && updateParam("invoice_id", e.currentTarget.value)}
        />
      </div>
      {hasFilters && (
        <button className={styles.clear} onClick={() => router.push("/audit")}>
          Clear filters
        </button>
      )}
    </div>
  );
}
