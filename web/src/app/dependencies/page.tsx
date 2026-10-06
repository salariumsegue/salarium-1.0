import type { Metadata } from "next";
import DependencyMap from "@/components/dependency-map";
import { loadForwardPaperSnapshot } from "@/lib/site-data";
export const metadata: Metadata = {
  title: "Portfolio dependencies",
  alternates: { canonical: "/dependencies" },
};
export default function DependenciesPage() {
  const forward = loadForwardPaperSnapshot();
  return (
    <main id="main-content" className="site-main research-page">
      <section className="site-container">
        <p className="eyebrow">HOLDINGS / SHARED BUSINESS RISKS</p>
        <h1>
          Shared business risks
          <br />
          across the portfolio.
        </h1>
        <p className="research-lead">
          Different stocks can rely on the same customers, suppliers, or economic trends. Select a theme to see the holdings, portfolio weight, and sources behind it.
        </p>
        {forward.status === "available" ? (
          <>
            <p className="research-muted">
              Rankings dated {forward.data.latest_signal_state.date} · holdings
              last changed {forward.data.forward_portfolio.last_rebalance_date}
            </p>
            <DependencyMap snapshot={forward.data} />
          </>
        ) : (
          <p>The portfolio data is unavailable: {forward.reason}</p>
        )}
      </section>
    </main>
  );
}
