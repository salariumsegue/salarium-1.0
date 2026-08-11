import type { Metadata } from "next";
import Link from "next/link";

import DataStatusStrip from "@/components/data-status-strip";
import MandateCard from "@/components/mandate-card";
import MetricCard from "@/components/metric-card";
import {
  AnnualPerformanceTable,
  ConstructorComparison,
  DecisionGrid,
  RobustnessTable,
  SignalBlendFrontier,
} from "@/components/research-visuals";
import { number, percent } from "@/lib/format";
import { loadReleaseSnapshot } from "@/lib/site-data";

export const metadata: Metadata = {
  title: "Research",
  description:
    "Review Salarium's walk-forward evidence, annual performance, rejected hypotheses, robustness checks, and locked release decisions.",
  alternates: { canonical: "/research" },
};

export default function ResearchPage() {
  const release = loadReleaseSnapshot();
  const research = release.research;
  const core = release.results.core_balanced;

  return (
    <main id="main-content" className="site-main">
      <section className="page-section pb-12 pt-16 lg:pt-20">
        <div className="grid gap-10 lg:grid-cols-[1fr_0.72fr] lg:items-end">
          <div>
            <p className="eyebrow">Research record</p>
            <h1 className="mt-5 text-5xl font-semibold tracking-tight text-balance sm:text-7xl">
              Evidence first.
              <span className="block text-white/32">Rejected ideas included.</span>
            </h1>
            <p className="mt-6 max-w-3xl text-base leading-7 text-white/48">
              The release architecture is the result of controlled walk-forward experiments—not a collection of parameters chosen because they looked sophisticated. This page shows what improved, what failed, and what remains uncertain.
            </p>
          </div>

          <aside className="border border-white/10 bg-white/[0.018] p-6">
            <p className="eyebrow">Committed evaluation</p>
            <dl className="mt-5 grid gap-4">
              <Fact label="Period" value={research.period} />
              <Fact label="Core rebalances" value={String(core.num_rebalances)} />
              <Fact label="Average exposure" value={`${core.avg_exposure.toFixed(3)}x`} />
              <Fact label="Live performance" value="No" risk />
            </dl>
          </aside>
        </div>
      </section>

      <DataStatusStrip snapshot={release} />

      <section className="page-section">
        <div className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="eyebrow">Three operating mandates</p>
            <h2 className="mt-4 text-4xl font-medium tracking-tight">One alpha engine, different risk choices.</h2>
          </div>
          <Link href="/architecture" className="text-link">Trace the architecture <span aria-hidden="true">→</span></Link>
        </div>

        <div className="mt-8 grid gap-4 lg:grid-cols-3">
          <MandateCard title="Core balanced" subtitle="Release candidate" result={release.results.core_balanced} featured />
          <MandateCard title="Aggressive" subtitle="Static 1.00x research" result={release.results.aggressive} />
          <MandateCard title="Defensive" subtitle="Minimum-variance anchor" result={release.results.defensive} defensive />
        </div>

        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard label="Core net return" value={percent(core.annualized_net_return)} detail="Simulated annualized net result" tone="positive" />
          <MetricCard label="Core Sharpe" value={number(core.net_sharpe)} detail="Risk-adjusted return across the full record" />
          <MetricCard label="Core Sortino" value={number(core.net_sortino)} detail="Downside-risk-adjusted result" />
          <MetricCard label="Core max drawdown" value={percent(core.max_drawdown)} detail="Historical simulated peak-to-trough decline" tone="negative" />
        </div>
      </section>

      <section className="page-section border-y border-white/8 bg-white/[0.012]">
        <div className="max-w-3xl">
          <p className="eyebrow">Annual out-of-sample record</p>
          <h2 className="mt-4 text-4xl font-medium tracking-tight">No single aggregate number gets the final word.</h2>
          <p className="mt-5 text-sm leading-7 text-white/42">
            Annual expanding-window fits produce a year-by-year view of the same locked architecture. This helps expose whether the result depends on one unusually favorable regime.
          </p>
        </div>
        <div className="mt-8">
          <AnnualPerformanceTable
            core={research.yearly.core_balanced}
            aggressive={research.yearly.aggressive}
            defensive={research.yearly.defensive}
          />
        </div>
      </section>

      <section className="page-section">
        <div className="max-w-3xl">
          <p className="eyebrow">Controlled decisions</p>
          <h2 className="mt-4 text-4xl font-medium tracking-tight">The path to the locked release.</h2>
          <p className="mt-5 text-sm leading-7 text-white/42">
            Every decision below corresponds to a committed comparison. Failed hypotheses stay visible because a credible research platform records what did not work.
          </p>
        </div>
        <div className="mt-9">
          <DecisionGrid decisions={research.decisions} />
        </div>
      </section>

      <section className="page-section border-y border-white/8 bg-black/45">
        <div className="grid gap-10 lg:grid-cols-2">
          <div>
            <p className="eyebrow">Covariance constructor</p>
            <h2 className="mt-4 text-3xl font-medium">Joint risk improved the Top-10.</h2>
            <p className="mt-4 max-w-xl text-sm leading-7 text-white/42">
              The 60-day shrinkage covariance tournament compared the original inverse-volatility baseline with minimum-variance and maximum-diversification portfolios while holding the upstream alpha signal fixed.
            </p>
            <div className="mt-7">
              <ConstructorComparison rows={research.covariance} />
            </div>
          </div>

          <div>
            <p className="eyebrow">Signal-aware weighting</p>
            <h2 className="mt-4 text-3xl font-medium">Conviction helps—until it dominates risk.</h2>
            <p className="mt-4 max-w-xl text-sm leading-7 text-white/42">
              A 25% signal blend gives model conviction a meaningful vote while preserving the covariance engine as the primary portfolio-risk anchor.
            </p>
            <div className="mt-7">
              <SignalBlendFrontier rows={research.signal_blend} />
            </div>
          </div>
        </div>
      </section>

      <section className="page-section">
        <div className="max-w-3xl">
          <p className="eyebrow">Robustness</p>
          <h2 className="mt-4 text-4xl font-medium tracking-tight">Stability matters more than one winning cell.</h2>
          <p className="mt-5 text-sm leading-7 text-white/42">
            The selected blend is evaluated against the same-anchor 0% signal baseline across six annual test periods. The record is mixed rather than universal, which is why the signal share remains governed at 25%.
          </p>
        </div>
        <div className="mt-8 grid gap-5 lg:grid-cols-2">
          <RobustnessTable rows={release.robustness.max_diversification_legacy} title="Legacy risk-scaled mandate" />
          <RobustnessTable rows={release.robustness.max_diversification_static} title="Static 1.00x mandate" />
        </div>
      </section>

      <section className="page-section border-y border-white/8 bg-red-400/[0.025]">
        <div className="grid gap-8 lg:grid-cols-[0.72fr_1.28fr]">
          <div>
            <p className="eyebrow text-red-300">Research limitations</p>
            <h2 className="mt-4 text-3xl font-medium">Strong evidence is not certainty.</h2>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <Limit title="Simulated returns" body="All displayed performance is historical research, not live account performance." />
            <Limit title="Survivorship exposure" body="The current universe process retains a documented survivorship-bias limitation." />
            <Limit title="Model selection" body="Multiple experiments increase the chance of choosing patterns that may not persist." />
            <Limit title="Execution reality" body="Borrow costs, market impact, taxes, and capacity can differ from research assumptions." />
            <Limit title="Covariance instability" body="A 60-day risk estimate can fail when correlations change abruptly." />
            <Limit title="No suitability assessment" body="The system does not know any visitor's objectives, constraints, or risk tolerance." />
          </div>
        </div>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link href="/disclosures" className="button-primary">Read complete disclosures <span aria-hidden="true">→</span></Link>
          <a href="/data/release_snapshot.json" className="button-secondary">Inspect release JSON</a>
        </div>
      </section>
    </main>
  );
}

function Fact({ label, value, risk = false }: { label: string; value: string; risk?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-5 border-t border-white/8 pt-4 first:border-t-0 first:pt-0">
      <dt className="text-[9px] uppercase tracking-[0.16em] text-white/25">{label}</dt>
      <dd className={`font-mono text-xs ${risk ? "text-red-300" : "text-white/62"}`}>{value}</dd>
    </div>
  );
}

function Limit({ title, body }: { title: string; body: string }) {
  return (
    <article className="border border-red-400/15 bg-black/25 p-5">
      <h3 className="text-sm font-medium text-red-200">{title}</h3>
      <p className="mt-2 text-xs leading-6 text-white/38">{body}</p>
    </article>
  );
}
