import fs from "node:fs";
import path from "node:path";
import type { Metadata } from "next";
import DecisionReplay from "@/components/decision-replay";
import type { DecisionArchive } from "@/lib/evidence";
export const metadata: Metadata = {
  title: "Decision replay",
  alternates: { canonical: "/replay" },
};
export default function ReplayPage() {
  const archive = JSON.parse(
    fs.readFileSync(
      path.join(process.cwd(), "public/data/decision_archive.json"),
      "utf8",
    ),
  ) as DecisionArchive;
  return (
    <main id="main-content" className="site-main research-page">
      <section className="site-container">
        <p className="eyebrow">PAST PORTFOLIO DECISIONS</p>
        <h1>What the model knew then.</h1>
        <p className="research-lead">
          {archive.entries.length} recorded rebalances. Review that day&apos;s
          rankings, holdings, and limits without using information that came later.
        </p>
        <DecisionReplay archive={archive} />
      </section>
    </main>
  );
}
