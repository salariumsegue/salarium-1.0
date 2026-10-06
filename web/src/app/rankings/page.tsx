import type { Metadata } from "next";
import RankingExplorer from "@/components/ranking-explorer";
import { DisclosurePanel, InternalCta, MetricCard, PageIntro, PlainEnglish, SectionHeading, StatusBadge } from "@/components/ui";
import { formatDate, formatDateTime, number, percent } from "@/lib/format";
import { loadForwardPaperSnapshot, loadRankingSnapshot, loadReleaseSnapshot } from "@/lib/site-data";

export const metadata: Metadata = {
  title: "Rankings",
  description: "See which stocks Salarium's 20-day model ranked highest and how to read each score.",
  alternates: { canonical: "/rankings" },
};

export default function RankingsPage() {
  const committed = loadRankingSnapshot();
  const forward = loadForwardPaperSnapshot();
  const snapshot = forward.status === "available" ? forward.data : committed;
  const isForward = forward.status === "available";
  const release = loadReleaseSnapshot();
  const rankings = snapshot.latest_signal_state.rankings;
  const avgVolatility = rankings.reduce((sum, item) => sum + item.volatility_20d, 0) / rankings.length;
  const riskOffCount = rankings.filter((item) => item.risk_state === "risk_off").length;
  const topScore = Math.max(...rankings.map((item) => item.score));

  return (
    <main id="main-content" className="site-main">
      <section className="site-container site-section">
        <PageIntro
          eyebrow={isForward ? "FORWARD PAPER / MARKET CLOSE" : "OUT-OF-SAMPLE MODEL OUTPUT"}
          title="Stocks ranked by the 20-day model"
          muted="A score is not a price target."
          description={`These are the top ${snapshot.latest_signal_state.count} of ${snapshot.latest_signal_state.universe_count} stocks in the ${isForward ? "latest paper" : "committed research"} ranking dated ${formatDate(snapshot.latest_signal_state.date)}. Scores compare stocks in this group; they do not predict a specific return.`}
          aside={<div className="card min-w-64 p-5"><p className="eyebrow">SIGNAL DATE</p><p className="mt-3 font-mono text-xl text-emerald-300">{formatDate(snapshot.latest_signal_state.date)}</p><div className="mt-4"><StatusBadge tone={isForward ? "positive" : "neutral"}>{isForward ? "PAPER / NO ORDERS" : "NOT LIVE"}</StatusBadge></div></div>}
        />

        <div className="ranking-summary-grid mt-7 grid gap-px sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard label="STOCKS SHOWN" value={String(rankings.length)} detail={`ranked from ${snapshot.latest_signal_state.universe_count} stocks`} />
          <MetricCard label="HIGHEST SCORE" value={topScore.toFixed(6)} detail="relative score in this ranking" tone="positive" />
          <MetricCard label="AVERAGE 20D VOL" value={percent(avgVolatility, 2)} detail="recent single-name volatility" />
          {isForward ? <ForwardStateCard exposure={forward.data.forward_portfolio.shadow_equity_exposure} coverage={forward.data.data_quality.feature_coverage} /> : <RegimeStateCard riskOffCount={riskOffCount} total={rankings.length} />}
        </div>

        <section className="ranking-primary mt-8">
          <SectionHeading
            eyebrow="STOCK BY STOCK"
            title="The full ranking"
            description="Select a row to see its score, rank, recent volatility, risk label, and source snapshot."
          />
          <RankingExplorer rankings={rankings} snapshot={snapshot} />
        </section>

        <div className="mt-6">
          <PlainEnglish>
            A higher rank means the model scored that stock above more of the other 499 names on this date. The model score alone does not put a stock in the portfolio. Selection rules, prior holdings, volatility, position limits, and total exposure also matter.
          </PlainEnglish>
        </div>

        <section className="mt-10 grid gap-4 lg:grid-cols-3">
          <InterpretationCard title="Model score" body="A stock's score compared with the other names in this snapshot. Compare scores only within the same date." />
          <InterpretationCard title="20-day volatility" body="A recent single-name risk estimate. It is not the portfolio forecast; the covariance engine evaluates how selected holdings interact." />
          <InterpretationCard title="Risk state" body="A macro/risk context flag used by downstream exposure controls. It does not overwrite the cross-sectional ranking." />
        </section>

        <section className="mt-10 card p-6 sm:p-8">
          <div className="grid gap-6 lg:grid-cols-[1fr_auto] lg:items-center">
            <div>
              <p className="eyebrow text-emerald-300">FROM RANK TO PORTFOLIO</p>
              <h2 className="mt-4 text-2xl font-semibold tracking-[-0.035em]">How rankings become portfolio holdings</h2>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-white/42">The release architecture uses a Top-{release.architecture.top_n} selection, rank-{release.architecture.buffer_rank} persistence buffer, {release.architecture.covariance_lookback_days}-day shrinkage covariance, and a {Math.round(release.architecture.signal_blend * 100)}% signal-aware blend before exposure control.</p>
            </div>
            <div className="flex flex-wrap gap-3"><InternalCta href="/architecture">See construction</InternalCta><InternalCta href="/candidates" secondary>Open candidate research</InternalCta></div>
          </div>
        </section>

        <p className="mt-8 font-mono text-[10px] leading-5 text-white/22">MODEL {snapshot.model.configuration.toUpperCase()} · {snapshot.model.source_rows.toLocaleString()} TRAINING ROWS · SNAPSHOT GENERATED {formatDateTime(snapshot.generated_at_utc).toUpperCase()} · RELEASE SHARPE REFERENCE {number(release.results.core_balanced.net_sharpe)}</p>
      </section>

      <section className="site-container pb-8">
        <DisclosurePanel items={[
          isForward ? "This ranking is a forward paper market-close feed, not live investment performance or an exchange-grade quote feed." : "The ranking snapshot is committed research data, not a continuously updated market feed.",
          "Rankings can change materially as prices, volatility, and features change. The frozen model is not retrained by the daily refresh.",
          "A high score does not imply suitability, valuation support, catalyst certainty, or a buy instruction.",
          "The release result is simulated and should not be interpreted as future performance evidence.",
        ]} />
      </section>
    </main>
  );
}

function ForwardStateCard({ exposure, coverage }: { exposure: number; coverage: number }) {
  return <div className="regime-state-card"><p>PAPER RISK STATE</p><div><strong>{percent(exposure, 0)}</strong><em>EXPOSURE</em></div><small><i className="positive-dot" />{percent(coverage, 1)} feature coverage</small></div>;
}

function InterpretationCard({ title, body }: { title: string; body: string }) {
  return <div className="card p-6"><p className="text-base font-medium">{title}</p><p className="mt-3 text-sm leading-6 text-white/42">{body}</p></div>;
}

function RegimeStateCard({ riskOffCount, total }: { riskOffCount: number; total: number }) {
  const riskOff = riskOffCount > total / 2;
  return <div className="regime-state-card"><p>REGIME STATE</p><div><strong>{riskOffCount}<span> / {total}</span></strong><em className={riskOff?"is-risk-off":""}>{riskOff?"RISK-OFF":"MIXED"}</em></div><small><i className={riskOff?"negative-dot":"positive-dot"} />Committed snapshot</small></div>;
}
