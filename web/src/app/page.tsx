import Link from "next/link";
import fs from "node:fs";
import path from "node:path";
import type { PaperPortfolios } from "@/lib/paper-portfolios";
import HistoricalAccountChart from "@/components/historical-account-chart";
import { EdgeGlyph } from "@/components/edge-glyph";
import {
  loadHypotheticalAccountSnapshot,
  loadReleaseSnapshot,
} from "@/lib/site-data";
import { percent, formatDate } from "@/lib/format";

export default function HomePage() {
  const comparison = JSON.parse(
    fs.readFileSync(path.join(process.cwd(), "public/data/paper_portfolios.json"), "utf8"),
  ) as PaperPortfolios;
  const release = loadReleaseSnapshot();
  const account = loadHypotheticalAccountSnapshot();
  const money = (n: number) => new Intl.NumberFormat("en-US", {
    style: "currency", currency: "USD", maximumFractionDigits: 0,
  }).format(n);

  return (
    <main id="main-content" className="site-main home-vision">
      <section className="home-vision-hero" aria-labelledby="home-title">
        <div className="home-hero-grid" aria-hidden="true" />
        <div className="home-hero-meta"><span>INDEPENDENT INVESTMENT RESEARCH</span><span>EST. 2024 / BLOOMINGTON, IN</span></div>
        <div className="home-hero-center">
          <div className="home-mark-field"><span className="home-mark-ring home-mark-ring-a" /><span className="home-mark-ring home-mark-ring-b" /><EdgeGlyph className="home-center-mark" /></div>
          <p className="home-hero-overline">SALARIUM / SYSTEMATIC EQUITY</p>
          <h1 id="home-title">Capital allocation,<br /><em>under a microscope.</em></h1>
          <p className="home-hero-deck">A stock-selection model and four paper portfolios, documented from first ranking to final rebalance.</p>
          <div className="home-hero-actions"><Link href="/research">Enter the research record <span aria-hidden="true">↘</span></Link><Link href="/dashboard">See the portfolio policies <span aria-hidden="true">↗</span></Link></div>
        </div>
        <div className="home-hero-foot"><span>500 STOCKS / 10 POSITIONS / 20-DAY HORIZON</span><a href="#research-system">SCROLL TO EXPLORE <span aria-hidden="true">↓</span></a><span>SIMULATED CAPITAL / NO LIVE ORDERS</span></div>
      </section>

      <section className="home-thesis site-container" id="research-system">
        <div className="home-section-index"><span>01 / THE RESEARCH SYSTEM</span><span>MODEL RELEASE {release.release.version.toUpperCase()}</span></div>
        <div className="home-thesis-layout"><h2>Every call leaves<br />a <em>paper trail.</em></h2><div><p>Salarium ranks a broad US stock universe, builds a concentrated portfolio, and applies explicit risk limits. Each decision can be checked against the data and rules available at the time.</p><Link href="/methodology">Read how the model works <span aria-hidden="true">↗</span></Link></div></div>
        <div className="home-metrics-rail"><div><strong>500</strong><span>LIQUID STOCKS<br />IN THE RESEARCH UNIVERSE</span></div><div><strong>10</strong><span>POSITIONS<br />IN THE CORE POLICY</span></div><div><strong>20<span>D</span></strong><span>RANKING HORIZON<br />HELD FIXED BETWEEN RELEASES</span></div><div><strong>0</strong><span>LIVE TRADES<br />PAPER CAPITAL ONLY</span></div></div>
      </section>

      <section className="home-ledger site-container">
        <div className="home-section-index"><span>02 / HOW A DECISION EARNS ITS PLACE</span><span>RULES BEFORE STORIES</span></div>
        <div className="home-ledger-grid">
          <article><span>01 — RANK</span><h3>Start with the full list.</h3><p>The frozen 20-day model scores the eligible universe. A high score is a relative ranking, not a price target.</p></article>
          <article><span>02 — SIZE</span><h3>Budget for the whole book.</h3><p>Position weights reflect return forecasts, covariance, liquidity, and portfolio-level risk controls.</p></article>
          <article><span>03 — CHALLENGE</span><h3>Keep the losing case.</h3><p>New sleeves face the same dates, costs, and risk limits. The oil hedge remains experimental after failing its out-of-sample test.</p><Link href="/research/courtroom">Read the oil decision <span aria-hidden="true">↗</span></Link></article>
        </div>
      </section>

      <section className="home-history site-container">
        <div className="home-section-index"><span>03 / HISTORICAL EVIDENCE</span><span>{account.period.start} — {account.period.end}</span></div>
        <div className="home-history-heading"><div><h2>Tested on dates<br />the model had not seen.</h2><p>Walk-forward simulation. Transaction costs included where stated. Historical results are not live performance.</p></div><Link href="/research/performance">Full results and assumptions <span aria-hidden="true">↗</span></Link></div>
        <div className="home-history-stats"><div><span>ANNUALIZED NET RETURN</span><strong>{percent(account.statistics.annualized_net_return)}</strong></div><div><span>MAXIMUM DRAWDOWN</span><strong>{percent(account.statistics.max_drawdown)}</strong></div><div><span>OUT-OF-SAMPLE REBALANCES</span><strong>{release.results.core_balanced.num_rebalances}</strong></div><div><span>BENCHMARK</span><strong>SPY / TOTAL-RETURN PROXY</strong></div></div>
        <div className="home-chart-frame"><HistoricalAccountChart snapshot={account} /></div>
        <p className="home-chart-note">Both curves start at $100,000. Salarium results include modeled trading costs; taxes, market capacity, additional impact, and benchmark entry costs are excluded.</p>
      </section>

      <section className="home-casefiles site-container">
        <div className="home-section-index"><span>04 / OPEN CASE FILES</span><Link href="/research">ALL RESEARCH ↗</Link></div>
        <div className="home-case-grid">
          <Link href="/replay"><span>DECISION REPLAY / 01</span><h2>Rewind a rebalance.</h2><p>See the rankings, holdings, and constraints available on a past date.</p><b>Open the archive ↗</b></Link>
          <Link href="/dependencies"><span>PORTFOLIO RISK / 02</span><h2>Find the shared exposure.</h2><p>Trace measured factors and documented business links across holdings.</p><b>Open the dependency map ↗</b></Link>
          <Link href="/research/experiments"><span>EXPERIMENT LOG / 03</span><h2>Read what did not work.</h2><p>Accepted and rejected tests stay in the same record as their results.</p><b>Browse the experiments ↗</b></Link>
        </div>
      </section>

      <section className="home-portfolios site-container" id="portfolios">
        <div className="home-section-index"><span>05 / FORWARD PAPER ACCOUNTS</span><span>COMMON START DATE / INDEPENDENT RULES</span></div>
        <div className="home-portfolio-heading"><div><h2>Four policies.<br /><em>One live paper record.</em></h2><p>Each account follows its own published rules. No broker connection and no live orders.</p></div><Link href="/dashboard">Compare all four <span aria-hidden="true">↗</span></Link></div>
        <div className="home-portfolio-grid">{comparison.portfolios.map((portfolio) => <Link className="home-portfolio-card" href="/dashboard" key={portfolio.key}><span>{portfolio.name}{portfolio.experimental ? " / EXPERIMENTAL" : ""}</span><strong>{money(portfolio.observations.at(-1)?.nav ?? comparison.starting_capital)}</strong><small>{portfolio.observations.length ? `Paper NAV · ${formatDate(portfolio.observations.at(-1)!.date)}` : "Opening capital · awaiting first completed signal"}</small><b>View policy and holdings ↗</b></Link>)}</div>
      </section>

      <footer className="home-endnote site-container"><EdgeGlyph className="home-end-mark" /><div><span>THE RECORD IS OPEN</span><p>Source code, model specification, decision archive, and evidence bundle.</p></div><Link href="/api/evidence-bundle" download>Download the research bundle ↗</Link></footer>
    </main>
  );
}
