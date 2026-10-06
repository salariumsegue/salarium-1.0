import type { Metadata } from "next";
import Link from "next/link";
import { loadReleaseSnapshot } from "@/lib/site-data";

export const metadata: Metadata = {
  title: "Research",
  description:
    "Browse Salarium's portfolio policies, research evidence, rejected experiments, historical results, and model decisions.",
  alternates: { canonical: "/research" },
};

const destinations = [
  {
    eyebrow: "PAPER ACCOUNTS",
    title: "Compare four portfolio policies",
    description:
      "Follow independent Core, Defensive, Drawdown Control, and experimental Oil accounts on the same dates.",
    href: "/dashboard",
    action: "Open portfolio dashboard",
  },
  {
    eyebrow: "OIL SLEEVE / CASE 001",
    title: "Read the oil hedge verdict",
    description:
      "See the strongest evidence for and against the 20% oil sleeve, its recorded gates, and why it remains experimental.",
    href: "/research/courtroom",
    action: "Open the model courtroom",
  },
  {
    eyebrow: "EXPERIMENT RECORD",
    title: "Inspect accepted and rejected tests",
    description:
      "Review the hypotheses that changed the release and the evidence attached to each decision.",
    href: "/research/experiments",
    action: "Browse the experiment archive",
  },
  {
    eyebrow: "HISTORICAL RESULTS",
    title: "Review performance and risk",
    description:
      "Explore walk-forward returns, drawdowns, yearly results, and the separate forward paper record.",
    href: "/research/performance",
    action: "View the performance record",
  },
  {
    eyebrow: "DECISION REPLAY",
    title: "Reconstruct a past rebalance",
    description:
      "Inspect what the model knew, ranked, held, and changed on a recorded decision date.",
    href: "/replay",
    action: "Open the decision archive",
  },
  {
    eyebrow: "PORTFOLIO RISK",
    title: "Trace shared dependencies",
    description:
      "See where holdings overlap through measured exposures and documented business themes.",
    href: "/dependencies",
    action: "Map portfolio dependencies",
  },
  {
    eyebrow: "MODEL DESIGN",
    title: "Read the method and architecture",
    description:
      "Follow the data, ranking, weighting, and risk controls behind the research portfolio.",
    href: "/methodology",
    action: "Review methodology",
  },
];

export default function ResearchPage() {
  const release = loadReleaseSnapshot();
  const core = release.results.core_balanced;
  const facts = [
    ["Evaluation", release.research.period],
    ["Out-of-sample rebalances", String(core.num_rebalances)],
    ["Live track record", "None"],
  ];

  return (
    <main id="main-content" className="site-main research-index">
      <section className="page-section research-index-intro">
        <div>
          <p className="eyebrow">SALARIUM / RESEARCH RECORD</p>
          <h1>What we tested. What worked. What failed.</h1>
          <p>
            Compare the paper portfolios, read why the oil hedge failed its test,
            and check the historical results against their assumptions. The returns
            are simulated or paper tracked. No money is invested through this site.
          </p>
        </div>
        <aside aria-label="Research record scope">
          {facts.map(([label, value]) => (
            <div key={label}><span>{label}</span><strong>{value}</strong></div>
          ))}
        </aside>
      </section>

      <section className="site-container research-index-grid" aria-label="Research sections">
        {destinations.map((item, index) => (
          <Link className="research-index-card" href={item.href} key={item.href}>
            <span className="research-index-number">0{index + 1}</span>
            <span className="eyebrow">{item.eyebrow}</span>
            <h2>{item.title}</h2>
            <p>{item.description}</p>
            <span className="research-index-action">{item.action}<span aria-hidden="true"> ↗</span></span>
          </Link>
        ))}
      </section>

      <section className="site-container research-index-note">
        <p>Evidence standard</p>
        <span>Each result links to its method, evaluation period, and known limitations. The release candidate’s historical return is not a forecast.</span>
        <Link href="/disclosures">Read the full disclosures ↗</Link>
      </section>
    </main>
  );
}
