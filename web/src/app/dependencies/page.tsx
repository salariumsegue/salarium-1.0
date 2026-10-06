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
        <p className="eyebrow">PORTFOLIO / BUSINESS DEPENDENCIES</p>
        <h1>
          Business dependencies
          <br />
          in the paper portfolio.
        </h1>
        <p className="research-lead">
          A first map of business relationships inside the paper portfolio.
          Select a theme to inspect its holdings, allocation, and source
          material.
        </p>
        {forward.status === "available" ? (
          <>
            <p className="research-muted">
              Signal date {forward.data.latest_signal_state.date} · holdings
              from {forward.data.forward_portfolio.last_rebalance_date}
            </p>
            <DependencyMap snapshot={forward.data} />
          </>
        ) : (
          <p>Current portfolio unavailable: {forward.reason}</p>
        )}
      </section>
    </main>
  );
}
