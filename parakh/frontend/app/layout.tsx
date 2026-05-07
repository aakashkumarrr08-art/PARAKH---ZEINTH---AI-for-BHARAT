import { ReactNode } from "react";
import Link from "next/link";
import { IBM_Plex_Sans, Source_Serif_4 } from "next/font/google";

import "../styles/globals.css";

const sans = IBM_Plex_Sans({ subsets: ["latin"], weight: ["400", "500", "600", "700"], variable: "--font-sans" });
const serif = Source_Serif_4({ subsets: ["latin"], weight: ["600", "700"], variable: "--font-serif" });

export const metadata = {
  title: "PARAKH",
  description: "Procurement Audit-Ready Assessment & Knowledge Harnessing"
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className={`${sans.variable} ${serif.variable} app-shell font-[var(--font-sans)]`}>
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <header className="panel mb-6 overflow-hidden">
            <div className="bg-mesh p-6 sm:flex sm:items-center sm:justify-between">
              <div>
                <p className="section-title">Transparent Tender Review</p>
                <Link href="/" className="mt-2 block font-[var(--font-serif)] text-3xl text-slate-950">
                  PARAKH
                </Link>
                <p className="mt-2 max-w-2xl text-sm text-slate-700">
                  Deterministic eligibility checks, officer-led decisions, and an audit trail built to survive scrutiny.
                </p>
              </div>
              <nav className="mt-4 flex flex-wrap gap-2 sm:mt-0">
                <Link href="/" className="button-secondary">
                  Dashboard
                </Link>
                <Link href="/tenders" className="button-secondary">
                  Tenders
                </Link>
                <Link href="/bidders" className="button-secondary">
                  Bidder Hub
                </Link>
              </nav>
            </div>
          </header>
          <main>{children}</main>
        </div>
      </body>
    </html>
  );
}
