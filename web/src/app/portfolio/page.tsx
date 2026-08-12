import type { Metadata } from "next";

import { UnavailableState } from "@/components/data-state";
import ProvenanceDisclosure from "@/components/provenance-disclosure";
import { PageIntro, StatusBadge } from "@/components/ui";
import { formatDate, formatDateTime, percent } from "@/lib/format";
import { loadForwardPaperSnapshot, loadPortfolioSnapshot, loadReleaseSnapshot } from "@/lib/site-data";

export const metadata: Metadata = {
  title: "Portfolio",
  description: "Inspect the governed Salarium forward paper portfolio and its release boundary.",
  alternates: { canonical: "/portfolio" },
};

const currency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

export default function PortfolioPage() {
  const forward = loadForwardPaperSnapshot();
  const releasePortfolio = loadPortfolioSnapshot();
  const release = loadReleaseSnapshot();

  return (
    <main id="main-content" className="site-main">
      <section className="page-section">
        <PageIntro
          eyebrow="FORWARD PAPER PORTFOLIO"
          title="Weights you can inspect."
          muted="No orders behind them."
          description="A ranking is not a holding. This page shows the governed paper portfolio only when fresh prices, frozen-model scoring, covariance construction, exposure control, and provenance gates all pass."
        />

        <div className="mt-10">
          {forward.status === "available" ? (
            <div className="card overflow-hidden">
              <div className="flex flex-col justify-between gap-5 p-6 sm:flex-row sm:items-start">
                <div>
                  <p className="eyebrow">PAPER / NO BROKERAGE CONNECTION</p>
                  <h2 className="mt-3 text-3xl">Rebalanced {formatDate(forward.data.forward_portfolio.last_rebalance_date)}</h2>
                  <p className="mt-3 text-sm text-white/42">Indicative NAV {currency.format(forward.data.forward_portfolio.indicative_nav)} · {percent(forward.data.forward_portfolio.shadow_equity_exposure, 0)} equity · {percent(forward.data.forward_portfolio.cash_weight, 0)} {forward.data.forward_portfolio.cash_proxy}</p>
                </div>
                <StatusBadge tone="positive">FORWARD PAPER</StatusBadge>
              </div>
              <div className="overflow-x-auto"><table className="institutional-table min-w-[46rem]">
                <thead><tr><th>Rank</th><th>Ticker / company</th><th>Base weight</th><th>Paper weight</th></tr></thead>
                <tbody>{forward.data.forward_portfolio.holdings.map((holding) => (
                  <tr key={holding.ticker}>
                    <td>{holding.rank}</td>
                    <td><strong>{holding.ticker}</strong><small className="ml-3 text-white/30">{holding.company_name}</small></td>
                    <td>{percent(holding.base_weight, 2)}</td>
                    <td className="positive-number">{percent(holding.paper_weight, 2)}</td>
                  </tr>
                ))}</tbody>
              </table></div>
            </div>
          ) : releasePortfolio.status === "available" ? (
            <div className="card overflow-hidden">
              <div className="p-6"><p className="eyebrow">{releasePortfolio.data.portfolio}</p><h2 className="mt-3 text-3xl">Snapshot {releasePortfolio.data.snapshot_date}</h2></div>
              <div className="overflow-x-auto"><table className="institutional-table min-w-[40rem]"><thead><tr><th>Rank</th><th>Ticker</th><th>Weight</th><th>Status</th></tr></thead><tbody>{releasePortfolio.data.holdings.map((holding) => <tr key={holding.ticker}><td>{holding.rank ?? "—"}</td><td>{holding.ticker}</td><td>{percent(holding.weight, 2)}</td><td>{holding.selection_status}</td></tr>)}</tbody></table></div>
            </div>
          ) : (
            <UnavailableState title="Current portfolio snapshot is not published." artifact="web/public/data/forward_paper_snapshot.json">{forward.reason} The historical policy weights remain separate from forward paper evidence.</UnavailableState>
          )}
        </div>

        <div className="mt-8 grid gap-4 md:grid-cols-3">
          <Boundary label="Market-close data" value={forward.status === "available" ? formatDate(forward.data.latest_signal_state.date) : "Unavailable"} detail={forward.status === "available" ? `${percent(forward.data.data_quality.feature_coverage, 1)} feature coverage` : "Forward gate required"} />
          <Boundary label="Paper holdings" value={forward.status === "available" ? `${forward.data.forward_portfolio.holdings.length} names` : "Unavailable"} detail="Top-10 / covariance / drawdown control" />
          <Boundary label="Live execution" value="Disabled" detail="No orders, broker, or live capital" risk />
        </div>

        <div className="mt-8"><ProvenanceDisclosure record={{ source: forward.status === "available" ? "Frozen 20D model / forward market-close paper feed" : "Salarium 1.0 release contract", artifact: forward.status === "available" ? forward.data.provenance.source_path : "web/public/data/forward_paper_snapshot.json", portfolio: "Top-10 / 60D shrinkage max-div / 25% signal blend / drawdown budget", commit: forward.status === "available" ? forward.data.provenance.git_commit : release.provenance.git_commit, generatedAt: forward.status === "available" ? formatDateTime(forward.data.generated_at_utc) : "Not generated" }} /></div>
      </section>
    </main>
  );
}

function Boundary({ label, value, detail, risk = false }: { label: string; value: string; detail: string; risk?: boolean }) {
  return <div className="card p-5"><p className="detail-label">{label}</p><p className={`mt-4 font-mono ${risk ? "text-red-300" : "text-white"}`}>{value}</p><p className="mt-2 text-xs text-white/35">{detail}</p></div>;
}
