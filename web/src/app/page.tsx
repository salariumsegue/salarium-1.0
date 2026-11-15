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
import { BUILD_TIME_MS, CONTACT_EMAIL, ISSUES_URL, LINKEDIN_URL } from "@/lib/site-config";

export default function HomePage() {
  const comparison = JSON.parse(
    fs.readFileSync(path.join(process.cwd(), "public/data/paper_portfolios.json"), "utf8"),
  ) as PaperPortfolios;
  const release = loadReleaseSnapshot();
  const account = loadHypotheticalAccountSnapshot();
  const money = (n: number) => new Intl.NumberFormat("en-US", {
    style: "currency", currency: "USD", maximumFractionDigits: 0,
  }).format(n);

  const core = release.results.core_balanced;
  const lastClose = comparison.signal_date;
  const recordedCloses = Math.max(...comparison.portfolios.map((portfolio) => portfolio.observations.length), 0);
  const costBps = comparison.transaction_cost_bps ?? 10;
  // Evaluated when the site is built, so the notice reflects the record at deploy time.
  const daysSinceClose = lastClose
    ? Math.floor((BUILD_TIME_MS - new Date(`${lastClose}T00:00:00Z`).getTime()) / 86_400_000)
    : 0;
  const recordPaused = daysSinceClose > 5;

  return (
    <main id="main-content" className="site-main home-vision">
      <section className="home-vision-hero" aria-labelledby="home-title">
        <div className="home-hero-grid" aria-hidden="true" />
        <div className="home-hero-meta"><span>STUDENT-BUILT STOCK RESEARCH</span><span>EST. 2024 / BLOOMINGTON, IN</span></div>
        <div className="home-hero-center">
          <div className="home-mark-field"><span className="home-mark-ring home-mark-ring-a" /><span className="home-mark-ring home-mark-ring-b" /><EdgeGlyph className="home-center-mark" /></div>
          <p className="home-hero-overline">SALARIUM / SYSTEMATIC EQUITY</p>
          <h1 id="home-title">An open stock model,<br /><em>tested in public.</em></h1>
          <p className="home-hero-deck">Salarium ranks 500 liquid US stocks, holds the top 10 in four paper portfolios, and publishes the rules, the results, and the tests that failed.</p>
          <div className="home-hero-actions"><Link href="/research">See the research <span aria-hidden="true">↘</span></Link><Link href="/dashboard">See the paper portfolios <span aria-hidden="true">↗</span></Link></div>
        </div>
        <div className="home-hero-foot"><span>500 STOCKS / 10 POSITIONS / 20-DAY HORIZON</span><a href="#research-system">SCROLL TO EXPLORE <span aria-hidden="true">↓</span></a><span>SIMULATED CAPITAL / NO LIVE ORDERS</span></div>
      </section>

      <section className="home-thesis site-container" id="research-system">
        <div className="home-section-index"><span>01 / WHAT IT DOES</span><span>MODEL RELEASE {release.release.version.toUpperCase()}</span></div>
        <div className="home-thesis-layout"><h2>Rank, size,<br /><em>limit risk.</em></h2><div><p>Salarium scores 500 liquid US stocks, puts the top 10 into a portfolio, and scales exposure down when portfolio risk is high. Every rebalance is saved with the rankings and rules that produced it.</p><Link href="/methodology">Read how the model works <span aria-hidden="true">↗</span></Link></div></div>
        <div className="home-metrics-rail"><div><strong>500</strong><span>LIQUID STOCKS<br />IN THE RESEARCH UNIVERSE</span></div><div><strong>10</strong><span>POSITIONS<br />IN THE CORE POLICY</span></div><div><strong>20<span>D</span></strong><span>RANKING HORIZON<br />HELD FIXED BETWEEN RELEASES</span></div><div><strong>0</strong><span>LIVE TRADES<br />PAPER CAPITAL ONLY</span></div></div>
      </section>

      <section className="home-ledger site-container">
        <div className="home-section-index"><span>02 / HOW A PORTFOLIO GETS BUILT</span><span>THREE STEPS</span></div>
        <div className="home-ledger-grid">
          <article><span>01 — RANK</span><h3>Score every stock.</h3><p>A fixed 20-day model scores all 500 stocks. A high score means a stock ranks well against the others. It is not a price target.</p></article>
          <article><span>02 — SIZE</span><h3>Size the positions.</h3><p>Weights depend on the model score, how the stocks move together, and an 18% cap on any single name.</p></article>
          <article><span>03 — TEST</span><h3>Hold new ideas to the same test.</h3><p>Any new idea runs on the same dates, costs, and risk limits. The oil hedge failed its recovery test and was not added. It still runs as an experimental paper account, so there is a forward record of it next to Core.</p><Link href="/research/courtroom">Read the oil decision <span aria-hidden="true">↗</span></Link></article>
        </div>
      </section>

      <section className="home-history site-container">
        <div className="home-section-index"><span>03 / HISTORICAL EVIDENCE</span><span>{account.period.start} — {account.period.end}</span></div>
        <div className="home-history-heading"><div><h2>Tested on dates<br />the model had not seen.</h2><p>This is a walk-forward simulation with modeled trading costs. It is not live performance.</p></div><Link href="/research/performance">Full results and assumptions <span aria-hidden="true">↗</span></Link></div>
        <div className="home-history-stats"><div><span>ANNUALIZED NET RETURN</span><strong>{percent(account.statistics.annualized_net_return)}</strong></div><div><span>MAXIMUM DRAWDOWN</span><strong>{percent(account.statistics.max_drawdown)}</strong></div><div><span>ANNUALIZED VOLATILITY</span><strong>{percent(core.annualized_net_volatility)}</strong></div><div><span>NET SHARPE / SORTINO</span><strong>{account.statistics.net_sharpe.toFixed(2)} / {core.net_sortino.toFixed(2)}</strong></div><div><span>SPY MAX DRAWDOWN</span><strong>{percent(account.benchmark.statistics.max_drawdown)}</strong></div><div><span>OUT-OF-SAMPLE REBALANCES</span><strong>{core.num_rebalances}</strong></div></div>
        <p className="home-risk-note"><b>Read the drawdown first.</b> The simulated account lost {percent(Math.abs(account.statistics.max_drawdown))} from peak to trough at its worst, with {percent(core.annualized_net_volatility)} annualized volatility. The return came with that risk, in a ten-stock portfolio over one {account.period.start.slice(0, 4)}–{account.period.end.slice(0, 4)} window. Benchmark: SPY total-return proxy.</p>
        <div className="home-chart-frame"><HistoricalAccountChart snapshot={account} /></div>
        <p className="home-chart-note">Both curves start at $100,000. Salarium results include modeled trading costs; taxes, market capacity, additional impact, and benchmark entry costs are excluded.</p>
      </section>

      <section className="home-casefiles site-container">
        <div className="home-section-index"><span>04 / LOOK CLOSER</span><Link href="/research">ALL RESEARCH ↗</Link></div>
        <div className="home-case-grid">
          <Link href="/replay"><span>DECISION REPLAY / 01</span><h2>Replay a past rebalance.</h2><p>See the rankings, holdings, and limits the model had on that date.</p><b>Open the archive ↗</b></Link>
          <Link href="/dependencies"><span>PORTFOLIO RISK / 02</span><h2>See where holdings overlap.</h2><p>Holdings that depend on the same customers, suppliers, or trends, grouped by theme.</p><b>Open the dependency map ↗</b></Link>
          <Link href="/research/experiments"><span>EXPERIMENT LOG / 03</span><h2>Read what did not work.</h2><p>Every test is listed with its result, including the ones I rejected.</p><b>Browse the experiments ↗</b></Link>
        </div>
      </section>

      <section className="home-portfolios site-container" id="portfolios">
        <div className="home-section-index"><span>05 / FORWARD PAPER ACCOUNTS</span><span>COMMON START DATE / INDEPENDENT RULES</span></div>
        <div className="home-portfolio-heading"><div><h2>Four paper portfolios.<br /><em>Same start date.</em></h2><p>Each account follows its own published rules. There is no broker connection and no real money.</p></div><Link href="/dashboard">Compare all four <span aria-hidden="true">↗</span></Link></div>
        <p className="home-record-status" data-paused={recordPaused}>{recordedCloses <= 1 ? `All four accounts opened ${formatDate(comparison.launch_date ?? lastClose)} with ${money(comparison.starting_capital)} and paid the same ${costBps} bp entry cost, so they show the same opening value. The values will separate as more closes are recorded.` : `${recordedCloses} closes recorded since ${formatDate(comparison.launch_date ?? lastClose)}.`}{" "}Last recorded close: {formatDate(lastClose)}.{recordPaused ? ` Nothing has been recorded since then, and missed days are not filled in afterward.` : ""}</p>
        <div className="home-portfolio-grid">{comparison.portfolios.map((portfolio) => <Link className="home-portfolio-card" href="/dashboard" key={portfolio.key}><span>{portfolio.name}{portfolio.experimental ? " / EXPERIMENTAL" : ""}</span><strong>{money(portfolio.observations.at(-1)?.nav ?? comparison.starting_capital)}</strong><small>{portfolio.observations.length > 1 ? `Paper NAV · ${formatDate(portfolio.observations.at(-1)!.date)} · ${portfolio.observations.length} recorded closes` : portfolio.observations.length === 1 ? `Opening NAV · ${formatDate(portfolio.observations[0].date)} · ${money(comparison.starting_capital)} less ${costBps} bp entry cost` : "Opening capital · awaiting first completed signal"}</small>{portfolio.experimental && <small>Not added to the model. Tracked to see how the rejected oil idea does going forward.</small>}<b>View policy and holdings ↗</b></Link>)}</div>
      </section>

      <footer className="home-endnote site-container"><EdgeGlyph className="home-end-mark" /><div><span>DOWNLOAD EVERYTHING</span><p>Source code, model card, saved rebalances, and the data behind each result.</p></div><Link href="/api/evidence-bundle" download>Download the research bundle ↗</Link></footer>

      <section className="home-contact site-container" id="contact" aria-labelledby="contact-title">
        <div className="home-section-index"><span>06 / CONTACT</span><span>QUESTIONS AND CORRECTIONS</span></div>
        <div className="home-contact-layout"><h2 id="contact-title">Questions or<br />corrections?</h2><div><p>I&apos;m Niall Gillen, a finance student at Indiana University&apos;s Kelley School of Business. I built Salarium and I maintain it. If something looks wrong or you want to talk through the method, send me a message.</p><div className="home-hero-actions">{CONTACT_EMAIL && <a href={`mailto:${CONTACT_EMAIL}`}>Email {CONTACT_EMAIL} <span aria-hidden="true">↗</span></a>}<a href={LINKEDIN_URL} target="_blank" rel="noreferrer">Message on LinkedIn <span aria-hidden="true">↗</span></a><a href={ISSUES_URL} target="_blank" rel="noreferrer">Open a GitHub issue <span aria-hidden="true">↗</span></a></div></div></div>
      </section>
    </main>
  );
}
