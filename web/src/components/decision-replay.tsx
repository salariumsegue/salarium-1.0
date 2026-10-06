"use client";
import { useState } from "react";
import type { DecisionArchive } from "@/lib/evidence";
import { percent } from "@/lib/format";
const money = (x: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(x);
export default function DecisionReplay({
  archive,
}: {
  archive: DecisionArchive;
}) {
  const [index, setIndex] = useState(archive.entries.length - 1);
  const [hindsight, setHindsight] = useState(false);
  const entry = archive.entries[index],
    s = entry.snapshot,
    p = s.forward_portfolio;
  const next = archive.entries[index + 1];
  return (
    <div className="replay-workspace">
      <div className="replay-controls">
        <label>
          Recorded rebalance
          <select
            value={index}
            onChange={(e) => {
              setIndex(Number(e.target.value));
              setHindsight(false);
            }}
          >
            {archive.entries.map((e, i) => (
              <option key={e.date} value={i}>
                {e.date}
              </option>
            ))}
          </select>
        </label>
        <label className="hindsight-toggle">
          <input
            type="checkbox"
            checked={hindsight}
            onChange={(e) => setHindsight(e.target.checked)}
          />{" "}
          Show subsequent outcome separately
        </label>
      </div>
      <div aria-live="polite">
        <div className="record-banner">
          <span>REBALANCE DATE / {entry.date}</span>
          <span>RECORDED / {entry.available_at}</span>
        </div>
        <p className="research-muted">
          This is the published record available at the recorded timestamp. A
          rebalance date is not proof that publication occurred that day.
          Original feature rows and the full covariance matrix are not included
          in this archive.
        </p>
        <div className="research-grid">
          <article className="research-panel">
            <p className="eyebrow">01 / Inputs on record</p>
            <h2>{s.latest_signal_state.date}</h2>
            <p>
              Signal date · {s.data_quality.feature_rows} feature rows ·{" "}
              {percent(s.data_quality.feature_coverage)} coverage
            </p>
            <p>
              Frozen {s.architecture.model_horizon_days}D model. No automatic
              retraining.
            </p>
          </article>
          <article className="research-panel">
            <p className="eyebrow">02 / Portfolio decision</p>
            <h2>{percent(p.shadow_equity_exposure)} equity</h2>
            <p>
              {percent(p.cash_weight)} cash proxy ({p.cash_proxy}).{" "}
              {p.holdings.length} holdings.
            </p>
            <p>
              Baseline {percent(p.baseline_equity_exposure)}; controller cap{" "}
              {percent(p.controller.exposure_cap)}. Soft floor{" "}
              {money(p.controller.soft_floor_value)}.
            </p>
          </article>
        </div>
        <div className="research-table-wrap">
          <table className="research-table">
            <caption>Holdings recorded with this rebalance</caption>
            <thead>
              <tr>
                <th>Company</th>
                <th>Recorded rank</th>
                <th>Base weight</th>
                <th>Paper weight</th>
                <th>Reference price</th>
              </tr>
            </thead>
            <tbody>
              {p.holdings.map((h) => (
                <tr key={h.ticker}>
                  <td>
                    <b>{h.ticker}</b>
                    <small>{h.company_name}</small>
                  </td>
                  <td>{h.rank}</td>
                  <td>{percent(h.base_weight)}</td>
                  <td>{percent(h.paper_weight)}</td>
                  <td>{money(h.reference_price)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <details className="research-panel">
          <summary>Recorded rankings and provenance</summary>
          <div className="research-table-wrap">
            <table className="research-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Ticker</th>
                  <th>Score</th>
                </tr>
              </thead>
              <tbody>
                {s.latest_signal_state.rankings.map((r) => (
                  <tr key={r.ticker}>
                    <td>{r.rank}</td>
                    <td>{r.ticker}</td>
                    <td>{r.score.toFixed(6)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="hash-text">
            Publication commit:{" "}
            {entry.published_commit ?? "Recorded in the publication bundle"}
            <br />
            Snapshot SHA-256: {entry.snapshot_sha256}
            <br />
            Model SHA-256: {s.provenance.model_sha256}
          </p>
          {entry.published_commit && (
            <a
              href={`https://github.com/salariumsegue/salarium-1.0/blob/${entry.published_commit}/web/public/data/forward_paper_snapshot.json`}
              target="_blank"
              rel="noreferrer"
            >
              Open the original Git record ↗
            </a>
          )}
        </details>
        {hindsight && (
          <article className="hindsight-panel">
            <p className="eyebrow">
              HINDSIGHT / NOT AN INPUT TO THE SELECTED DECISION
            </p>
            <h2>
              {next
                ? `Next recorded rebalance: ${next.date}`
                : "No later rebalance in this archive"}
            </h2>
            {next?.ledger ? (
              <p>
                Next interval net return:{" "}
                {percent(Number(next.ledger.net_return))}. Ledger NAV:{" "}
                {money(Number(next.ledger.paper_nav_after))}. Recorded at{" "}
                {next.available_at}.
              </p>
            ) : (
              <p>
                No subsequent completed interval is available here. Current
                marks are not substituted for a missing outcome.
              </p>
            )}
          </article>
        )}
      </div>
      <p className="research-muted">
        {archive.coverage} No brokerage connection or live capital.
      </p>
    </div>
  );
}
