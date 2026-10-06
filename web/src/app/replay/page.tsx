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
        <p className="eyebrow">DECISION ARCHIVE / FORWARD PAPER</p>
        <h1>Reopen the record.</h1>
        <p className="research-lead">
          {archive.entries.length} recorded rebalances. The rankings, weights,
          and limits that were published at the time—without mixing in what
          happened next.
        </p>
        <DecisionReplay archive={archive} />
      </section>
    </main>
  );
}
