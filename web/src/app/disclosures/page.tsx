import type { Metadata } from "next";
import Link from "next/link";

import DataStatusStrip from "@/components/data-status-strip";
import { formatDate, formatDateTime } from "@/lib/format";
import { loadCandidateSnapshot, loadForwardPaperSnapshot, loadRankingSnapshot, loadReleaseSnapshot } from "@/lib/site-data";

export const metadata: Metadata = {
  title: "Disclosures",
  description:
    "Read what Salarium's market data, model, simulations, and cost assumptions leave out.",
  alternates: { canonical: "/disclosures" },
};

export default function DisclosuresPage() {
  const release = loadReleaseSnapshot();
  const ranking = loadRankingSnapshot();
  const candidates = loadCandidateSnapshot();
  const forward = loadForwardPaperSnapshot();

  const sections = [
    {
      title: "Research, not personal advice",
      body: "Salarium is a student research project. Nothing here recommends a stock or portfolio for you, asks you to buy anything, or promises a return.",
    },
    {
      title: "Simulated historical performance",
      body: "Returns, Sharpe and Sortino ratios, drawdowns, and turnover come from historical simulations. They are not results from a live brokerage account.",
    },
    {
      title: "Backtest and selection risk",
      body: "I tested several model designs and chose settings after reviewing their historical results. That creates a risk of overfitting. Future markets may behave differently from the test period.",
    },
    {
      title: "Universe and data limitations",
      body: "The model uses available prices, liquidity, economic data, and company information. The stock lists have survivorship bias, and historical point-in-time data is incomplete for some measures and stocks.",
    },
    {
      title: "Transaction costs and capacity",
      body: "The simulations cannot fully capture bid/ask spreads, market impact, stock-borrow costs, financing, taxes, delays, or how much the strategy can trade. Real results could be worse.",
    },
    {
      title: "Covariance and risk estimates",
      body: "The model estimates how stocks move together using a 60-day Ledoit-Wolf covariance estimate. Correlations and volatility can change quickly, so actual risk can be higher than estimated risk.",
    },
    {
      title: "Exposure and leverage",
      body: `The model's exposure limit is ${release.architecture.leverage_cap.toFixed(2)}x, but that is a maximum, not a target. The selected portfolio did not go above 1.00x in the historical test. Borrowing can increase losses and add financing costs.`,
    },
    {
      title: "Rankings and candidates",
      body: "A high rank is not a buy instruction. The portfolio also applies a stock limit, considers how holdings move together, and adjusts total market exposure.",
    },
    {
      title: "No live execution",
      body: "Salarium does not connect to a broker, place trades, manage money, or monitor personal accounts. The site shows saved research and paper portfolios only.",
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
            Research limitations
            <span className="block text-white/32">and data disclosures.</span>
          </h1>
          <p className="mt-6 max-w-3xl text-base leading-7 text-white/48">
            These notes explain how the data and historical tests were built, what costs they include, and what a real account could do differently.
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
          <h2 className="mt-4 text-4xl font-medium tracking-tight">When the published data was made</h2>
          <p className="mt-5 text-sm leading-7 text-white/42">
            Dates below show when each data file was made. Paper rankings update after eligible market closes. They are delayed research data, not live quotes or a brokerage statement.
          </p>
        </div>
        <div className="mt-8 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Artifact label="Paper ranking date" value={forward.status === "available" ? formatDate(forward.data.latest_signal_state.date) : "Unavailable"} note={forward.status === "available" ? `${forward.data.latest_signal_state.universe_count} stocks scored · no orders` : "No published paper snapshot"} />
          <Artifact label="Release file date" value={formatDateTime(release.generated_at_utc)} note={release.provenance.git_commit.slice(0, 12)} />
          <Artifact label="Historical ranking date" value={formatDate(ranking.latest_signal_state.date)} note={`${ranking.latest_signal_state.count} saved rankings`} />
          <Artifact label="Watchlist date" value={formatDate(candidates.as_of_date)} note={`${candidates.evidence_summary.candidate_count} stocks under review`} />
        </div>
      </section>

      <section className="page-section">
        <div className="grid gap-6 lg:grid-cols-[1fr_0.72fr]">
          <div className="border border-red-400/25 bg-red-400/[0.03] p-6 sm:p-9">
            <p className="eyebrow text-red-300">Before using these results</p>
            <h2 className="mt-4 text-3xl font-medium">The model can still be wrong</h2>
            <p className="mt-4 max-w-3xl text-sm leading-7 text-white/45">
              Check the assumptions and consider your own circumstances before making a financial decision. The published results cannot tell you whether this strategy suits you.
            </p>
          </div>
          <div className="border border-white/10 bg-white/[0.018] p-6 sm:p-8">
            <p className="eyebrow">Read the supporting pages</p>
            <div className="mt-6 grid gap-3">
              <Link href="/research" className="button-primary">Review research evidence <span aria-hidden="true">→</span></Link>
              <Link href="/architecture" className="button-secondary">See how the model works</Link>
              <a href="/data/forward_paper_snapshot.json" className="button-secondary">Open paper JSON</a>
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
