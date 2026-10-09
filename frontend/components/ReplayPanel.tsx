"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApiError, ingestInvoice } from "../lib/api";
import { SAMPLE_INVOICES } from "../lib/sample-invoices";
import type { IngestResponse } from "../lib/types";
import InlineMarkdown from "./InlineMarkdown";
import StampBadge from "./StampBadge";
import styles from "./ReplayPanel.module.css";

export default function ReplayPanel() {
  const router = useRouter();
  const [selected, setSelected] = useState(0);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<IngestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const sample = SAMPLE_INVOICES[selected];
      const invoiceNumber = `INV-DEMO-${Date.now()}`;
      const rawText = sample.raw_text.replace(
        /Invoice Number: [^\n]+/,
        `Invoice Number: ${invoiceNumber}`,
      );
      const response = await ingestInvoice({ raw_text: rawText });
      setResult(response);
      router.refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong sending this invoice.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={styles.panel}>
      <p className={styles.title}>Send a sample invoice</p>
      <p className={styles.caption}>
        POSTs directly to <code>/ingest</code> — the same endpoint the n8n workflow calls — so
        you can see the pipeline decide in real time without n8n running.
      </p>
      <div className={styles.options} role="radiogroup" aria-label="Sample invoice">
        {SAMPLE_INVOICES.map((sample, i) => (
          <div
            key={sample.label}
            className={styles.option}
            data-selected={selected === i}
            role="radio"
            aria-checked={selected === i}
            tabIndex={0}
            onClick={() => setSelected(i)}
            onKeyDown={(e) => e.key === "Enter" && setSelected(i)}
          >
            <input
              type="radio"
              checked={selected === i}
              onChange={() => setSelected(i)}
              style={{ marginTop: 3 }}
            />
            <span>
              <span className={styles.optionLabel}>{sample.label}</span>
              <span className={styles.optionDescription}>{sample.description}</span>
            </span>
          </div>
        ))}
      </div>
      <button className={styles.submit} onClick={handleSubmit} disabled={loading}>
        {loading ? "Sending\u2026" : "Send invoice"}
      </button>

      {error && (
        <div className={styles.result}>
          <p className={styles.resultExplanation}>{error}</p>
        </div>
      )}

      {result && (
        <div className={styles.result}>
          <div className={styles.resultHeader}>
            <StampBadge decision={result.decision.decision} />
            <span className={styles.resultRule}>{result.decision.rule_applied}</span>
          </div>
          <p className={styles.resultExplanation}>
            <InlineMarkdown text={result.explanation} />
          </p>
        </div>
      )}
    </div>
  );
}
