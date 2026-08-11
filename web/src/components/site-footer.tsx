import Link from "next/link";
import type { ReactNode } from "react";

import { ArrowUpRightIcon, GitHubIcon } from "@/components/icons";
import { DATA_LINKS, GITHUB_URL, MODEL_CARD_URL, NAV_LINKS, RELEASE_NOTES_URL } from "@/lib/site-config";
import { formatDateTime } from "@/lib/format";

export default function SiteFooter({
  commit,
  generatedAt,
}: {
  commit: string;
  generatedAt: string;
}) {
  return (
    <footer className="relative mt-24 border-t border-white/10 bg-black/70">
      <div className="site-container grid gap-12 py-12 lg:grid-cols-[1.2fr_1fr_1fr_1fr]">
        <div>
          <div className="flex items-center gap-3">
            <span className="brand-mark" aria-hidden="true"><span className="brand-mark-core" /></span>
            <span className="text-lg font-semibold tracking-[0.22em]">SALARIUM</span>
          </div>
          <p className="mt-5 max-w-sm text-sm leading-6 text-white/40">
            Open-source systematic equity research: governed data, out-of-sample rankings, concentrated portfolio construction, and auditable risk decisions.
          </p>
          <p className="mt-4 text-xs leading-5 text-white/25">Research only. Not investment advice. No live order execution.</p>
        </div>

        <FooterGroup title="Explore">
          {NAV_LINKS.map((link) => <Link key={link.href} href={link.href} className="footer-link">{link.label}</Link>)}
          <Link href="/disclosures" className="footer-link">Disclosures</Link>
        </FooterGroup>

        <FooterGroup title="Evidence">
          {DATA_LINKS.map((link) => (
            <a key={link.href} href={link.href} className="footer-link" target="_blank" rel="noreferrer">
              {link.label}<ArrowUpRightIcon className="h-3 w-3" />
            </a>
          ))}
        </FooterGroup>

        <FooterGroup title="Project">
          <a href={GITHUB_URL} target="_blank" rel="noreferrer" className="footer-link"><GitHubIcon className="h-3.5 w-3.5" />GitHub repository</a>
          <a href={MODEL_CARD_URL} target="_blank" rel="noreferrer" className="footer-link">Model card<ArrowUpRightIcon className="h-3 w-3" /></a>
          <a href={RELEASE_NOTES_URL} target="_blank" rel="noreferrer" className="footer-link">Release notes<ArrowUpRightIcon className="h-3 w-3" /></a>
        </FooterGroup>
      </div>

      <div className="border-t border-white/8">
        <div className="site-container flex flex-col gap-2 py-5 font-mono text-[10px] tracking-[0.12em] text-white/25 md:flex-row md:items-center md:justify-between">
          <span>COMMIT {commit.slice(0, 12)}</span>
          <span>SNAPSHOT {formatDateTime(generatedAt).toUpperCase()}</span>
          <span>© 2026 NIALL GILLEN · MIT LICENSE</span>
        </div>
      </div>
    </footer>
  );
}

function FooterGroup({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div>
      <p className="text-[10px] font-medium tracking-[0.22em] text-white/30">{title.toUpperCase()}</p>
      <div className="mt-5 flex flex-col items-start gap-3 text-sm text-white/45">{children}</div>
    </div>
  );
}
