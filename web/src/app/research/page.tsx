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
    title: "Compare the four paper portfolios",
    description:
      "Core, Defensive, Drawdown Control, and the experimental Oil account, tracked on the same dates.",
    href: "/dashboard",
    action: "Open the portfolios",
  },
  {
    eyebrow: "OIL SLEEVE / CASE 001",
    title: "Why the oil hedge was rejected",
    description:
      "The case for and against a 20% oil sleeve, the nine tests it faced, and the one it failed.",
    href: "/research/courtroom",
    action: "Read the oil sleeve case",
  },
  {
    eyebrow: "EXPERIMENTS",
    title: "Tests that passed and tests that failed",
    description:
      "Each design question, the result, and the decision it led to.",
    href: "/research/experiments",
    action: "See the experiments",
  },
  {
    eyebrow: "HISTORICAL RESULTS",
    title: "Returns and risk",
    description:
      "Walk-forward returns, drawdowns, and year-by-year results, plus the separate paper record.",
    href: "/research/performance",
    action: "See the results",
  },
  {
    eyebrow: "DECISION REPLAY",
    title: "Replay a past rebalance",
    description:
      "What the model ranked, held, and changed on a recorded date.",
    href: "/replay",
    action: "Open the archive",
  },
  {
    eyebrow: "PORTFOLIO RISK",
    title: "Where holdings overlap",
    description:
      "Holdings that depend on the same customers, suppliers, or trends.",
    href: "/dependencies",
    action: "See the overlap",
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
          <p className="eyebrow">SALARIUM / RESEARCH</p>
          <h1>What I tested and how it turned out.</h1>
          <p>
            Compare the paper portfolios, read why the oil hedge was rejected, and check the historical results against their assumptions. Every return here is simulated or paper tracked. No real money is involved.
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
        <p>How to read these</p>
        <span>Each result links to its method, test period, and known limits. A historical return is not a forecast.</span>
        <Link href="/disclosures">Read the full disclosures ↗</Link>
      </section>

      <section className="site-container research-next">
        <div className="research-next-heading">
          <div><p className="eyebrow">NEXT / FIVE IDEAS</p><h2>What I would test next.</h2><p>These are ideas I plan to test, not scheduled launches. Each one starts as its own paper account and has to pass the same out-of-sample, cost, and risk tests before it is added.</p></div>
          <aside><span>NON-OIL CAPITAL</span><strong>20% target sleeve</strong><small>Each idea tests an allocation outside oil. Bitcoin is capped at 5% because its drawdowns can dominate a portfolio.</small></aside>
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
