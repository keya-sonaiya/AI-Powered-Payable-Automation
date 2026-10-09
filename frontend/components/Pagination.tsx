"use client";

import { useRouter, useSearchParams } from "next/navigation";
import styles from "./Pagination.module.css";

export default function Pagination({
  total,
  limit,
  offset,
}: {
  total: number;
  limit: number;
  offset: number;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();

  function goTo(nextOffset: number) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("offset", String(nextOffset));
    router.push(`/audit?${params.toString()}`);
  }

  const start = total === 0 ? 0 : offset + 1;
  const end = Math.min(offset + limit, total);

  return (
    <div className={styles.bar}>
      <span>
        {start}&ndash;{end} of {total}
      </span>
      <div className={styles.controls}>
        <button
          className={styles.button}
          onClick={() => goTo(Math.max(0, offset - limit))}
          disabled={offset === 0}
        >
          Previous
        </button>
        <button
          className={styles.button}
          onClick={() => goTo(offset + limit)}
          disabled={offset + limit >= total}
        >
          Next
        </button>
      </div>
    </div>
  );
}
