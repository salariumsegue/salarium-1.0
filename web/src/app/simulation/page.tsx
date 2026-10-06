import type { Metadata } from "next";

import { UnavailableState } from "@/components/data-state";
import LivePaperSimulator from "@/components/live-paper-simulator";
import { PageIntro, StatusBadge } from "@/components/ui";
import { loadForwardPaperSnapshot } from "@/lib/site-data";

export const metadata: Metadata = {
  title: "Paper account simulator",
  description: "Try a $100,000 paper account using delayed public prices. No broker is connected.",
  alternates: { canonical: "/simulation" },
};

export default function SimulationPage() {
  const snapshot = loadForwardPaperSnapshot();

  return (
    <main id="main-content" className="site-main">
      <section className="page-section">
        <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-start">
          <PageIntro
            eyebrow="PAPER ACCOUNT / BROWSER ONLY"
            title="Try the portfolio with paper money"
            muted="Using delayed prices."
            description="Start with $100,000 and follow the current paper portfolio. Prices may be delayed, and simulated trades do not include every cost of a real trade. Nothing connects to a broker."
          />
          <StatusBadge tone="neutral">DELAYED PRICES · SIMULATED TRADES</StatusBadge>
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
            <UnavailableState title="The paper account is unavailable." artifact="web/public/data/forward_paper_snapshot.json">
              {snapshot.reason} The simulator needs a current paper portfolio snapshot.
            </UnavailableState>
          )}
        </div>
      </section>
    </main>
  );
}
