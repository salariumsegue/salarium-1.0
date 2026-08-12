"use client";

import { useMemo, useRef, useState } from "react";

import ProvenanceDisclosure from "@/components/provenance-disclosure";
import { SearchIcon } from "@/components/icons";
import { humanize, percent } from "@/lib/format";
import type { Ranking, RankingSnapshot } from "@/lib/site-types";

type SortKey = "rank" | "ticker" | "score" | "score_percentile" | "volatility_20d";
type Direction = "asc" | "desc";

export default function RankingExplorer({ rankings, snapshot }: { rankings: Ranking[]; snapshot: RankingSnapshot }) {
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<{ key: SortKey; direction: Direction }>({ key: "rank", direction: "asc" });
  const [selected, setSelected] = useState<Ranking | null>(null);
  const dialogRef = useRef<HTMLDialogElement>(null);

  const visible = useMemo(() => {
    const normalized = query.trim().toUpperCase();
    return rankings.filter((row) => !normalized || row.ticker.includes(normalized)).sort((a, b) => {
      const av = a[sort.key]; const bv = b[sort.key];
      const order = typeof av === "string" ? av.localeCompare(String(bv)) : Number(av) - Number(bv);
      return sort.direction === "asc" ? order : -order;
    });
  }, [query, rankings, sort]);

  function changeSort(key: SortKey) { setSort((current) => ({ key, direction: current.key === key && current.direction === "asc" ? "desc" : "asc" })); }
  function openDetail(row: Ranking) { setSelected(row); requestAnimationFrame(() => dialogRef.current?.showModal()); }
  function closeDetail() { dialogRef.current?.close(); setSelected(null); }

  return <div className="ranking-surface">
    <div className="ranking-toolbar"><label className="search-field"><SearchIcon className="h-4 w-4 text-white/35" /><span className="sr-only">Search published tickers</span><input value={query} onChange={(event)=>setQuery(event.target.value.toUpperCase())} placeholder="Search ticker" /></label><span aria-live="polite">{visible.length} / {rankings.length} PUBLISHED SECURITIES</span></div>
    <div className="ranking-desktop"><table className="institutional-table"><thead><tr><SortHeader label="Rank" field="rank" active={sort} onSort={changeSort} /><SortHeader label="Ticker / company" field="ticker" active={sort} onSort={changeSort} /><SortHeader label="Salarium score" field="score" active={sort} onSort={changeSort} /><SortHeader label="Percentile" field="score_percentile" active={sort} onSort={changeSort} /><SortHeader label="20D volatility" field="volatility_20d" active={sort} onSort={changeSort} /><th>Risk state</th><th>Selection band</th></tr></thead><tbody>{visible.map((row)=><tr key={row.ticker}><td className="muted-number">{String(row.rank).padStart(2,"0")}</td><td><button type="button" className="ticker-button" onClick={()=>openDetail(row)}><strong>{row.ticker}</strong><small>{row.company_name ?? "Company not provided"}</small></button></td><td className="positive-number">{row.score.toFixed(6)}</td><td>{percent(row.score_percentile,1)}</td><td>{percent(row.volatility_20d,2)}</td><td><span className="risk-label"><i className={row.risk_state==="risk_off"?"negative-dot":"positive-dot"} />{humanize(row.risk_state)}</span></td><td>{selectionBand(row.rank, snapshot)}</td></tr>)}</tbody></table></div>
    <div className="ranking-mobile">{visible.map((row)=><button type="button" key={row.ticker} className="ranking-mobile-row" onClick={()=>openDetail(row)}><span><small>#{String(row.rank).padStart(2,"0")}</small><strong>{row.ticker}</strong><em>{row.company_name ?? "Company not provided"}</em></span><span><b>{row.score.toFixed(6)}</b><small>{percent(row.score_percentile,1)} percentile</small><em>{selectionBand(row.rank,snapshot)}</em></span></button>)}</div>
    {visible.length===0 && <div className="empty-state"><span>0 RESULTS</span><h3>No published ticker matches “{query}”.</h3><p>Search is limited to the 25 securities in this published snapshot.</p><button type="button" onClick={()=>setQuery("")} className="button-secondary">Clear search</button></div>}
    <dialog ref={dialogRef} className="ranking-dialog" onClose={()=>setSelected(null)}>{selected && <div><header><div><p className="eyebrow">RANKING DETAIL / {String(selected.rank).padStart(2,"0")}</p><h2>{selected.ticker}</h2><p>{selected.company_name ?? "Company name is not present in this artifact."}</p></div><button type="button" onClick={closeDetail} aria-label={`Close ${selected.ticker} detail`}>Close</button></header><dl className="detail-ledger"><Detail label="Salarium score" value={selected.score.toFixed(6)} /><Detail label="Universe percentile" value={percent(selected.score_percentile,1)} /><Detail label="Model rank" value={`${selected.rank} of ${snapshot.latest_signal_state.universe_count}`} /><Detail label="Selection status" value={selectionBand(selected.rank,snapshot)} /><Detail label="20D volatility" value={percent(selected.volatility_20d,2)} /><Detail label="Risk state" value={`${humanize(selected.risk_state)} · ${selected.regime_is_confident?"confident":"low confidence"}`} /></dl><p className="dialog-note">The selection band is a ranking-stage label, not confirmation that the security is held. Covariance, persistence, weighting, and exposure controls operate downstream.</p><ProvenanceDisclosure record={{source:snapshot.system.status==="forward_paper_no_orders"?"Frozen 20D model / forward paper market-close feed":"Governed 20D out-of-sample score stream",artifact:snapshot.provenance.source_path,outOfSamplePeriod:String(snapshot.model.test_year),model:snapshot.model.configuration,commit:snapshot.provenance.git_commit,generatedAt:snapshot.generated_at_utc}} /></div>}</dialog>
  </div>;
}

function selectionBand(rank: number, snapshot: RankingSnapshot) { if(rank<=snapshot.architecture.portfolio_top_n) return "Top-10 selection band"; if(rank<=snapshot.architecture.persistence_buffer_rank) return "Persistence buffer band"; return "Outside portfolio band"; }
function SortHeader({label,field,active,onSort}:{label:string;field:SortKey;active:{key:SortKey;direction:Direction};onSort:(field:SortKey)=>void}){const selected=active.key===field;return <th aria-sort={selected?(active.direction==="asc"?"ascending":"descending"):"none"}><button type="button" onClick={()=>onSort(field)}>{label}<span aria-hidden="true">{selected?(active.direction==="asc"?" ↑":" ↓"):" ↕"}</span></button></th>;}
function Detail({label,value}:{label:string;value:string}){return <div><dt>{label}</dt><dd>{value}</dd></div>;}
