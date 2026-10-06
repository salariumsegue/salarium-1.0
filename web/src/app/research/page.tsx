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

const nextIdeas = [
  { code: "R-01", name: "Treasury ballast", sleeve: "20% 3-month T-bills", question: "Does a fixed bill ladder cut equity drawdowns without giving up too much return after costs?", review: "30 NOV 2026", date: "2026-11-30", risk: "Reinvestment risk / bill yield changes" },
  { code: "R-02", name: "Developed markets ex-US", sleeve: "20% international equities", question: "Does adding developed-market stocks reduce portfolio concentration after currency and country risk?", review: "21 DEC 2026", date: "2026-12-21", risk: "FX, country weights, overlapping sectors" },
  { code: "R-03", name: "Real-rate split", sleeve: "10% T-bills / 10% gold", question: "Can a small gold position diversify the equity book across inflation and real-rate regimes?", review: "25 JAN 2027", date: "2027-01-25", risk: "Gold carries no income; regime dependence" },
  { code: "R-04", name: "Listed infrastructure", sleeve: "20% global infrastructure equities", question: "Do infrastructure operators add durable cash flows, or mostly add rate and equity exposure?", review: "22 FEB 2027", date: "2027-02-22", risk: "Leverage, rate sensitivity, sector concentration" },
  { code: "R-05", name: "Digital-asset satellite", sleeve: "5% Bitcoin / 15% T-bills", question: "Does a tightly capped bitcoin position improve diversification enough to justify its tail risk?", review: "29 MAR 2027", date: "2027-03-29", risk: "Severe drawdowns, custody and market-hour gaps" },
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

      <section className="site-container research-next">
        <div className="research-next-heading">
          <div><p className="eyebrow">NEXT / FIVE HYPOTHESES</p><h2>What I would test next.</h2><p>These are proposed research reviews, not scheduled launches. Each idea starts in a separate paper ledger and has to beat the same out-of-sample, cost, and risk gates before it earns a release.</p></div>
          <aside><span>NON-OIL CAPITAL</span><strong>20% target sleeve</strong><small>Every candidate tests an allocation outside oil. The digital-asset idea is capped at 5% because its drawdowns can dominate a portfolio.</small></aside>
        </div>
        <div className="research-next-grid">{nextIdeas.map((idea) => <article className="research-next-card" key={idea.code}>
          <div className="research-next-top"><span>{idea.code} / PROPOSAL</span><time dateTime={idea.date}>{idea.review}</time></div>
          <h3>{idea.name}</h3><strong>{idea.sleeve}</strong><p>{idea.question}</p>
          <footer><span>MAIN RISK</span><span>{idea.risk}</span></footer>
        </article>)}</div>
        <p className="research-next-disclaimer">Review dates are planning targets for deciding whether to publish the evidence. None of these strategies is currently in a released portfolio.</p>
      </section>
    </main>
  );
}
