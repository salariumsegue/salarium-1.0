import type { Metadata } from "next";

import CandidateExplorer from "@/components/candidate-explorer";
import { DisclosurePanel, MetricCard, PageIntro, PlainEnglish, SectionHeading, StatusBadge } from "@/components/ui";
import { formatDate, percent } from "@/lib/format";
import { loadCandidateSnapshot } from "@/lib/site-data";

export const metadata: Metadata = {
  title: "Candidates",
  description: "See how stocks move from a broad screen to a smaller research list, with sources and risk notes.",
  alternates: { canonical: "/candidates" },
};

export default function CandidatesPage() {
  const snapshot = loadCandidateSnapshot();
  const primaryShare = snapshot.evidence_summary.candidate_count
    ? snapshot.evidence_summary.primary_evidence_supported / snapshot.evidence_summary.candidate_count
    : 0;

  return (
    <main id="main-content" className="site-main">
      <section className="site-container site-section">
        <PageIntro
          eyebrow="RESEARCH WATCHLIST"
          title="Stocks selected for a closer look"
          muted="Kept separate from the paper portfolio."
          description="The screen starts with a broad list and narrows it using model scores, company filings, news, and risk checks. A name on this list is not a portfolio holding or a buy recommendation."
          aside={<div className="card min-w-64 p-5"><p className="eyebrow">CANDIDATE DATE</p><p className="mt-3 font-mono text-xl text-emerald-300">{formatDate(snapshot.as_of_date)}</p><div className="mt-4"><StatusBadge>RESEARCH SNAPSHOT</StatusBadge></div></div>}
        />

        <section className="mt-10">
          <SectionHeading
            eyebrow="SCREENING PROCESS"
            title="How the list gets smaller"
            description="Fast number checks narrow the list first. Filing, news, and manual review cover fewer stocks."
          />
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
            {snapshot.architecture.stages.map((stage, index) => (
              <div key={stage.key} className="card relative min-h-52 p-5">
                <div className="flex items-center justify-between"><span className="font-mono text-[10px] text-emerald-300">STAGE {String(index + 1).padStart(2, "0")}</span><span className="h-1.5 w-1.5 rounded-full bg-white/20" /></div>
                <p className="mt-8 font-mono text-3xl">{stage.count.toLocaleString()}</p>
                <p className="mt-3 text-[9px] uppercase tracking-[0.15em] text-white/50">{stage.label}</p>
                <p className="mt-3 text-xs leading-5 text-white/28">{stage.description}</p>
                {index < snapshot.architecture.stages.length - 1 && <span className="absolute -right-2 top-1/2 z-10 hidden text-white/20 lg:block">→</span>}
              </div>
            ))}
          </div>
        </section>

        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard label="WATCHLIST SIZE" value={String(snapshot.evidence_summary.candidate_count)} detail="stocks for further review" />
          <MetricCard label="FILING SUPPORT" value={String(snapshot.evidence_summary.primary_evidence_supported)} detail={`${percent(primaryShare, 0)} of this list`} tone="positive" />
          <MetricCard label="NO FLAGGED ISSUES" value={String(snapshot.evidence_summary.red_flag_free_candidates)} detail="under current checks" />
          <MetricCard label="VERIFIED NEWS CATALYSTS" value={String(snapshot.evidence_summary.external_catalyst_evidence)} detail="sources currently accepted" tone={snapshot.evidence_summary.external_catalyst_evidence === 0 ? "negative" : "default"} />
        </div>

        <div className="mt-6">
          <PlainEnglish>
            Rankings show which stocks scored well. This watchlist adds filings, news, and risk notes to help decide what deserves more research. A high score or a watchlist entry does not make a stock a holding.
          </PlainEnglish>
        </div>

        <section className="mt-10">
          <SectionHeading
            eyebrow="COMPANY NOTES"
            title="What we know about each stock"
            description="Search the list and open a stock to read its case, risk notes, model scores, liquidity, and source links."
          />
          <CandidateExplorer candidates={snapshot.candidates} />
        </section>

        <section className="mt-10 grid gap-4 lg:grid-cols-3">
          <EvidenceCard title="Company filing found" body="The review includes a company filing. That adds a source to check; it does not mean the stock is a good investment." tone="positive" />
          <EvidenceCard title="Model data only" body="The review has model and market data, but no outside source. The score stays limited until more information is available." />
          <EvidenceCard title="No verified news" body="When there is no reliable news source for a catalyst, the review makes no claim based on price changes alone." tone="negative" />
        </section>
      </section>

      <section className="site-container pb-8">
        <DisclosurePanel items={snapshot.disclosures} />
      </section>
    </main>
  );
}

function EvidenceCard({ title, body, tone = "neutral" }: { title: string; body: string; tone?: "positive" | "negative" | "neutral" }) {
  const color = tone === "positive" ? "text-emerald-300" : tone === "negative" ? "text-red-300" : "text-white/55";
  return <div className="card p-6"><p className={`text-base font-medium ${color}`}>{title}</p><p className="mt-3 text-sm leading-6 text-white/42">{body}</p></div>;
}
