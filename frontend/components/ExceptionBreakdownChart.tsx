"use client";

import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import styles from "./ChartPanel.module.css";

const ROWS = [
  { key: "approved", label: "Approved", color: "#2f6f4e" },
  { key: "exception", label: "Exception", color: "#93650f" },
  { key: "fraud", label: "Flagged", color: "#8f3636" },
] as const;

function ChartTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: { label: string; count: number } }>;
}) {
  if (!active || !payload || payload.length === 0) return null;
  const { label, count } = payload[0].payload;
  return (
    <div className={styles.tooltip}>
      <div className={styles.tooltipRow}>
        <span>{label}</span>
        <span>{count}</span>
      </div>
    </div>
  );
}

export default function ExceptionBreakdownChart({
  approvedCount,
  exceptionCount,
  fraudCount,
}: {
  approvedCount: number;
  exceptionCount: number;
  fraudCount: number;
}) {
  const data = [
    { key: "approved", label: "Approved", count: approvedCount },
    { key: "exception", label: "Exception", count: exceptionCount },
    { key: "fraud", label: "Flagged", count: fraudCount },
  ];

  return (
    <div className={styles.panel}>
      <p className={styles.title}>Decision breakdown</p>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 4, right: 24, left: 8, bottom: 0 }}
        >
          <CartesianGrid stroke="var(--rule)" horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 12, fill: "var(--ink-faint)" }} axisLine={false} tickLine={false} allowDecimals={false} />
          <YAxis
            type="category"
            dataKey="label"
            tick={{ fontSize: 13, fill: "var(--ink)" }}
            axisLine={false}
            tickLine={false}
            width={80}
          />
          <Tooltip content={<ChartTooltip />} cursor={{ fill: "var(--paper-sunken)" }} />
          <Bar dataKey="count" radius={[0, 2, 2, 0]} barSize={28}>
            {data.map((entry) => (
              <Cell key={entry.key} fill={ROWS.find((r) => r.key === entry.key)!.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
