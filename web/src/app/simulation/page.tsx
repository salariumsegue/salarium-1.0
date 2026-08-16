import type { Metadata } from "next";

import { UnavailableState } from "@/components/data-state";
import LivePaperSimulator from "@/components/live-paper-simulator";
import { PageIntro, StatusBadge } from "@/components/ui";
import { loadForwardPaperSnapshot } from "@/lib/site-data";

export const metadata: Metadata = {
  title: "Live Paper Simulator",
  description: "Follow Salarium's governed portfolio with delayed public quotes and a local $100,000 paper account.",
  alternates: { canonical: "/simulation" },
};

export default function SimulationPage() {
  const snapshot = loadForwardPaperSnapshot();

  return (
    <main id="main-content" className="site-main">
      <section className="page-section">
        <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-start">
          <PageIntro
            eyebrow="LIVE PAPER SIMULATOR"
            title="Market motion."
            muted="No market access."
            description="A browser-local $100,000 paper account marks the current governed Salarium portfolio with delayed best-effort public quotes. Simulated fills, costs, cash, positions, P&L, drawdown, and an append-only event history remain separated from brokerage infrastructure."
          />
          <StatusBadge tone="neutral">DELAYED / SIMULATED</StatusBadge>
        </div>

        <div className="mt-10">
          {snapshot.status === "available" ? (
            <LivePaperSimulator
              holdings={snapshot.data.forward_portfolio.holdings.map((holding) => ({
                ticker: holding.ticker,
                companyName: holding.company_name,
                rank: holding.rank,
                weight: holding.paper_weight,
                referencePrice: holding.reference_price,
              }))}
              generatedAt={snapshot.data.generated_at_utc}
              lastRebalanceDate={snapshot.data.forward_portfolio.last_rebalance_date}
              modelHash={snapshot.data.model.model_sha256}
              signalDate={snapshot.data.latest_signal_state.date}
              sessionsUntilNextRebalance={snapshot.data.forward_portfolio.sessions_until_next_rebalance}
            />
          ) : (
            <UnavailableState title="The paper simulator is gated." artifact="web/public/data/forward_paper_snapshot.json">
              {snapshot.reason} A simulated account is created only from a valid governed forward-paper snapshot.
            </UnavailableState>
          )}
        </div>
      </section>
    </main>
  );
}
