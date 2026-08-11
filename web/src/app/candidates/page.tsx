import type { Metadata } from "next";

import CandidateExplorer from "@/components/candidate-explorer";
import { DisclosurePanel, MetricCard, PageIntro, PlainEnglish, SectionHeading, StatusBadge } from "@/components/ui";
import { formatDate, percent } from "@/lib/format";
import { loadCandidateSnapshot } from "@/lib/site-data";

export const metadata: Metadata = {
  title: "Candidates",
  description: "Inspect Salarium's evidence-governed candidate funnel, score stack, thesis, risk review, and source coverage.",
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
          eyebrow="EVIDENCE-GOVERNED RESEARCH FUNNEL"
          title="From broad discovery"
          muted="to monitored conviction."
          description="The candidate layer is separate from the release portfolio. It compresses a broad discovery universe through quantitative, advanced-model, evidence, catalyst, and risk review so the strongest research questions receive deeper attention."
          aside={<div className="card min-w-64 p-5"><p className="eyebrow">CANDIDATE DATE</p><p className="mt-3 font-mono text-xl text-emerald-300">{formatDate(snapshot.as_of_date)}</p><div className="mt-4"><StatusBadge>RESEARCH SNAPSHOT</StatusBadge></div></div>}
        />

        <section className="mt-10">
          <SectionHeading
            eyebrow="FUNNEL ARCHITECTURE"
            title="Every stage earns the next layer of cost."
            description="Cheap quantitative screening comes first. Higher-cost evidence and qualitative review are reserved for a much smaller set."
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
          <MetricCard label="FINAL RESEARCH SET" value={String(snapshot.evidence_summary.candidate_count)} detail="monitored candidates" />
          <MetricCard label="PRIMARY EVIDENCE" value={String(snapshot.evidence_summary.primary_evidence_supported)} detail={`${percent(primaryShare, 0)} of candidate set`} tone="positive" />
          <MetricCard label="RED-FLAG FREE" value={String(snapshot.evidence_summary.red_flag_free_candidates)} detail="no governed flags" />
          <MetricCard label="EXTERNAL CATALYSTS" value={String(snapshot.evidence_summary.external_catalyst_evidence)} detail="currently verified" tone={snapshot.evidence_summary.external_catalyst_evidence === 0 ? "negative" : "default"} />
        </div>

        <div className="mt-6">
          <PlainEnglish>
            Rankings answer “which stocks look strongest to the model?” Candidates answer “which of those names deserve more human and evidence-based investigation?” A candidate is not automatically a portfolio holding.
          </PlainEnglish>
        </div>

        <section className="mt-10">
          <SectionHeading
            eyebrow="CANDIDATE INTELLIGENCE"
            title="Every name carries its evidence and uncertainty."
            description="Search or filter the governed stack. Expand a candidate to inspect the thesis, risk review, catalyst treatment, score layers, liquidity, and source types."
          />
          <CandidateExplorer candidates={snapshot.candidates} />
        </section>

        <section className="mt-10 grid gap-4 lg:grid-cols-3">
          <EvidenceCard title="Primary supported" body="The packet includes accepted primary filing evidence. This raises evidence coverage; it does not make the investment conclusion automatically positive." tone="positive" />
          <EvidenceCard title="Internal only" body="The packet relies on internal model and market evidence. Confidence is capped rather than filled with unsupported assumptions." />
          <EvidenceCard title="Neutral catalyst" body="When no accepted external catalyst source exists, the catalyst assessment remains neutral instead of inferring a story from price action." tone="negative" />
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
