import type { Metadata } from "next";
import { IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import NavLinks from "../components/NavLinks";
import styles from "./layout.module.css";
import "./globals.css";

const plexSans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex-sans",
});

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-plex-mono",
});

export const metadata: Metadata = {
  title: "AP Agent — Console",
  description: "Live monitoring console for invoice intake, matching, and audit trail.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${plexSans.variable} ${plexMono.variable}`}>
      <body>
        <div className={styles.appShell}>
          <aside className={styles.sidebar}>
            <div className={styles.brand}>
              <span className={styles.brandDot} />
              AP Agent
            </div>
            <NavLinks />
            <p className={styles.sidebarNote}>
              Decisions are made by a deterministic policy engine. The model only
              extracts fields and writes the plain-English explanation.
            </p>
          </aside>
          <div className={styles.main}>{children}</div>
        </div>
      </body>
    </html>
  );
}