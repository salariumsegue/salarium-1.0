import fs from "node:fs";
import path from "node:path";
import type { Metadata } from "next";
import PortfolioDashboard from "@/components/portfolio-dashboard";
import type { PaperPortfolios } from "@/lib/paper-portfolios";
export const metadata: Metadata = {
  title: "Four paper portfolios",
  alternates: { canonical: "/dashboard" },
};
export default function DashboardPage() {
  const data = JSON.parse(
    fs.readFileSync(
      path.join(process.cwd(), "public/data/paper_portfolios.json"),
      "utf8",
    ),
  ) as PaperPortfolios;
  return (
    <main id="main-content" className="site-main research-page">
      <section className="site-container">
        <p className="eyebrow">FORWARD RESEARCH / FOUR PAPER ACCOUNTS</p>
        <h1>
          Same market.
          <br />
          Four portfolio policies.
        </h1>
        <p className="research-lead">
          Core, Defensive, Drawdown Control, and Oil Diversifier. Compare
          independent accounts on the same dates, then inspect their positions,
          costs, and decisions.
        </p>
        <PortfolioDashboard data={data} />
      </section>
    </main>
  );
}
