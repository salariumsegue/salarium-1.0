import Link from "next/link";

import { EdgeGlyph } from "@/components/edge-glyph";
import HistoricalAccountChart from "@/components/historical-account-chart";
import { InternalCta } from "@/components/ui";
import { formatDate, percent } from "@/lib/format";
import { loadHypotheticalAccountSnapshot, loadRankingSnapshot, loadReleaseSnapshot } from "@/lib/site-data";

const currency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

export default function HomePage() {
  const release = loadReleaseSnapshot();
  const ranking = loadRankingSnapshot();
  const account = loadHypotheticalAccountSnapshot();
  const architecture = release.architecture;
  const core = release.results.core_balanced;

  return (
    <main id="main-content" className="site-main home-cinematic">
      <section className="hero-shell hero-shell-cinematic">
        <div className="site-container hero-grid">
          <div className="hero-statement">
            <p className="roman-inscription">SALARIUM / MMXXVI</p>
            <h1>
              Research the edge.
              <span>Govern the risk.</span>
            </h1>
            <p className="hero-copy hero-copy-short">Systematic equity research for liquid markets.</p>
            <div className="hero-actions">
              <InternalCta href="/rankings">Explore Rankings</InternalCta>
              <InternalCta href="/methodology" secondary>Inspect Method</InternalCta>
            </div>
            <p className="hero-disclaimer">SIMULATED RESEARCH · NO LIVE EXECUTION</p>
          </div>

          <aside className="system-status" aria-label="Current Salarium research system status">
            <header><span>SALARIUM / RESEARCH SYSTEM</span><i>COMMITTED SNAPSHOT</i></header>
            <div className="system-status-mark">
              <EdgeGlyph title="Salarium Imperial Edge Glyph" />
              <p>MARKET-EDGE RING / PROPRIETARY SIGNAL MARK</p>
            </div>
            <dl>
              <div><dt>Model</dt><dd>{architecture.model_horizon_days}D</dd></div>
              <div><dt>Universe</dt><dd>{architecture.universe.toUpperCase()}</dd></div>
              <div><dt>Release</dt><dd>{release.release.version}</dd></div>
              <div><dt>Snapshot</dt><dd>{formatDate(ranking.latest_signal_state.date)}</dd></div>
              <div className="system-status-state"><dt>Status</dt><dd><span />Committed / not live</dd></div>
            </dl>
          </aside>
        </div>
      </section>

      <section className="account-stage">
        <div className="site-container">
          <header className="account-stage-heading">
            <div>
              <p className="roman-inscription">HYPOTHETICAL ACCOUNT / MARKET COMPARISON</p>
              <h2>$100,000, system versus market.</h2>
            </div>
            <div className="account-ending-values">
              <div className="account-ending-value account-ending-model">
                <span>SALARIUM / SIMULATED</span>
                <strong>{currency.format(account.ending_balance)}</strong>
              </div>
              <div className="account-ending-value account-ending-benchmark">
                <span>S&amp;P 500 / SPY PROXY</span>
                <strong>{currency.format(account.benchmark.ending_balance)}</strong>
              </div>
            </div>
          </header>

          <HistoricalAccountChart snapshot={account} />

          <dl className="account-ledger">
            <div><dt>Holding period</dt><dd>{monthYear(account.period.start)} — {monthYear(account.period.end)}</dd></div>
            <div><dt>Annualized</dt><dd><b>Salarium {percent(account.statistics.annualized_net_return)}</b><small>SPY {percent(account.benchmark.statistics.annualized_total_return)}</small></dd></div>
            <div><dt>Maximum drawdown</dt><dd><b className="negative-value">Salarium {percent(account.statistics.max_drawdown)}</b><small>SPY {percent(account.benchmark.statistics.max_drawdown)}</small></dd></div>
            <div><dt>Observations</dt><dd>{account.statistics.rebalances} rebalances</dd></div>
          </dl>
          <p className="account-disclosure">Both lines begin with a hypothetical $100,000 on identical dates. Salarium compounds the governed out-of-sample portfolio stream after modeled transaction costs; the market comparison is a buy-and-hold SPY adjusted-close total-return proxy. Taxes, capacity limits, additional market impact, and the benchmark&apos;s initial trade cost are excluded. Simulated research—not live performance.</p>
        </div>
      </section>

      <section className="system-showcase site-container">
        <header className="showcase-heading">
          <p className="roman-inscription">THE RESEARCH CHAIN / II</p>
          <h2>One signal. Six controls.</h2>
        </header>
        <div className="pipeline-row pipeline-roman">
          {[
            ["I", "Universe", "500"],
            ["II", "Alpha", "20D"],
            ["III", "Rank", "01—500"],
            ["IV", "Select", "Top 10"],
            ["V", "Construct", "Covariance"],
            ["VI", "Govern", "Exposure"],
          ].map(([index, title, detail]) => (
            <div key={index}><span>{index}</span><strong>{title}</strong><small>{detail}</small></div>
          ))}
        </div>
      </section>

      <section className="ranking-stage">
        <div className="site-container ranking-stage-grid">
          <header>
            <p className="roman-inscription">LATEST SIGNAL / III</p>
            <h2>Ranked now.</h2>
            <p>{formatDate(ranking.latest_signal_state.date)}</p>
            <InternalCta href="/rankings" secondary>Open all rankings</InternalCta>
          </header>
          <div className="ranking-preview ranking-preview-large">
            {ranking.latest_signal_state.rankings.slice(0, 5).map((row) => (
              <Link href="/rankings" key={row.ticker}>
                <span>{String(row.rank).padStart(2, "0")}</span>
                <strong>{row.ticker}</strong>
                <em>{row.score.toFixed(6)}</em>
                <small>{percent(row.score_percentile, 1)}</small>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="evidence-strip" aria-label="Selected simulated research evidence">
        <div className="site-container">
          <div><span>NET RETURN</span><strong>{percent(core.annualized_net_return)}</strong></div>
          <div><span>NET SHARPE</span><strong>{core.net_sharpe.toFixed(2)}</strong></div>
          <div><span>MAX DRAWDOWN</span><strong className="negative-value">{percent(core.max_drawdown)}</strong></div>
          <div><span>AVG EXPOSURE</span><strong>{core.avg_exposure.toFixed(2)}x</strong></div>
        </div>
      </section>

      <section className="home-portals site-container">
        {[
          ["IV", "Evidence", "/research/performance"],
          ["V", "Rejected ideas", "/research/experiments"],
          ["VI", "Architecture", "/architecture"],
          ["VII", "Methodology", "/methodology"],
        ].map(([index, label, href]) => (
          <Link href={href} key={href}><span>{index}</span><strong>{label}</strong><i>↗</i></Link>
        ))}
      </section>
    </main>
  );
}

function monthYear(value: string) {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`)).toUpperCase();
}
