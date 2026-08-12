import type { Metadata } from "next";

import { UnavailableState } from "@/components/data-state";
import ProvenanceDisclosure from "@/components/provenance-disclosure";
import { PageIntro } from "@/components/ui";
import { formatDateTime } from "@/lib/format";
import { loadPortfolioSnapshot, loadReleaseSnapshot } from "@/lib/site-data";

export const metadata: Metadata = { title: "Portfolio", description: "Inspect the governed Salarium research portfolio when a release-aligned snapshot is available.", alternates: { canonical: "/portfolio" } };

export default function PortfolioPage() {
  const state = loadPortfolioSnapshot();
  const release = loadReleaseSnapshot();
  return <main id="main-content" className="site-main"><section className="page-section">
    <PageIntro eyebrow="PORTFOLIO CONSTRUCTION" title="Portfolio evidence." muted="Only when the artifact agrees." description="A ranking is not a holding. This surface requires a governed, release-aligned export containing actual weights, exposure, snapshot date, and provenance before it will display a portfolio." />
    <div className="mt-10">
      {state.status === "available" ? <div className="card overflow-hidden"><div className="p-6"><p className="eyebrow">{state.data.portfolio}</p><h2 className="mt-3 text-3xl">Snapshot {state.data.snapshot_date}</h2></div><table className="institutional-table"><thead><tr><th>Rank</th><th>Ticker</th><th>Weight</th><th>Status</th></tr></thead><tbody>{state.data.holdings.map((holding) => <tr key={holding.ticker}><td>{holding.rank ?? "—"}</td><td>{holding.ticker}</td><td>{(holding.weight * 100).toFixed(2)}%</td><td>{holding.selection_status}</td></tr>)}</tbody></table></div> : <UnavailableState title="Current portfolio snapshot is not published." artifact="web/public/data/portfolio_snapshot.json">{state.reason} The repository contains historical policy weights, but they do not match the locked release portfolio contract and are therefore not shown here.</UnavailableState>}
    </div>
    <div className="mt-8 grid gap-4 md:grid-cols-3"><Boundary label="Rankings" value="Available" detail="Top-25 committed cross-section" /><Boundary label="Holdings and weights" value="Unavailable" detail="Release-aligned export required" risk /><Boundary label="Live execution" value="Not applicable" detail="Salarium does not place trades" /></div>
    <div className="mt-8"><ProvenanceDisclosure record={{ source: "Salarium 1.0 release contract", artifact: state.status === "available" ? state.data.provenance.source_path : "web/public/data/portfolio_snapshot.json", portfolio: "Top-10 / 60D shrinkage max-div / 25% signal blend", commit: state.status === "available" ? state.data.provenance.git_commit : release.provenance.git_commit, generatedAt: state.status === "available" ? formatDateTime(state.data.generated_at_utc) : "Not generated" }} /></div>
  </section></main>;
}

function Boundary({ label, value, detail, risk = false }: { label: string; value: string; detail: string; risk?: boolean }) { return <div className="card p-5"><p className="detail-label">{label}</p><p className={`mt-4 font-mono ${risk ? "text-red-300" : "text-white"}`}>{value}</p><p className="mt-2 text-xs text-white/35">{detail}</p></div>; }
