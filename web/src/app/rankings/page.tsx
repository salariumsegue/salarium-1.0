import type { Metadata } from "next";
import RankingExplorer from "@/components/ranking-explorer";
import { DisclosurePanel, InternalCta, MetricCard, PageIntro, PlainEnglish, SectionHeading, StatusBadge } from "@/components/ui";
import { formatDate, formatDateTime, number, percent } from "@/lib/format";
import { loadRankingSnapshot, loadReleaseSnapshot } from "@/lib/site-data";

export const metadata: Metadata = {
  title: "Rankings",
  description: "Inspect Salarium's latest committed out-of-sample equity ranking snapshot, score context, volatility, and regime state.",
  alternates: { canonical: "/rankings" },
};

export default function RankingsPage() {
  const snapshot = loadRankingSnapshot();
  const release = loadReleaseSnapshot();
  const rankings = snapshot.latest_signal_state.rankings;
  const avgVolatility = rankings.reduce((sum, item) => sum + item.volatility_20d, 0) / rankings.length;
  const riskOffCount = rankings.filter((item) => item.risk_state === "risk_off").length;
  const topScore = Math.max(...rankings.map((item) => item.score));

  return (
    <main id="main-content" className="site-main">
      <section className="site-container site-section">
        <PageIntro
          eyebrow="OUT-OF-SAMPLE MODEL OUTPUT"
          title="Ranked securities."
          muted="Full context, no false precision."
          description={`Explore the top ${snapshot.latest_signal_state.count} names from the final ${snapshot.architecture.model_horizon_days}D model's latest committed ${snapshot.latest_signal_state.universe_count}-security cross-section. Scores express relative conviction; they are not price targets, recommendations, or guaranteed expected returns.`}
          aside={<div className="card min-w-64 p-5"><p className="eyebrow">SIGNAL DATE</p><p className="mt-3 font-mono text-xl text-emerald-300">{formatDate(snapshot.latest_signal_state.date)}</p><div className="mt-4"><StatusBadge>NOT LIVE</StatusBadge></div></div>}
        />

        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard label="PUBLISHED RANKINGS" value={String(rankings.length)} detail={`${snapshot.latest_signal_state.universe_count}-name cross-section`} />
          <MetricCard label="TOP MODEL SCORE" value={topScore.toFixed(6)} detail="relative cross-sectional output" tone="positive" />
          <MetricCard label="AVERAGE 20D VOL" value={percent(avgVolatility, 2)} detail="recent single-name volatility" />
          <MetricCard label="RISK-OFF NAMES" value={`${riskOffCount}/${rankings.length}`} detail="committed regime state" tone={riskOffCount > rankings.length / 2 ? "negative" : "default"} />
        </div>

        <div className="mt-6">
          <PlainEnglish>
            A higher-ranked stock scored better than other stocks in the same governed Liquid-500 cross-section at this historical signal date. The public table shows the top 25 for inspection; the release portfolio still applies Top-10 selection, persistence, covariance, position limits, and exposure rules before a name can influence a research mandate.
          </PlainEnglish>
        </div>

        <section className="mt-10">
          <SectionHeading
            eyebrow="INTERACTIVE RANKING EXPLORER"
            title="Search, filter, sort, and inspect."
            description="Open any row for a plain-language explanation of the score, volatility field, and portfolio status."
          />
          <RankingExplorer rankings={rankings} />
        </section>

        <section className="mt-10 grid gap-4 lg:grid-cols-3">
          <InterpretationCard title="Model score" body="A relative signal produced by the governed technical ranking model. Magnitudes are meaningful only inside the same model snapshot." />
          <InterpretationCard title="20-day volatility" body="A recent single-name risk estimate. It is not the portfolio forecast; the covariance engine evaluates how selected holdings interact." />
          <InterpretationCard title="Risk state" body="A macro/risk context flag used by downstream exposure controls. It does not overwrite the cross-sectional ranking." />
        </section>

        <section className="mt-10 card p-6 sm:p-8">
          <div className="grid gap-6 lg:grid-cols-[1fr_auto] lg:items-center">
            <div>
              <p className="eyebrow text-emerald-300">FROM RANK TO PORTFOLIO</p>
              <h2 className="mt-4 text-2xl font-semibold tracking-[-0.035em]">Rankings are an input—not the final product.</h2>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-white/42">The release architecture uses a Top-{release.architecture.top_n} selection, rank-{release.architecture.buffer_rank} persistence buffer, {release.architecture.covariance_lookback_days}-day shrinkage covariance, and a {Math.round(release.architecture.signal_blend * 100)}% signal-aware blend before exposure control.</p>
            </div>
            <div className="flex flex-wrap gap-3"><InternalCta href="/architecture">See construction</InternalCta><InternalCta href="/candidates" secondary>Open candidate research</InternalCta></div>
          </div>
        </section>

        <p className="mt-8 font-mono text-[10px] leading-5 text-white/22">MODEL {snapshot.model.configuration.toUpperCase()} · {snapshot.model.source_rows.toLocaleString()} OOS SCORE ROWS · SNAPSHOT GENERATED {formatDateTime(snapshot.generated_at_utc).toUpperCase()} · RELEASE SHARPE REFERENCE {number(release.results.core_balanced.net_sharpe)}</p>
      </section>

      <section className="site-container pb-8">
        <DisclosurePanel items={[
          "The ranking snapshot is committed research data, not a continuously updated market feed.",
          "Rankings can change materially as prices, volatility, features, and model-training windows change.",
          "A high score does not imply suitability, valuation support, catalyst certainty, or a buy instruction.",
          "The release result is simulated and should not be interpreted as future performance evidence.",
        ]} />
      </section>
    </main>
  );
}

function InterpretationCard({ title, body }: { title: string; body: string }) {
  return <div className="card p-6"><p className="text-base font-medium">{title}</p><p className="mt-3 text-sm leading-6 text-white/42">{body}</p></div>;
}
