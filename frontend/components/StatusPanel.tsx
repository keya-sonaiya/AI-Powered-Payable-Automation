import styles from "./StatusPanel.module.css";

export function ErrorPanel({ message }: { message: string }) {
  return (
    <div className={styles.panel} data-tone="error">
      <p className={styles.title}>Couldn&rsquo;t load this data</p>
      <p className={`${styles.body} ${styles.mono}`}>{message}</p>
      <p className={styles.body} style={{ marginTop: 10 }}>
        Check that the backend is running and NEXT_PUBLIC_API_URL points at it, then reload.
      </p>
    </div>
  );
}

export function EmptyPanel({ title, body }: { title: string; body: string }) {
  return (
    <div className={styles.panel}>
      <p className={styles.title}>{title}</p>
      <p className={styles.body}>{body}</p>
    </div>
  );
}
