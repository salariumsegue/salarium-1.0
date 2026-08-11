"use client";

import { useMemo, useState } from "react";

import { SearchIcon } from "@/components/icons";
import { humanize, money, number, percent } from "@/lib/format";
import type { Candidate } from "@/lib/site-types";

const FILTERS = ["all", "primary", "internal", "flagged"] as const;
type Filter = (typeof FILTERS)[number];
type SortMode = "rank" | "agentic" | "confidence" | "risk";

export default function CandidateExplorer({ candidates }: { candidates: Candidate[] }) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [sortMode, setSortMode] = useState<SortMode>("rank");

  const visible = useMemo(() => {
    const normalized = query.trim().toUpperCase();
    const rows = candidates.filter((candidate) => {
      const matchesQuery = !normalized || candidate.ticker.toUpperCase().includes(normalized) || (candidate.company_name ?? "").toUpperCase().includes(normalized);
      const matchesFilter = filter === "all"
        || (filter === "primary" && candidate.primary_evidence_supported)
        || (filter === "internal" && !candidate.primary_evidence_supported)
        || (filter === "flagged" && candidate.red_flag_count > 0);
      return matchesQuery && matchesFilter;
    });

    return [...rows].sort((a, b) => {
      if (sortMode === "agentic") return (b.scores.agentic ?? -Infinity) - (a.scores.agentic ?? -Infinity);
      if (sortMode === "confidence") return (b.scores.confidence ?? -Infinity) - (a.scores.confidence ?? -Infinity);
      if (sortMode === "risk") return (b.scores.risk ?? -Infinity) - (a.scores.risk ?? -Infinity);
      return a.rank - b.rank;
    });
  }, [candidates, filter, query, sortMode]);

  return (
    <div className="card overflow-hidden">
      <div className="grid gap-4 border-b border-white/10 p-5 lg:grid-cols-[1fr_auto_auto] lg:items-center">
        <label className="search-field">
          <SearchIcon className="h-4 w-4 text-white/30" />
          <span className="sr-only">Search candidate</span>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search ticker or company"
            className="min-w-0 flex-1 bg-transparent text-sm text-white outline-none placeholder:text-white/25"
          />
        </label>
        <div className="flex flex-wrap gap-2" aria-label="Evidence filters">
          {FILTERS.map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => setFilter(value)}
              className={`filter-button ${filter === value ? "filter-button-active" : ""}`}
            >
              {value === "all" ? "All candidates" : humanize(value)}
            </button>
          ))}
        </div>
        <label className="select-field">
          <span className="sr-only">Sort candidates</span>
          <select value={sortMode} onChange={(event) => setSortMode(event.target.value as SortMode)}>
            <option value="rank">Governed rank</option>
            <option value="agentic">Agentic score</option>
            <option value="confidence">Confidence</option>
            <option value="risk">Risk assessment</option>
          </select>
        </label>
      </div>

      <div className="flex items-center justify-between border-b border-white/8 px-5 py-3 font-mono text-[10px] tracking-[0.12em] text-white/25" aria-live="polite">
        <span>{visible.length} OF {candidates.length} CANDIDATES</span>
        <span>EXPAND ANY NAME FOR THE FULL RESEARCH PACKET</span>
      </div>

      <div className="divide-y divide-white/6">
        {visible.map((candidate) => (
          <details key={candidate.ticker} className="group candidate-row">
            <summary className="list-none cursor-pointer px-5 py-5">
              <div className="grid gap-5 md:grid-cols-[60px_1.25fr_160px_120px_120px] md:items-center">
                <span className="font-mono text-sm text-white/25">{String(candidate.rank).padStart(2, "0")}</span>
                <div>
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="text-base font-semibold tracking-[0.14em]">{candidate.ticker}</span>
                    <span className={candidate.primary_evidence_supported ? "status-pill status-pill-positive" : "status-pill"}>
                      {candidate.primary_evidence_supported ? "Primary supported" : "Internal only"}
                    </span>
                    {candidate.red_flag_count > 0 && <span className="status-pill status-pill-risk">{candidate.red_flag_count} flag</span>}
                  </div>
                  <p className="mt-2 truncate text-xs text-white/32">{candidate.company_name ?? "Research candidate"}</p>
                </div>
                <Metric label="AGENTIC" value={number(candidate.scores.agentic ?? 0)} positive />
                <Metric label="CONFIDENCE" value={percent(candidate.scores.confidence ?? 0)} />
                <div className="flex items-center justify-between gap-4 md:justify-end">
                  <Metric label="EVIDENCE" value={String(candidate.evidence_count)} />
                  <span className="text-lg text-white/25 transition group-open:rotate-45 group-open:text-emerald-300">+</span>
                </div>
              </div>
            </summary>

            <div className="border-t border-white/8 bg-white/[0.015] p-5 sm:p-7">
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <Fact label="LAST PRICE" value={money(candidate.last_price)} />
                <Fact label="MEDIAN DOLLAR VOLUME" value={money(candidate.median_dollar_volume)} />
                <Fact label="DRAWDOWN RESILIENCE" value={percent(candidate.drawdown_resilience ?? 0)} />
                <Fact label="MODEL UNCERTAINTY" value={candidate.model_uncertainty?.toFixed(5) ?? "—"} />
              </div>

              <div className="mt-6 grid gap-5 lg:grid-cols-3">
                <ResearchBlock label="THESIS" text={candidate.thesis ?? "No thesis text was available in the committed packet."} />
                <ResearchBlock label="RISK REVIEW" text={candidate.risk_summary ?? "No risk summary was available in the committed packet."} risk />
                <ResearchBlock label="CATALYST REVIEW" text={candidate.catalyst_summary ?? "No catalyst summary was available in the committed packet."} />
              </div>

              <div className="mt-6 grid gap-5 lg:grid-cols-[1.1fr_1fr]">
                <div>
                  <p className="detail-label">SCORE STACK</p>
                  <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
                    <Score label="Quant" value={candidate.scores.quantitative} />
                    <Score label="Model" value={candidate.scores.model} decimals={5} />
                    <Score label="Fundamental" value={candidate.scores.fundamental} />
                    <Score label="Macro fit" value={candidate.scores.macro_fit} />
                    <Score label="Risk" value={candidate.scores.risk} />
                    <Score label="Evidence" value={candidate.scores.evidence} />
                    <Score label="Catalyst" value={candidate.scores.catalyst} />
                    <Score label="Confidence" value={candidate.scores.confidence} />
                  </div>
                </div>
                <div>
                  <p className="detail-label">GOVERNED SOURCE TYPES</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {candidate.source_types.length > 0 ? candidate.source_types.map((source) => <span key={source} className="source-chip">{humanize(source)}</span>) : <span className="text-xs text-white/28">No governed source type recorded.</span>}
                  </div>
                  <p className="mt-4 text-xs leading-5 text-white/28">Candidate rank is a research-prioritization output. It is not a portfolio weight, trade instruction, or suitability determination.</p>
                </div>
              </div>
            </div>
          </details>
        ))}

        {visible.length === 0 && (
          <div className="px-6 py-16 text-center">
            <p className="text-sm text-white/50">No candidates match the current filters.</p>
            <button type="button" className="button-secondary mt-5" onClick={() => { setQuery(""); setFilter("all"); setSortMode("rank"); }}>Reset filters</button>
          </div>
        )}
      </div>
    </div>
  );
}

