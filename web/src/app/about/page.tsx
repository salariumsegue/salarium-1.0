import type { Metadata } from "next";

import DataStatusStrip from "@/components/data-status-strip";
import MetricCard from "@/components/metric-card";
import { GITHUB_URL, MODEL_CARD_URL, RELEASE_NOTES_URL } from "@/lib/site-config";
import { loadReleaseSnapshot } from "@/lib/site-data";

export const metadata: Metadata = {
  title: "About",
  description:
    "Why I built Salarium, how its stock model works, and what its results can and cannot tell you.",
  alternates: { canonical: "/about" },
};

export default function AboutPage() {
  const release = loadReleaseSnapshot();

  return (
    <main id="main-content" className="site-main">
      <section className="page-section pb-12 pt-16 lg:pt-20">
        <div className="grid gap-12 lg:grid-cols-[1.1fr_0.9fr] lg:items-end">
          <div>
            <p className="eyebrow">Why Salarium exists</p>
            <h1 className="mt-5 text-5xl font-semibold tracking-tight text-balance sm:text-7xl">
              A student-built
              <span className="block text-white/32">quantitative research project.</span>
            </h1>
            <p className="mt-6 max-w-3xl text-base leading-7 text-white/48">
              Salarium ranks a set of U.S. stocks, builds paper portfolios from those rankings, and records each update. You can inspect the rules, results, and limits here.
            </p>
          </div>

          <aside className="border border-emerald-400/25 bg-emerald-400/[0.035] p-6 sm:p-8">
            <p className="eyebrow text-emerald-300">The standard</p>
            <blockquote className="mt-5 text-2xl font-medium leading-9 tracking-[-0.025em] text-white/85">
              I want every result to show its inputs, assumptions, and weak points.
            </blockquote>
          </aside>
        </div>
      </section>

      <DataStatusStrip snapshot={release} />

      <section className="page-section">
        <div className="grid gap-10 lg:grid-cols-[0.75fr_1.25fr]">
          <div>
            <p className="eyebrow">Project identity</p>
            <h2 className="mt-4 text-4xl font-medium tracking-tight">Finance, code, and a clear record.</h2>
          </div>
          <div className="space-y-6 text-base leading-8 text-white/45">
            <p>
              Salarium is a stock research project built in public. It ranks shares, turns those rankings into paper portfolios, and publishes the rules and results. It is not a fund, and its simulated returns are not live performance.
            </p>
            <p>
              I&apos;m Niall Gillen, a finance student at Indiana University&apos;s Kelley School of Business. I built Salarium to study how a stock-ranking model, portfolio rules, and risk controls work together.
            </p>
            <p>
              The name comes from the Latin <em>salarium</em>, a word linked to the origin of “salary.” Here it stands for careful decisions about capital.
            </p>
          </div>
        </div>
      </section>

      <section className="page-section border-y border-white/8 bg-white/[0.012]">
        <div className="grid gap-10 lg:grid-cols-[.8fr_1.2fr]">
          <div><p className="eyebrow">How the work is checked</p><h2 className="mt-4 text-4xl font-medium tracking-tight">Software helps with the research. Rules decide what gets published.</h2></div>
          <div className="text-base leading-8 text-white/45"><p>Scripts check market data, compare model settings, and calculate portfolio results. Each published result must pass date, cost, and portfolio checks that can be reviewed in the repository.</p><p className="mt-5">The model ranks stocks. It does not understand a company or make investment decisions for a person.</p></div>
        </div>
      </section>

      <section className="page-section border-y border-white/8 bg-white/[0.012]">
        <div className="max-w-3xl">
          <p className="eyebrow">How the model is checked</p>
          <h2 className="mt-4 text-4xl font-medium tracking-tight">The checks behind the results</h2>
        </div>
        <div className="mt-9 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Pillar number="01" title="Use only past data" body="Each annual test trains on earlier data and saves its later stock rankings." />
          <Pillar number="02" title="Compare on the same dates" body="Portfolio rules are tested against the same rankings and market periods." />
          <Pillar number="03" title="Keep failed tests" body="Results that made the portfolio worse stay in the experiment archive." />
          <Pillar number="04" title="Check each release" body="Code checks and saved data must pass before new results appear on the site." />
        </div>
      </section>

      <section className="page-section">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard label="Stock universe" value={release.architecture.universe} detail="Stocks eligible for ranking" />
          <MetricCard label="Prediction / rebalance" value={`${release.architecture.model_horizon_days}D / ${release.architecture.rebalance_every_days}D`} detail="Horizon and trading cadence tested separately" />
          <MetricCard label="Portfolio breadth" value={`Top-${release.architecture.top_n}`} detail={`Rank-${release.architecture.buffer_rank} persistence buffer`} />
          <MetricCard label="Leverage limit" value={`${release.architecture.leverage_cap.toFixed(2)}x`} detail="Maximum permitted exposure" />
        </div>
      </section>

      <section className="page-section border-y border-white/8 bg-black/45">
        <div className="grid gap-8 lg:grid-cols-[1fr_0.85fr]">
          <div>
            <p className="eyebrow">For readers who want the detail</p>
            <h2 className="mt-4 text-3xl font-medium">Code, model card, and release notes</h2>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-white/42">
              The code includes the stock-ranking model, portfolio calculations, experiment results, and the website. The links below take you to the source files and documents.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <a href={GITHUB_URL} target="_blank" rel="noreferrer" className="button-primary">Open source repository ↗</a>
              <a href={MODEL_CARD_URL} target="_blank" rel="noreferrer" className="button-secondary">Read model card ↗</a>
              <a href={RELEASE_NOTES_URL} target="_blank" rel="noreferrer" className="button-secondary">Read release notes ↗</a>
            </div>
          </div>

          <div className="border border-white/10 bg-white/[0.018] p-6 sm:p-8">
            <p className="eyebrow">In five steps</p>
            <h2 className="mt-4 text-2xl font-medium">How the model works</h2>
            <ol className="mt-6 grid gap-4 text-sm leading-6 text-white/44">
              <li><span className="mr-3 font-mono text-emerald-300">01</span>Salarium scores a governed list of liquid stocks.</li>
              <li><span className="mr-3 font-mono text-emerald-300">02</span>It keeps only the strongest research candidates.</li>
              <li><span className="mr-3 font-mono text-emerald-300">03</span>It reduces duplicated risk when several stocks move together.</li>
              <li><span className="mr-3 font-mono text-emerald-300">04</span>It scales exposure down when portfolio risk is elevated.</li>
              <li><span className="mr-3 font-mono text-emerald-300">05</span>It shows the evidence and limitations instead of hiding them.</li>
            </ol>
          </div>
        </div>
      </section>

      <section className="page-section">
        <div className="border border-red-400/20 bg-red-400/[0.025] p-6 sm:p-9">
          <p className="eyebrow text-red-300">Release boundary</p>
          <h2 className="mt-4 text-3xl font-medium">This is a research project, not an investment service.</h2>
          <p className="mt-4 max-w-4xl text-sm leading-7 text-white/42">
            Salarium does not connect to a broker, place trades, or give personal investment advice. Simulated returns may not repeat. You can inspect the model, its assumptions, and its results in the linked source files.
          </p>
          <a href="/disclosures" className="button-secondary mt-7">Read full disclosures</a>
        </div>
      </section>
    </main>
  );
}

function Pillar({ number: index, title, body }: { number: string; title: string; body: string }) {
  return (
    <article className="min-h-64 border border-white/10 bg-black/25 p-6">
      <span className="font-mono text-sm text-emerald-300">{index}</span>
      <h3 className="mt-12 text-xl font-medium">{title}</h3>
      <p className="mt-3 text-sm leading-6 text-white/38">{body}</p>
    </article>
  );
}
