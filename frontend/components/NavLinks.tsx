"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import styles from "../app/layout.module.css";

const LINKS = [
  { href: "/", label: "Dashboard" },
  { href: "/audit", label: "Audit trail" },
];

export default function NavLinks() {
  const pathname = usePathname();
  return (
    <nav className={styles.nav}>
      {LINKS.map((link) => (
        <Link key={link.href} href={link.href} data-active={pathname === link.href}>
          {link.label}
        </Link>
      ))}
    </nav>
  );
}
