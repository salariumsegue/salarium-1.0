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
        <p className="eyebrow">FOUR PAPER ACCOUNTS / SAME START DATE</p>
        <h1>
          One market.
          <br />
          Four portfolio policies.
        </h1>
        <p className="research-lead">
          Core, Defensive, Drawdown Control, and experimental Oil Diversifier.
          Compare their holdings, costs, and results from the same market closes.
        </p>
        <PortfolioDashboard data={data} />
      </section>
    </main>
  );
}