function Metric({ label, value, positive = false }: { label: string; value: string; positive?: boolean }) {
  return <div><p className={`font-mono text-sm ${positive ? "text-emerald-300" : "text-white/70"}`}>{value}</p><p className="mt-1 text-[9px] tracking-[0.16em] text-white/25">{label}</p></div>;
}

function Fact({ label, value }: { label: string; value: string }) {
  return <div className="border border-white/8 bg-black/30 p-4"><p className="detail-label">{label}</p><p className="mt-3 font-mono text-sm text-white/70">{value}</p></div>;
}

function ResearchBlock({ label, text, risk = false }: { label: string; text: string; risk?: boolean }) {
  return <div className={`border p-5 ${risk ? "border-red-400/15 bg-red-400/[0.02]" : "border-white/8 bg-black/25"}`}><p className={`detail-label ${risk ? "text-red-300" : ""}`}>{label}</p><p className="mt-3 text-sm leading-6 text-white/45">{text}</p></div>;
}

function Score({ label, value, decimals = 3 }: { label: string; value: number | null; decimals?: number }) {
  return <div className="border border-white/8 px-3 py-3"><p className="font-mono text-sm text-white/65">{typeof value === "number" ? value.toFixed(decimals) : "—"}</p><p className="mt-1 text-[8px] tracking-[0.12em] text-white/25">{label.toUpperCase()}</p></div>;
}
