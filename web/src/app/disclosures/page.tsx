import type { Metadata } from "next";
import Link from "next/link";

import DataStatusStrip from "@/components/data-status-strip";
import { formatDate, formatDateTime } from "@/lib/format";
import { loadCandidateSnapshot, loadRankingSnapshot, loadReleaseSnapshot } from "@/lib/site-data";

export const metadata: Metadata = {
  title: "Disclosures",
  description:
    "Read Salarium's research, data, performance, model, execution, leverage, and investment-advice disclosures.",
  alternates: { canonical: "/disclosures" },
};

export default function DisclosuresPage() {
  const release = loadReleaseSnapshot();
  const ranking = loadRankingSnapshot();
  const candidates = loadCandidateSnapshot();

  const sections = [
    {
      title: "Research—not investment advice",
      body: "Salarium is an educational and quantitative research system. Nothing on this website is a recommendation, solicitation, personalized portfolio, suitability determination, or promise of future performance.",
    },
    {
      title: "Simulated historical performance",
      body: "All displayed returns, Sharpe ratios, Sortino ratios, drawdowns, hit rates, turnover, exposure, and related metrics are simulated historical research outputs. They are not live brokerage-account results.",
    },
    {
      title: "Backtest and selection risk",
      body: "The project evaluates multiple hypotheses. Even with walk-forward discipline, choosing an architecture after observing historical results creates model-selection and overfitting risk. Future market structure can differ materially from the research period.",
    },
    {
      title: "Universe and data limitations",
      body: "The Liquid-500 and broad-universe pipelines rely on available price, liquidity, macro, and fundamental inputs. The project retains a documented survivorship-bias limitation, and point-in-time coverage is not complete for every feature or security.",
    },
    {
      title: "Transaction costs and capacity",
      body: "Research deductions cannot fully represent spreads, market impact, borrow availability, financing terms, taxes, operational latency, or portfolio capacity. Real execution can be materially worse than simulated execution.",
    },
    {
      title: "Covariance and risk estimates",
      body: "Ledoit-Wolf shrinkage improves stability but does not make covariance forecasts certain. Correlations and volatility can change abruptly, especially in market stress, causing realized risk to exceed forecasts.",
    },
    {
      title: "Leverage governance",
      body: `The release architecture contains a hard ${release.architecture.leverage_cap.toFixed(2)}x exposure ceiling. That ceiling is permission, not a target. The selected release mandate did not require leverage above 1.00x in the committed evaluation. Leverage can magnify losses and financing costs.`,
    },
    {
      title: "Rankings and candidates",
      body: "A high model rank or candidate score is not a trade instruction. Security selection, covariance, position caps, persistence buffers, evidence quality, and portfolio-level exposure rules intervene after ranking.",
    },
    {
      title: "No live execution",
      body: "Salarium 1.0 does not connect to a broker, route orders, manage client assets, monitor personal accounts, or provide execution services. The public site reads committed research artifacts.",
    },
    {
      title: "Open-source responsibility",
      body: "Users who run, modify, or deploy the source code are responsible for validating data licenses, software behavior, security, regulatory obligations, and financial risk in their own environment.",
    },
  ];

  return (
    <main id="main-content" className="site-main">
      <section className="page-section pb-12 pt-16 lg:pt-20">
        <div className="max-w-4xl">
          <p className="eyebrow text-red-300">Research boundaries</p>
          <h1 className="mt-5 text-5xl font-semibold tracking-tight text-balance sm:text-7xl">
            Read the limitations
            <span className="block text-white/32">before the metrics.</span>
          </h1>
          <p className="mt-6 max-w-3xl text-base leading-7 text-white/48">
            Salarium is designed to make risk and uncertainty visible. These disclosures define what the system is, what its evidence represents, and what no visitor should infer from the interface.
          </p>
        </div>
      </section>

      <DataStatusStrip snapshot={release} />

      <section className="page-section">
        <div className="grid gap-4 md:grid-cols-2">
          {sections.map((section, index) => (
            <article key={section.title} className="border border-white/10 bg-white/[0.018] p-6 sm:p-7">
              <div className="flex items-center justify-between gap-5">
                <span className="font-mono text-sm text-red-300">{String(index + 1).padStart(2, "0")}</span>
                <span className="h-1.5 w-1.5 rounded-full bg-red-300" />
              </div>
              <h2 className="mt-8 text-xl font-medium">{section.title}</h2>
              <p className="mt-3 text-sm leading-7 text-white/42">{section.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="page-section border-y border-white/8 bg-white/[0.012]">
        <div className="max-w-3xl">
          <p className="eyebrow">Artifact freshness</p>
          <h2 className="mt-4 text-4xl font-medium tracking-tight">The public data is committed, not streamed.</h2>
          <p className="mt-5 text-sm leading-7 text-white/42">
            Dates below identify the precise research artifacts displayed by the site. They should never be interpreted as a real-time market feed.
          </p>
        </div>
        <div className="mt-8 grid gap-4 md:grid-cols-3">
          <Artifact label="Release evidence" value={formatDateTime(release.generated_at_utc)} note={release.provenance.git_commit.slice(0, 12)} />
          <Artifact label="Ranking signal date" value={formatDate(ranking.latest_signal_state.date)} note={`${ranking.latest_signal_state.count} committed rankings`} />
          <Artifact label="Candidate as-of date" value={formatDate(candidates.as_of_date)} note={`${candidates.evidence_summary.candidate_count} monitored candidates`} />
        </div>
      </section>

      <section className="page-section">
        <div className="grid gap-6 lg:grid-cols-[1fr_0.72fr]">
          <div className="border border-red-400/25 bg-red-400/[0.03] p-6 sm:p-9">
            <p className="eyebrow text-red-300">Bottom line</p>
            <h2 className="mt-4 text-3xl font-medium">Do not make a financial decision from one model output.</h2>
            <p className="mt-4 max-w-3xl text-sm leading-7 text-white/45">
              Independent due diligence, professional advice where appropriate, and a clear understanding of loss tolerance are necessary before any real capital decision. A transparent model can still be wrong.
            </p>
          </div>
          <div className="border border-white/10 bg-white/[0.018] p-6 sm:p-8">
            <p className="eyebrow">Continue with context</p>
            <div className="mt-6 grid gap-3">
              <Link href="/research" className="button-primary">Review research evidence <span aria-hidden="true">→</span></Link>
              <Link href="/architecture" className="button-secondary">Understand the system</Link>
              <a href="/data/release_snapshot.json" className="button-secondary">Open release JSON</a>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}

function Artifact({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <article className="border border-white/10 bg-black/25 p-5">
      <p className="text-[9px] uppercase tracking-[0.16em] text-white/25">{label}</p>
      <p className="mt-3 font-mono text-sm text-white/72">{value}</p>
      <p className="mt-2 text-xs text-white/28">{note}</p>
    </article>
  );
}
