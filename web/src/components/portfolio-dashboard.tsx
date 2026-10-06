"use client";
import Link from "next/link";
import { useState } from "react";
import type { PaperPortfolios } from "@/lib/paper-portfolios";
import { dependencyGroups } from "@/lib/dependencies";
import { percent } from "@/lib/format";
const money = (n: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(n);
const colors = ["#8dfcc9", "#91b9ff", "#d1b0ff", "#ffc17e"];
export default function PortfolioDashboard({
  data,
}: {
  data: PaperPortfolios;
}) {
  const [key, setKey] = useState("core"),
    [view, setView] = useState("holdings"),
    [date, setDate] = useState("latest");
  const account =
    data.portfolios.find((p) => p.key === key) ?? data.portfolios[0];
  const latest = account.observations.at(-1);
  const record =
    date === "latest"
      ? latest
      : account.observations.find((o) => o.date === date);
  const allValues = [
    data.starting_capital,
    ...data.portfolios.flatMap((p) => p.observations.map((o) => o.nav)),
    ...data.benchmark.map((o) => o.nav),
  ];
  const low = Math.min(...allValues) * 0.995,
    high = Math.max(...allValues) * 1.005;
  const dates = Array.from(
    new Set(data.portfolios.flatMap((p) => p.observations.map((o) => o.date))),
  ).sort();
  const x = (d: string) =>
    70 + (dates.indexOf(d) / Math.max(1, dates.length - 1)) * 760;
  const y = (n: number) => 260 - ((n - low) / (high - low)) * 210;
  return (
    <div className="portfolio-dashboard">
      <div className="record-banner">
        <span>
          {data.signal_date
            ? `MARKET CLOSE / ${data.signal_date}`
            : "AWAITING FIRST ELIGIBLE CLOSE"}
        </span>
        <span>$100,000 PER ACCOUNT · PAPER ONLY</span>
      </div>
      <p className="research-muted">{data.message}</p>
      <div className="portfolio-account-grid">
        {data.portfolios.map((p, i) => {
          const last = p.observations.at(-1);
          return (
            <button
              className={`portfolio-account ${key === p.key ? "selected" : ""}`}
              style={{ borderTopColor: colors[i] }}
              key={p.key}
              type="button"
              aria-pressed={key === p.key}
              onClick={() => {
                setKey(p.key);
                setDate("latest");
              }}
            >
              <span>
                {p.name}
                {p.experimental ? " / EXPERIMENTAL" : ""}
              </span>
              <strong>{money(last?.nav ?? data.starting_capital)}</strong>
              <small>
                {last
                  ? `${percent(last.return)} return · ${percent(p.maximum_drawdown)} max drawdown`
                  : "Starting capital · no performance record yet"}
              </small>
              <small>
                {last
                  ? `${p.observations.length} close observations`
                  : "Launch pending"}
              </small>
            </button>
          );
        })}
      </div>
      <section className="research-panel">
          <h2>Same start date. Same market closes.</h2>
        {dates.length > 0 ? (
          <>
            <div className="portfolio-chart-scroll">
              <svg
                className="portfolio-comparison"
                viewBox="0 0 900 300"
                role="img"
                aria-label="Paper NAV comparison in US dollars"
              >
                <text x="10" y="24" fill="#a7b6cb" fontSize="15">
                  NAV / USD
                </text>
                {[low, (low + high) / 2, high].map((n) => (
                  <g key={n}>
                    <line
                      x1="70"
                      x2="830"
                      y1={y(n)}
                      y2={y(n)}
                      stroke="#28354a"
                    />
                    <text x="5" y={y(n) + 4} fill="#a7b6cb" fontSize="15">
                      {Math.round(n).toLocaleString()}
                    </text>
                  </g>
                ))}
                {data.portfolios.map((p, i) => (
                  <g key={p.key}>
                    <path
                      d={p.observations
                        .map(
                          (o, j) => `${j ? "L" : "M"}${x(o.date)},${y(o.nav)}`,
                        )
                        .join(" ")}
                      fill="none"
                      stroke={colors[i]}
                      strokeWidth="2.5"
                    />
                    {p.observations.length === 1 && (
                      <circle
                        cx={x(p.observations[0].date)}
                        cy={y(p.observations[0].nav)}
                        r="5"
                        fill={colors[i]}
                      />
                    )}
                  </g>
                ))}
                <path
                  d={data.benchmark
                    .map((o, j) => `${j ? "L" : "M"}${x(o.date)},${y(o.nav)}`)
                    .join(" ")}
                  fill="none"
                  stroke="#b7b9c1"
                  strokeWidth="1.5"
                  strokeDasharray="5 5"
                />
                <text x="70" y="288" fill="#a7b6cb" fontSize="15">
                  {dates[0]}
                </text>
                <text
                  x="830"
                  y="288"
                  textAnchor="end"
                  fill="#a7b6cb"
                  fontSize="15"
                >
                  {dates.at(-1)}
                </text>
              </svg>
            </div>
            <div className="chart-legend">
              {data.portfolios.map((p, i) => (
                <span key={p.key}>
                  <i style={{ background: colors[i] }} />
                  {p.name}
                </span>
              ))}
              <span>
                <i style={{ background: "#b7b9c1" }} />
                SPY
              </span>
            </div>
          </>
        ) : (
          <p>
            No curve is drawn until the first eligible close. Starting balances
            are not measured returns.
          </p>
        )}
        <p className="research-muted">
          Independent holdings and ledgers, shared close dates and
          transaction-cost rules. SPY starts on the same date with the same
          initial 10 bp purchase cost. Returns include modeled costs; taxes,
          capacity and additional impact are excluded.
        </p>
      </section>
      <section aria-live="polite">
        <div className="section-heading">
          <div>
            <p className="eyebrow">SELECTED ACCOUNT</p>
            <h2>{account.name}</h2>
            <p className="research-muted">{account.description}</p>
          </div>
          <Link href="/research/courtroom">Oil sleeve research ↗</Link>
        </div>
        <div
          className="dependency-tabs"
          role="group"
          aria-label="Portfolio detail"
        >
          {[
            "holdings",
            "attribution",
            "dependencies",
            "replay",
            "evidence",
          ].map((v) => (
            <button
              type="button"
              key={v}
              aria-pressed={view === v}
              onClick={() => setView(v)}
            >
              {v[0].toUpperCase() + v.slice(1)}
            </button>
          ))}
        </div>
        {!record ? (
          <div className="research-panel">
            <h2>Ready for the first close</h2>
            <p>
              This account has no positions or outcomes yet. All four policies
              launch together after the configured start boundary.
            </p>
            <Link href="/portfolio">Earlier drawdown-control record ↗</Link>
          </div>
        ) : (
          <>
            {view === "replay" && (
              <div className="replay-controls">
                <label>
                  Recorded close
                  <select
                    value={date}
                    onChange={(e) => setDate(e.target.value)}
                  >
                    <option value="latest">Latest close</option>
                    {account.observations.map((o) => (
                      <option key={o.date}>{o.date}</option>
                    ))}
                  </select>
                </label>
                <span className="research-muted">
                  Only the selected record is shown; later outcomes are
                  excluded.
                </span>
              </div>
            )}
            {(view === "holdings" || view === "replay") && (
              <>
                <div className="record-banner">
                  <span>
                    {record.date} /{" "}
                    {record.rebalance ? "REBALANCE" : "MARK ONLY"}
                  </span>
                  <span>NAV {money(record.nav)}</span>
                </div>
                <div className="research-table-wrap">
                  <table className="research-table">
                    <caption>Recorded positions</caption>
                    <thead>
                      <tr>
                        <th>Asset</th>
                        <th>Shares</th>
                        <th>Close</th>
                        <th>Value</th>
                        <th>Weight</th>
                      </tr>
                    </thead>
                    <tbody>
                      {record.holdings.map((h) => (
                        <tr key={h.ticker}>
                          <td>{h.ticker}</td>
                          <td>{h.shares.toFixed(4)}</td>
                          <td>{money(h.price)}</td>
                          <td>{money(h.value)}</td>
                          <td>{percent(h.weight)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {view === "replay" && (
                  <div className="research-panel">
                    <p>
                      Recorded at {record.recorded_at}. Modeled cost{" "}
                      {money(record.cost)}.
                    </p>
                    <p className="hash-text">
                      Source SHA-256: {record.source_sha256}
                    </p>
                    {record.rankings && (
                      <details>
                        <summary>Rankings recorded at this rebalance</summary>
                        {record.rankings.map((r) => (
                          <p key={r.ticker}>
                            {r.rank} · {r.ticker} · {r.score.toFixed(6)}
                          </p>
                        ))}
                      </details>
                    )}
                  </div>
                )}
              </>
            )}
            {view === "attribution" && (
              <div className="research-grid">
                {(["equity", "oil", "cash", "cost"] as const).map(
                  (category) => (
                    <article className="research-panel" key={category}>
                      <p className="eyebrow">
                        {category === "cost"
                          ? "MODELED COSTS"
                          : `${category.toUpperCase()} CONTRIBUTION`}
                      </p>
                      <h2>
                        {money(
                          account.observations.reduce(
                            (n, o) => n + o.attribution[category],
                            0,
                          ),
                        )}
                      </h2>
                      <p>Cumulative dollars since account launch.</p>
                    </article>
                  ),
                )}
                <p className="research-muted">
                  Equity + oil + cash + costs reconcile to the change from
                  $100,000. Cash denotes the BIL position, not idle cash.
                </p>
                <p className="research-muted">
                  Current underwater run: {account.days_underwater}{" "}
                  observations. Longest: {account.maximum_days_underwater}.
                  These are close observations, not a recovery-time forecast.
                </p>
              </div>
            )}
            {view === "dependencies" && (
              <div className="research-grid">
                {dependencyGroups.map((g) => (
                  <article className="research-panel" key={g.id}>
                    <p className="eyebrow">QUALITATIVE BUSINESS THEME</p>
                    <h2>{g.label}</h2>
                    <strong>
                      {percent(
                        record.holdings
                          .filter((h) =>
                            g.members.some((m) => m.ticker === h.ticker),
                          )
                          .reduce((n, h) => n + h.weight, 0),
                      )}{" "}
                      tagged allocation
                    </strong>
                    <p>{g.thesis}</p>
                    {g.members
                      .filter((m) =>
                        record.holdings.some((h) => h.ticker === m.ticker),
                      )
                      .map((m) => (
                        <p key={m.ticker}>
                          <a href={m.url} target="_blank" rel="noreferrer">
                            {m.ticker} / company source ↗
                          </a>
                        </p>
                      ))}
                  </article>
                ))}
                <p className="research-muted">
                  Themes overlap. Untagged holdings are unreviewed, not
                  independent. USO adds direct oil-proxy exposure; it is not a
                  measured hedge for these business themes.
                </p>
              </div>
            )}
            {view === "evidence" && (
              <article className="research-panel">
                <h2>Account evidence</h2>
                <p>
                  Close {record.date} · launch {account.launch_date} · last
                  rebalance {account.last_rebalance_date}
                </p>
                <p>
                  NAV = sum of shares × adjusted close. Return = NAV / $100,000
                  − 1. Drawdown = NAV / running high-water mark − 1. Every
                  executed paper allocation pays 10 bp on absolute dollars
                  bought and sold, including BIL and USO.
                </p>
                <p className="hash-text">
                  Configuration SHA-256: {data.config_sha256}
                  <br />
                  Signal source SHA-256: {record.source_sha256}
                </p>
                <p>
                  Source generated {data.generated_at}. No live execution,
                  taxes, or additional market impact.
                </p>
                <a
                  className="research-link"
                  href="/api/evidence-bundle"
                  download
                >
                  Download account ledger and evidence ↓
                </a>
              </article>
            )}
          </>
        )}
      </section>
    </div>
  );
}
