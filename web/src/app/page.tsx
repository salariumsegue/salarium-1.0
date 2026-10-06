import Link from "next/link";
import fs from "node:fs";
import path from "node:path";
import type { PaperPortfolios } from "@/lib/paper-portfolios";
import HistoricalAccountChart from "@/components/historical-account-chart";
import EvidencePassport from "@/components/evidence-passport";
import {
  loadForwardPaperSnapshot,
  loadHypotheticalAccountSnapshot,
  loadReleaseSnapshot,
} from "@/lib/site-data";
import { percent, formatDate } from "@/lib/format";
export default function HomePage() {
  const comparison = JSON.parse(
    fs.readFileSync(
      path.join(process.cwd(), "public/data/paper_portfolios.json"),
      "utf8",
    ),
  ) as PaperPortfolios;
  const release = loadReleaseSnapshot(),
    forward = loadForwardPaperSnapshot(),
    account = loadHypotheticalAccountSnapshot();
  const snapshot = forward.status === "available" ? forward.data : null,
    p = snapshot?.forward_portfolio;
  const money = (n: number) =>
    new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0,
    }).format(n);
  const common = {
    category: "Forward paper / indicative mark",
    source: "/data/forward_paper_snapshot.json",
    generated: snapshot?.generated_at_utc ?? "Unavailable",
    model: "Frozen 20D model / drawdown-budget paper control",
    commit: snapshot?.provenance.git_commit ?? "Unavailable",
    hash: snapshot?.provenance.model_sha256,
    exclusions:
      "Delayed research prices; no live execution. Soft floor cannot prevent gap losses. Indicative marks differ from completed rebalance NAV.",
  };
  return (
    <main id="main-content" className="site-main home-observatory">
      <section className="observatory-hero site-container">
        <div className="observatory-status">
          <span className="status-dot" /> FORWARD PAPER{" "}
          <span>
            {snapshot
              ? `SIGNALS / ${formatDate(snapshot.latest_signal_state.date)}`
              : "SNAPSHOT UNAVAILABLE"}
          </span>
          <span>NO LIVE ORDERS</span>
        </div>
        <div className="observatory-grid">
          <div>
            <p className="eyebrow">
              SALARIUM / INDEPENDENT QUANTITATIVE RESEARCH
            </p>
            <h1>
              A portfolio
              <br />
              with an
              <br />
              <em>open record.</em>
            </h1>
            <p className="observatory-copy">
              Five hundred stocks. Ten holdings. A frozen model whose decisions
              you can reopen, question, and follow as new evidence arrives.
            </p>
            <div className="observatory-actions">
              <Link href="/dashboard">Compare four portfolios ↗</Link>
              <Link href="/research/courtroom">Read the oil hedge case</Link>
            </div>
            <p className="research-muted">
              Built by Niall Gillen. Educational research using simulated
              capital and delayed market data.
            </p>
          </div>
          <aside className="signal-instrument">
            <div className="instrument-orbits" aria-hidden="true">
              <i />
              <i />
              <i />
            </div>
            <div className="instrument-center">
              <span>MODEL HORIZON</span>
              <strong>20D</strong>
              <span>FROZEN BETWEEN RELEASES</span>
            </div>
            <div className="instrument-label top">
              LIQUID-500 / EQUITY UNIVERSE
            </div>
            <div className="instrument-label bottom">
              TOP 10 / COVARIANCE-AWARE WEIGHTS
            </div>
          </aside>
        </div>
      </section>
      <section className="site-container paper-record">
        <div className="section-heading">
          <div>
            <p className="eyebrow">FOUR INDEPENDENT PAPER ACCOUNTS</p>
            <h2>Compare the portfolio policies.</h2>
          </div>
          <Link href="/dashboard">Open dashboard ↗</Link>
        </div>
        <div className="portfolio-account-grid">
          {comparison.portfolios.map((account) => (
            <Link
              className="portfolio-account"
              href="/dashboard"
              key={account.key}
            >
              <span>
                {account.name}
                {account.experimental ? " / EXPERIMENTAL" : ""}
              </span>
              <strong>
                {money(
                  account.observations.at(-1)?.nav ??
                    comparison.starting_capital,
                )}
              </strong>
              <small>
                {account.observations.length
                  ? "Forward paper NAV"
                  : "Starting capital · launch pending"}
              </small>
            </Link>
          ))}
        </div>
        <p className="research-muted">
          The four accounts share a common launch date. The
          earlier paper account below retains its separate history.
        </p>
      </section>
      <section className="site-container paper-record">
        <div className="section-heading">
          <div>
            <p className="eyebrow">THE FORWARD RECORD</p>
            <h2>The earlier paper account.</h2>
          </div>
          <Link href="/portfolio">Inspect holdings ↗</Link>
        </div>
        <div className="passport-grid">
          {p && (
            <>
              <EvidencePassport
                evidence={{
                  ...common,
                  label: "Indicative paper NAV",
                  value: money(p.indicative_nav),
                  calculation: `Published forward_portfolio.indicative_nav. Last completed rebalance NAV: ${money(p.last_completed_nav)}.`,
                }}
              />
              <EvidencePassport
                evidence={{
                  ...common,
                  label: "Current drawdown",
                  value: percent(p.current_drawdown),
                  calculation: `NAV / high-water mark − 1. ${p.indicative_nav.toFixed(2)} / ${p.high_water_mark.toFixed(2)} − 1.`,
                }}
              />
              <EvidencePassport
                evidence={{
                  ...common,
                  label: "Equity exposure",
                  value: percent(p.shadow_equity_exposure),
                  calculation:
                    "Sum of current holdings’ paper_weight. The remainder is allocated to the cash proxy.",
                }}
              />
            </>
          )}
          {!p && (
            <p>
              Forward paper snapshot unavailable. Historical returns are not
              substituted here.
            </p>
          )}
        </div>
      </section>
      <section className="site-container research-destinations">
        <Link href="/research/courtroom">
          <span>01 / MODEL COURTROOM</span>
          <h2>
            Why the oil hedge
            <br />
            was rejected.
          </h2>
          <p>The argument, the objection, and the test it failed.</p>
          <b>Open case ↗</b>
        </Link>
        <Link href="/replay">
          <span>02 / DECISION REPLAY</span>
          <h2>
            {p ? formatDate(p.last_rebalance_date) : "Recorded rebalance"}
            <br />
              See what the model knew.
          </h2>
          <p>Original rankings, recorded weights, and risk limits.</p>
          <b>View the archive ↗</b>
        </Link>
        <Link href="/dependencies">
          <span>03 / DEPENDENCY MAP</span>
          <h2>
            What these holdings
            <br />
            have in common.
          </h2>
          <p>Business themes, measured allocation, and gaps in coverage.</p>
          <b>Inspect relationships ↗</b>
        </Link>
      </section>
      <section className="site-container historical-evidence">
        <div className="section-heading">
          <div>
            <p className="eyebrow">
              HISTORICAL SIMULATION / {account.period.start} —{" "}
              {account.period.end}
            </p>
            <h2>What the historical test shows.</h2>
            <p className="research-muted">
              Historical model selection and simulated trading. Separate from
              the forward account above.
            </p>
          </div>
        </div>
        <div className="passport-grid">
          <EvidencePassport
            evidence={{
              label: "Annualized simulated net return",
              value: percent(account.statistics.annualized_net_return),
              category: "Historical simulation / out-of-sample research",
              source: "/data/hypothetical_account_snapshot.json",
              generated: release.generated_at_utc,
              model: account.model.base_policy,
              commit: release.provenance.git_commit,
              calculation:
                "product(1 + net_return) ** ((252 / 10) / 139) − 1. Full-precision returns are included in the research bundle. Chart values are rounded.",
              exclusions:
                "Model-selection bias, universe-selection risk, taxes, capacity limits, additional market impact, and live execution.",
            }}
          />
          <EvidencePassport
            evidence={{
              label: "Historical maximum drawdown",
              value: percent(account.statistics.max_drawdown),
              category: "Historical simulation / out-of-sample research",
              source: "/data/hypothetical_account_snapshot.json",
              generated: release.generated_at_utc,
              model: account.model.base_policy,
              commit: release.provenance.git_commit,
              calculation:
                "Minimum historical NAV / running NAV peak − 1, using the full-precision research stream.",
              exclusions:
                "Historical losses do not bound future losses. Rounded chart values can differ from underlying calculations.",
            }}
          />
        </div>
        <HistoricalAccountChart snapshot={account} />
        <p className="research-muted">
          Both curves begin at $100,000. SPY is an adjusted-close total-return
          proxy. Modeled Salarium transaction costs are included; taxes,
          capacity, additional impact, and the benchmark’s initial trade cost
          are excluded.
        </p>
        <Link className="research-link" href="/research/performance">
          Read the full performance record ↗
        </Link>
      </section>
      <section className="site-container research-closing">
        <h2>Inspect the work behind the website.</h2>
        <div>
          <Link href="/rankings">Equity rankings ↗</Link>
          <Link href="/methodology">Model specification ↗</Link>
          <Link href="/api/evidence-bundle" download>
            Download research bundle ↓
          </Link>
        </div>
      </section>
    </main>
  );
}
