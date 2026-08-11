import Link from "next/link";

import { ArrowRightIcon } from "@/components/icons";
import { DecisionCard, MandateCard } from "@/components/research-components";
import { DisclosurePanel, ExternalCta, InternalCta, MetricCard, PlainEnglish, SectionHeading, StatusBadge } from "@/components/ui";
import { formatDate, number, percent } from "@/lib/format";
import { GITHUB_URL, MODEL_CARD_URL } from "@/lib/site-config";
import { loadRankingSnapshot, loadReleaseSnapshot } from "@/lib/site-data";

export default function HomePage() {
  const release = loadReleaseSnapshot();
  const rankingSnapshot = loadRankingSnapshot();
  const core = release.results.core_balanced;
  const topRankings = rankingSnapshot.latest_signal_state.rankings.slice(0, 5);
  const decisions = release.research.decisions.slice(0, 3);

  return (
    <main id="main-content" className="site-main">
      <section className="site-container relative overflow-hidden pb-16 pt-16 sm:pt-24 lg:pb-24 lg:pt-28">
        <div className="pointer-events-none absolute right-0 top-16 hidden h-72 w-72 rounded-full border border-emerald-300/10 lg:block" aria-hidden="true">
          <div className="absolute inset-8 rounded-full border border-white/8" />
          <div className="absolute inset-20 rounded-full border border-white/8" />
          <div className="absolute left-1/2 top-1/2 h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-emerald-300 shadow-[0_0_30px_rgba(110,231,183,.8)]" />
        </div>

        <div className="relative max-w-5xl">
          <div className="flex flex-wrap items-center gap-3">
            <StatusBadge tone="positive">SALARIUM 1.0</StatusBadge>
            <span className="font-mono text-[9px] tracking-[0.16em] text-white/25">COMMITTED RESEARCH SNAPSHOT</span>
          </div>
          <p className="mt-8 eyebrow text-emerald-300">SYSTEMATIC EQUITY RESEARCH</p>
          <h1 className="mt-5 max-w-5xl text-5xl font-semibold leading-[0.98] tracking-[-0.06em] sm:text-7xl lg:text-[5.8rem]">
            Institutional-style research workflow,
            <span className="block text-white/28">built in public.</span>
          </h1>
          <p className="mt-7 max-w-3xl text-base leading-7 text-white/50 sm:text-lg sm:leading-8">
            Salarium turns governed market data into out-of-sample rankings, concentrated portfolios, covariance-aware weights, and auditable exposure decisions—without pretending a backtest is a live trading record.
          </p>
          <div className="mt-9 flex flex-wrap gap-3">
            <InternalCta href="/rankings">Explore rankings</InternalCta>
            <InternalCta href="/architecture" secondary>See the system</InternalCta>
            <ExternalCta href={GITHUB_URL}>View source</ExternalCta>
          </div>
          <div className="mt-8 flex flex-wrap gap-x-7 gap-y-2 font-mono text-[10px] tracking-[0.1em] text-white/28">
            <span>2021–2026 WALK-FORWARD</span>
            <span>LIQUID-500</span>
            <span>LONG-ONLY</span>
            <span>1.25x HARD LEVERAGE CAP</span>
          </div>
        </div>
      </section>

      <section className="border-y border-white/10 bg-white/[0.012]">
        <div className="site-container grid gap-px bg-white/8 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard label="SIMULATED NET RETURN" value={percent(core.annualized_net_return)} detail="annualized, after modeled costs" tone="positive" />
          <MetricCard label="NET SHARPE" value={number(core.net_sharpe)} detail="core balanced candidate" />
          <MetricCard label="MAX DRAWDOWN" value={percent(core.max_drawdown)} detail="historical simulation" tone="negative" />
          <MetricCard label="AVERAGE EXPOSURE" value={`${core.avg_exposure.toFixed(3)}x`} detail="risk-governed, not fully invested" />
        </div>
      </section>

      <section className="site-container site-section">
        <SectionHeading
          eyebrow="WHAT THE SYSTEM DOES"
          title="One research engine. Four governed decisions."
          description="The product is not a single stock score. It is a chain of separately auditable research decisions—from data eligibility to final portfolio exposure."
        />
        <div className="grid gap-4 lg:grid-cols-4">
          <Capability index="01" title="Rank" body="An expanding-window model compares liquid equities using only information available before each test period." href="/rankings" />
          <Capability index="02" title="Investigate" body="A broader evidence funnel prioritizes names for quantitative, fundamental, catalyst, and risk review." href="/candidates" />
          <Capability index="03" title="Construct" body="Top-ranked names are weighted with a 60-day shrinkage covariance model and controlled signal influence." href="/architecture" />
          <Capability index="04" title="Govern" body="Portfolio exposure responds to regime and risk constraints under a hard 1.25x ceiling." href="/research" />
        </div>
        <div className="mt-5">
          <PlainEnglish>
            Salarium studies a governed stock universe, estimates which names may outperform over roughly one month, concentrates on the strongest ten, reduces redundant correlated risk, and then decides how much portfolio exposure the evidence deserves.
          </PlainEnglish>
        </div>
      </section>

      <section className="border-y border-white/10 bg-white/[0.012]">
        <div className="site-container site-section">
          <SectionHeading
            eyebrow="CORE RESEARCH MANDATE"
            title="Concentrated alpha, with risk visibly attached."
            description="The same out-of-sample signal supports multiple risk postures. The balanced candidate is the release focus; aggressive and defensive variants remain explicit comparators."
            action={<Link href="/research" className="footer-link text-xs tracking-[0.12em] text-emerald-300">OPEN FULL EVIDENCE <ArrowRightIcon className="h-4 w-4" /></Link>}
          />
          <div className="grid gap-4 lg:grid-cols-3">
            <MandateCard title="Core Balanced" subtitle="Release candidate" result={core} featured />
            <MandateCard title="Aggressive Reference" subtitle="Static 1.00x" result={release.results.aggressive} />
            <MandateCard title="Defensive Reference" subtitle="Minimum variance" result={release.results.defensive} defensive />
          </div>
        </div>
      </section>

      <section className="site-container site-section">
        <SectionHeading
          eyebrow="LATEST COMMITTED SIGNALS"
          title="The model output is inspectable—not mystified."
          description={`Signal date ${formatDate(rankingSnapshot.latest_signal_state.date)}. This is a repository snapshot, not a live market feed.`}
          action={<InternalCta href="/rankings" secondary>Open all rankings</InternalCta>}
        />
        <div className="card overflow-hidden">
          <div className="hidden grid-cols-[72px_1fr_160px_160px] border-b border-white/10 px-5 py-3 text-[9px] tracking-[0.18em] text-white/25 sm:grid">
            <span>RANK</span><span>SECURITY</span><span>MODEL SCORE</span><span>20D VOLATILITY</span>
          </div>
          <div className="divide-y divide-white/6">
            {topRankings.map((item) => (
              <Link key={item.ticker} href="/rankings" className="grid gap-3 px-5 py-5 transition hover:bg-white/[0.025] sm:grid-cols-[72px_1fr_160px_160px] sm:items-center">
                <span className="font-mono text-sm text-white/25">{String(item.rank).padStart(2, "0")}</span>
                <div><p className="font-semibold tracking-[0.16em]">{item.ticker}</p><p className="mt-1 text-xs text-white/28">{item.risk_state.replaceAll("_", " ").toUpperCase()}</p></div>
                <span className="font-mono text-sm text-emerald-300">{item.score.toFixed(6)}</span>
                <span className="font-mono text-sm text-white/60">{percent(item.volatility_20d, 2)}</span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="border-y border-white/10 bg-white/[0.012]">
        <div className="site-container site-section">
          <SectionHeading
            eyebrow="RESEARCH DECISION LEDGER"
            title="Progress came from rejecting attractive ideas."
            description="A serious research platform records what failed, not just what won. These decisions are generated from committed experiment reports."
            action={<InternalCta href="/research" secondary>View all decisions</InternalCta>}
          />
          <div className="grid gap-4 lg:grid-cols-3">{decisions.map((decision) => <DecisionCard key={decision.key} decision={decision} />)}</div>
        </div>
      </section>

      <section className="site-container site-section">
        <div className="grid gap-6 lg:grid-cols-[1.15fr_.85fr]">
          <div className="card p-7 sm:p-9">
            <p className="eyebrow text-emerald-300">WHY THIS IS DIFFERENT</p>
            <h2 className="mt-5 text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">The research artifact is the product.</h2>
            <p className="mt-5 max-w-2xl text-sm leading-7 text-white/48">Salarium is designed around point-in-time discipline, expanding-window evaluation, reproducible score artifacts, portfolio-policy separation, transaction-cost assumptions, governance tests, and public limitations. The system is intended to be examined—not merely believed.</p>
            <div className="mt-8 flex flex-wrap gap-3"><ExternalCta href={MODEL_CARD_URL} secondary={false}>Read model card</ExternalCta><InternalCta href="/about" secondary>About the project</InternalCta></div>
          </div>
          <div className="card p-7 sm:p-9">
            <p className="eyebrow">DATA STATUS</p>
            <div className="mt-6 space-y-5">
              <DataStatus label="Release research" value={formatDate(release.data_status.release_snapshot.generated_at_utc)} live={false} />
              <DataStatus label="Ranking signal" value={formatDate(release.data_status.ranking_snapshot.signal_date)} live={release.data_status.ranking_snapshot.live} />
              <DataStatus label="Candidate research" value={formatDate(release.data_status.candidate_snapshot.as_of_date)} live={release.data_status.candidate_snapshot.live} />
            </div>
            <p className="mt-6 border-t border-white/8 pt-5 text-xs leading-5 text-white/28">Salarium labels data freshness explicitly. No public surface represents committed snapshots as a live feed.</p>
          </div>
        </div>
      </section>

      <section className="site-container pb-8">
        <DisclosurePanel items={[
          "Historical results are simulated and do not represent live trading performance.",
          "The system remains exposed to data, model, universe-selection, transaction-cost, covariance-estimation, and regime risks.",
          "The 1.25x leverage limit is a ceiling, not a target; the current core result did not exceed 1.00x.",
          "Salarium is an educational research system and does not provide investment advice or personal suitability analysis.",
        ]} />
      </section>
    </main>
  );
}

function Capability({ index, title, body, href }: { index: string; title: string; body: string; href: string }) {
  return (
    <Link href={href} className="card card-hover group flex min-h-64 flex-col p-6">
      <div className="flex items-center justify-between"><span className="font-mono text-xs text-emerald-300">{index}</span><ArrowRightIcon className="h-4 w-4 text-white/20 transition group-hover:translate-x-1 group-hover:text-emerald-300" /></div>
      <h3 className="mt-auto pt-16 text-xl font-medium">{title}</h3>
      <p className="mt-3 text-sm leading-6 text-white/40">{body}</p>
    </Link>
  );
}

function DataStatus({ label, value, live }: { label: string; value: string; live: boolean }) {
  return (
    <div className="flex items-center justify-between gap-5 border-b border-white/6 pb-4 last:border-0 last:pb-0">
      <div><p className="text-sm text-white/62">{label}</p><p className="mt-1 font-mono text-[10px] text-white/25">{value.toUpperCase()}</p></div>
      <StatusBadge tone={live ? "positive" : "neutral"}>{live ? "LIVE" : "SNAPSHOT"}</StatusBadge>
    </div>
  );
}
