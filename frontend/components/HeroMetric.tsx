import styles from "./HeroMetric.module.css";

export default function HeroMetric({
  ratePct,
  approvedCount,
  totalCount,
}: {
  ratePct: number;
  approvedCount: number;
  totalCount: number;
}) {
  return (
    <div className={styles.hero}>
      <div className={`${styles.number} mono`}>
        {ratePct.toFixed(1)}
        <sup>%</sup>
      </div>
      <div className={styles.copy}>
        <p className={styles.headline}>Touchless rate</p>
        <p className={styles.caption}>
          {approvedCount} of {totalCount} invoices cleared the policy engine with no human
          review. The rate reads low by design here — most clean matches in this dataset still
          exceed the $5,000 auto-approval ceiling, so they correctly route to exception even at
          0% variance.
        </p>
      </div>
    </div>
  );
}
