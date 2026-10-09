import styles from "./LedgerStats.module.css";

interface Entry {
  label: string;
  value: string | number;
  tone?: "approve" | "exception" | "fraud";
}

export default function LedgerStats({ entries }: { entries: Entry[] }) {
  return (
    <div className={styles.row}>
      {entries.map((entry) => (
        <div className={styles.entry} key={entry.label}>
          <p className={styles.label}>{entry.label}</p>
          <div className={styles.value} data-tone={entry.tone}>
            {entry.value}
          </div>
        </div>
      ))}
    </div>
  );
}
