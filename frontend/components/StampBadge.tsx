import type { Decision } from "../lib/types";
import styles from "./StampBadge.module.css";

const LABEL: Record<Decision, string> = {
  auto_approved: "Approved",
  exception: "Exception",
  fraud_flag: "Flagged",
};

const CLASS: Record<Decision, string> = {
  auto_approved: styles.approved,
  exception: styles.exception,
  fraud_flag: styles.fraud,
};

export default function StampBadge({
  decision,
  large = false,
}: {
  decision: Decision;
  large?: boolean;
}) {
  return (
    <span className={`${styles.stamp} ${CLASS[decision]} ${large ? styles.large : ""}`}>
      {LABEL[decision]}
    </span>
  );
}
