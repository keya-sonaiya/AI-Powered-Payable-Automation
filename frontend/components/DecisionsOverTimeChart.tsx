"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DecisionsOverTimePoint } from "../lib/types";
import styles from "./ChartPanel.module.css";

const COLORS = {
  auto_approved: "#2f6f4e",
  exception: "#93650f",
  fraud_flag: "#8f3636",
};

function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ dataKey: string; value: number }>;
  label?: string;
}) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className={styles.tooltip}>
      <div style={{ marginBottom: 6, color: "var(--ink-soft)" }}>{label}</div>
      {payload.map((entry) => (
        <div className={styles.tooltipRow} key={entry.dataKey}>
          <span>{entry.dataKey.replace("_", " ")}</span>
          <span>{entry.value}</span>
        </div>
      ))}
    </div>
  );
}

export default function DecisionsOverTimeChart({ data }: { data: DecisionsOverTimePoint[] }) {
  return (
    <div className={styles.panel}>
      <p className={styles.title}>Decisions over time</p>
      <div className={styles.legend}>
        <span className={styles.legendItem}>
          <i className={styles.swatch} style={{ background: COLORS.auto_approved }} />
          Approved
        </span>
        <span className={styles.legendItem}>
          <i className={styles.swatch} style={{ background: COLORS.exception }} />
          Exception
        </span>
        <span className={styles.legendItem}>
          <i className={styles.swatch} style={{ background: COLORS.fraud_flag }} />
          Flagged
        </span>
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
          <CartesianGrid stroke="var(--rule)" vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 12, fill: "var(--ink-faint)" }}
            axisLine={{ stroke: "var(--rule-strong)" }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 12, fill: "var(--ink-faint)" }}
            axisLine={false}
            tickLine={false}
            allowDecimals={false}
          />
          <Tooltip content={<ChartTooltip />} cursor={{ fill: "var(--paper-sunken)" }} />
          <Bar dataKey="auto_approved" stackId="d" fill={COLORS.auto_approved} />
          <Bar dataKey="exception" stackId="d" fill={COLORS.exception} />
          <Bar dataKey="fraud_flag" stackId="d" fill={COLORS.fraud_flag} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
