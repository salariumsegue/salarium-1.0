import type { Metadata } from "next";

import DataStatusStrip from "@/components/data-status-strip";
import MetricCard from "@/components/metric-card";
import { GITHUB_URL, MODEL_CARD_URL, RELEASE_NOTES_URL } from "@/lib/site-config";
import { loadReleaseSnapshot } from "@/lib/site-data";

export const metadata: Metadata = {
  title: "About",
  description:
    "Learn why Salarium was built, how the project approaches quantitative research, and where the open-source release draws its boundaries.",
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
              Build research that
              <span className="block text-white/32">can survive questions.</span>
            </h1>
            <p className="mt-6 max-w-3xl text-base leading-7 text-white/48">
              Salarium is an open-source equity-research system built to connect finance intuition with reproducible software: governed data, walk-forward learning, transparent portfolio construction, and explicit risk controls.
            </p>
          </div>

          <aside className="border border-emerald-400/25 bg-emerald-400/[0.035] p-6 sm:p-8">
            <p className="eyebrow text-emerald-300">The standard</p>
            <blockquote className="mt-5 text-2xl font-medium leading-9 tracking-[-0.025em] text-white/85">
              A result is only useful when another person can trace how it was produced, what assumptions shaped it, and where it can fail.
            </blockquote>
          </aside>
        </div>
      </section>

      <DataStatusStrip snapshot={release} />

      <section className="page-section">
        <div className="grid gap-10 lg:grid-cols-[0.75fr_1.25fr]">
          <div>
            <p className="eyebrow">Project identity</p>
            <h2 className="mt-4 text-4xl font-medium tracking-tight">Finance, engineering, and research governance.</h2>
          </div>
          <div className="space-y-6 text-base leading-8 text-white/45">
            <p>
              Salarium began as a systematic stock-ranking project and evolved into a modular research platform. The system now separates universe governance, feature construction, annual walk-forward models, portfolio optimization, exposure control, candidate intelligence, evidence export, and public presentation.
            </p>
            <p>
              The project is built by Niall Gillen, a finance student at Indiana University&apos;s Kelley School of Business, as a serious demonstration of quantitative research, software architecture, and the ability to turn iterative analysis into a coherent product.
            </p>
            <p>
              The name references the Roman <em>salarium</em>—historically associated with compensation and the linguistic root of “salary.” The modern project uses that idea as a symbol for disciplined capital allocation rather than as a claim about Roman payment practices.
            </p>
          </div>
        </div>
      </section>

      <section className="page-section border-y border-white/8 bg-white/[0.012]">
        <div className="max-w-3xl">
          <p className="eyebrow">What makes the work credible</p>
          <h2 className="mt-4 text-4xl font-medium tracking-tight">Not one model. A governed research chain.</h2>
        </div>
        <div className="mt-9 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Pillar number="01" title="Point-in-time discipline" body="The research process uses annual expanding-window fits and preserves out-of-sample score artifacts." />
          <Pillar number="02" title="Controlled comparison" body="Portfolio, horizon, breadth, covariance, and signal-weight hypotheses are compared under shared score streams." />
          <Pillar number="03" title="Visible failure" body="Experiments that degraded performance remain archived rather than disappearing from the narrative." />
          <Pillar number="04" title="Release governance" body="Tests, audits, static builds, route validation, and committed JSON evidence gate the public release." />
        </div>
      </section>

      <section className="page-section">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard label="Research universe" value={release.architecture.universe} detail="Locked portfolio-research population" />
          <MetricCard label="Prediction / rebalance" value={`${release.architecture.model_horizon_days}D / ${release.architecture.rebalance_every_days}D`} detail="Horizon and trading cadence tested separately" />
          <MetricCard label="Portfolio breadth" value={`Top-${release.architecture.top_n}`} detail={`Rank-${release.architecture.buffer_rank} persistence buffer`} />
          <MetricCard label="Leverage ceiling" value={`${release.architecture.leverage_cap.toFixed(2)}x`} detail="Permission ceiling, not a usage objective" />
        </div>
      </section>

      <section className="page-section border-y border-white/8 bg-black/45">
        <div className="grid gap-8 lg:grid-cols-[1fr_0.85fr]">
          <div>
            <p className="eyebrow">For technical reviewers</p>
            <h2 className="mt-4 text-3xl font-medium">Inspect the implementation, not just the interface.</h2>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-white/42">
              The repository contains model-generation scripts, portfolio evaluators, experiment reports, release-snapshot exporters, governance tests, and the Next.js public product. The public interface is intentionally linked back to committed source evidence.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <a href={GITHUB_URL} target="_blank" rel="noreferrer" className="button-primary">Open source repository ↗</a>
              <a href={MODEL_CARD_URL} target="_blank" rel="noreferrer" className="button-secondary">Read model card ↗</a>
              <a href={RELEASE_NOTES_URL} target="_blank" rel="noreferrer" className="button-secondary">Read release notes ↗</a>
            </div>
          </div>

          <div className="border border-white/10 bg-white/[0.018] p-6 sm:p-8">
            <p className="eyebrow">For non-technical visitors</p>
            <h2 className="mt-4 text-2xl font-medium">The simple version.</h2>
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
          <h2 className="mt-4 text-3xl font-medium">Salarium 1.0 is a research release.</h2>
          <p className="mt-4 max-w-4xl text-sm leading-7 text-white/42">
            It does not connect to a brokerage, execute orders, provide personalized advice, or claim that simulated returns will repeat. The value of the release is the architecture, evidence discipline, and reproducibility of the research process.
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
