"use client";

import { useMemo, useState } from "react";

import { SearchIcon } from "@/components/icons";
import { humanize, percent } from "@/lib/format";
import type { Ranking } from "@/lib/site-types";

const FILTERS = ["all", "risk_on", "neutral", "risk_off"] as const;
type Filter = (typeof FILTERS)[number];
type SortMode = "rank" | "score" | "volatility_low" | "volatility_high";

export default function RankingExplorer({ rankings }: { rankings: Ranking[] }) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [sortMode, setSortMode] = useState<SortMode>("rank");

  const visible = useMemo(() => {
    const normalized = query.trim().toUpperCase();
    const rows = rankings
      .filter((item) => !normalized || item.ticker.toUpperCase().includes(normalized))
      .filter((item) => filter === "all" || item.risk_state === filter);

    return [...rows].sort((a, b) => {
      if (sortMode === "score") return b.score - a.score;
      if (sortMode === "volatility_low") return a.volatility_20d - b.volatility_20d;
      if (sortMode === "volatility_high") return b.volatility_20d - a.volatility_20d;
      return a.rank - b.rank;
    });
  }, [filter, query, rankings, sortMode]);

  const maxScore = rankings.length ? Math.max(...rankings.map((item) => item.score)) : 1;
  const minScore = rankings.length ? Math.min(...rankings.map((item) => item.score)) : 0;

  return (
    <div className="card overflow-hidden">
      <div className="grid gap-4 border-b border-white/10 p-5 lg:grid-cols-[1fr_auto_auto] lg:items-center">
        <label className="search-field">
          <SearchIcon className="h-4 w-4 text-white/30" />
          <span className="sr-only">Search ticker</span>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search ticker"
            className="min-w-0 flex-1 bg-transparent text-sm text-white outline-none placeholder:text-white/25"
          />
        </label>

        <div className="flex flex-wrap gap-2" aria-label="Risk-state filters">
          {FILTERS.map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => setFilter(value)}
              className={`filter-button ${filter === value ? "filter-button-active" : ""}`}
            >
              {value === "all" ? "All states" : humanize(value)}
            </button>
          ))}
        </div>

        <label className="select-field">
          <span className="sr-only">Sort rankings</span>
          <select value={sortMode} onChange={(event) => setSortMode(event.target.value as SortMode)}>
            <option value="rank">Original rank</option>
            <option value="score">Score: high to low</option>
            <option value="volatility_low">Volatility: low to high</option>
            <option value="volatility_high">Volatility: high to low</option>
          </select>
        </label>
      </div>

      <div className="flex items-center justify-between border-b border-white/8 px-5 py-3 font-mono text-[10px] tracking-[0.12em] text-white/25" aria-live="polite">
        <span>{visible.length} OF {rankings.length} SECURITIES</span>
        <span>COMMITTED SNAPSHOT · NOT LIVE</span>
      </div>

      <div className="hidden min-w-[760px] grid-cols-[72px_1fr_150px_150px_180px] border-b border-white/10 px-5 py-3 text-[9px] tracking-[0.18em] text-white/25 md:grid">
        <span>RANK</span><span>SECURITY</span><span>MODEL SCORE</span><span>20D VOLATILITY</span><span>RISK STATE</span>
      </div>

      <div className="divide-y divide-white/6">
        {visible.map((item) => {
          const denominator = maxScore - minScore || 1;
          const scoreWidth = Math.max(4, ((item.score - minScore) / denominator) * 100);
          return (
            <details key={item.ticker} className="group ranking-row">
              <summary className="list-none cursor-pointer px-5 py-5">
                <div className="grid gap-4 md:grid-cols-[72px_1fr_150px_150px_180px] md:items-center">
                  <span className="font-mono text-sm text-white/25">{String(item.rank).padStart(2, "0")}</span>
                  <div>
                    <div className="flex items-center gap-3">
                      <span className="text-base font-semibold tracking-[0.16em] text-white">{item.ticker}</span>
                      <span className="text-[9px] tracking-[0.14em] text-white/20 group-open:text-emerald-300">DETAILS +</span>
                    </div>
                    <p className="mt-1 text-xs text-white/30">{humanize(item.model_configuration)}</p>
                  </div>
                  <div>
                    <p className="font-mono text-sm text-emerald-300">{item.score.toFixed(6)}</p>
                    <div className="mt-2 h-px w-full bg-white/8"><div className="h-px bg-emerald-300" style={{ width: `${scoreWidth}%` }} /></div>
                  </div>
                  <div className="font-mono text-sm text-white/65">{percent(item.volatility_20d, 2)}</div>
                  <div className="flex items-center gap-3">
                    <span className={`status-pill ${item.risk_state === "risk_off" ? "status-pill-risk" : "status-pill-positive"}`}>{humanize(item.risk_state)}</span>
                    <span className="text-[9px] text-white/25">{item.regime_is_confident ? "CONFIDENT" : "LOW CONF."}</span>
                  </div>
                </div>
              </summary>
              <div className="grid gap-4 border-t border-white/6 bg-white/[0.015] px-5 py-5 text-sm leading-6 text-white/42 md:grid-cols-3">
                <div><p className="detail-label">WHAT THE SCORE MEANS</p><p className="mt-2">A higher score indicates stronger relative model conviction inside this committed cross-section. This name sits at the {percent(item.score_percentile, 1)} score percentile. It is not a price target or expected return guarantee.</p></div>
                <div><p className="detail-label">RISK CONTEXT</p><p className="mt-2">The displayed volatility is a recent 20-day estimate. Portfolio risk is later evaluated jointly through the covariance engine.</p></div>
                <div><p className="detail-label">PORTFOLIO STATUS</p><p className="mt-2">A high ranking does not automatically become a holding. Buffer, covariance, signal-weight and exposure rules are applied afterward.</p></div>
              </div>
            </details>
          );
        })}

        {visible.length === 0 && (
          <div className="px-6 py-16 text-center">
            <p className="text-sm text-white/50">No securities match the current filters.</p>
            <button type="button" className="button-secondary mt-5" onClick={() => { setQuery(""); setFilter("all"); setSortMode("rank"); }}>Reset filters</button>
          </div>
        )}
      </div>
    </div>
  );
}
