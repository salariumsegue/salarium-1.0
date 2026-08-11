import type { Metadata } from "next";
import Link from "next/link";

import DataStatusStrip from "@/components/data-status-strip";
import MetricCard from "@/components/metric-card";
import { ArchitectureNode } from "@/components/research-visuals";
import { humanize, percent } from "@/lib/format";
import { RELEASE_BRANCH_URL } from "@/lib/site-config";
import { loadCandidateSnapshot, loadReleaseSnapshot } from "@/lib/site-data";

export const metadata: Metadata = {
  title: "Architecture",
  description:
    "Understand Salarium's locked Liquid-500 research architecture, signal-aware covariance engine, candidate research plane, and release governance.",
  alternates: { canonical: "/architecture" },
};

export default function ArchitecturePage() {
  const release = loadReleaseSnapshot();
  const candidates = loadCandidateSnapshot();
  const architecture = release.architecture;

  const nodes = [
    {
      title: "Governed universe",
      description: `${architecture.universe} defines the portfolio research population. The broader candidate funnel remains separate.`,
    },
    {
      title: `${architecture.model_horizon_days}D alpha model`,
      description: "Annual expanding-window fits produce out-of-sample cross-sectional scores without retraining portfolio policies.",
    },
    {
      title: `${architecture.rebalance_every_days}D rebalance`,
      description: "The holding cadence was selected independently from the prediction horizon to reduce overtrading.",
    },
    {
      title: `Top-${architecture.top_n} selection`,
      description: `A rank-${architecture.buffer_rank} persistence buffer preserves concentrated signal while limiting unnecessary churn.`,
    },
    {
      title: `${architecture.covariance_lookback_days}D covariance`,
      description: `${architecture.covariance_estimator} estimates how selected securities move together, not just their standalone volatility.`,
    },
    {
      title: `${percent(architecture.signal_blend, 0)} signal blend`,
      description: "Final weights combine model conviction with covariance-risk structure under an 18% single-name cap.",
      accent: true,
    },
    {
      title: "Exposure governance",
      description: "Portfolio-level regime and drawdown controls can reduce exposure after the security weights have been formed.",
    },
    {
      title: `${architecture.leverage_cap.toFixed(2)}x hard ceiling`,
      description: "Leverage is permitted only when justified by risk controls. It is never treated as a performance target.",
    },
  ];

  return (
    <main id="main-content" className="site-main">
      <section className="page-section pb-12 pt-16 lg:pt-20">
        <div className="grid gap-10 lg:grid-cols-[1fr_0.72fr] lg:items-end">
          <div>
            <p className="eyebrow">System blueprint</p>
            <h1 className="mt-5 text-5xl font-semibold tracking-tight text-balance sm:text-7xl">
              Research architecture
              <span className="block text-white/32">built for repeatability.</span>
            </h1>
            <p className="mt-6 max-w-3xl text-base leading-7 text-white/48">
              Salarium separates alpha generation, portfolio construction, and exposure control so each layer can be tested, governed, and explained independently.
            </p>
          </div>

          <aside className="border border-white/10 bg-white/[0.018] p-6">
            <p className="eyebrow">Locked release contract</p>
            <dl className="mt-5 grid gap-4">
              <ContractRow label="Universe" value={architecture.universe} />
              <ContractRow label="Target / rebalance" value={`${architecture.model_horizon_days}D / ${architecture.rebalance_every_days}D`} />
              <ContractRow label="Portfolio" value={`Top-${architecture.top_n}, rank-${architecture.buffer_rank} buffer`} />
              <ContractRow label="Risk anchor" value={humanize(architecture.primary_risk_anchor)} />
              <ContractRow label="Leverage cap" value={`${architecture.leverage_cap.toFixed(2)}x`} />
            </dl>
          </aside>
        </div>
      </section>

      <DataStatusStrip snapshot={release} />

      <section className="page-section">
        <div className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="eyebrow">Core execution sequence</p>
            <h2 className="mt-4 text-4xl font-medium tracking-tight">Eight governed nodes.</h2>
          </div>
          <p className="max-w-md text-sm leading-6 text-white/35">
            Every node has one primary responsibility. That separation is what makes the system auditable rather than merely complicated.
          </p>
        </div>

        <div className="mt-9 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {nodes.map((node, index) => (
            <ArchitectureNode
              key={node.title}
              index={index + 1}
              title={node.title}
              description={node.description}
              accent={node.accent}
            />
          ))}
        </div>
      </section>

      <section className="page-section border-y border-white/8 bg-white/[0.012]">
        <div className="grid gap-8 lg:grid-cols-2">
          <article className="border border-emerald-400/25 bg-emerald-400/[0.035] p-6 sm:p-8">
            <p className="eyebrow text-emerald-300">Portfolio research plane</p>
            <h2 className="mt-4 text-3xl font-medium">Liquid-500 → Top-10 → governed exposure</h2>
            <p className="mt-4 text-sm leading-7 text-white/42">
              This is the locked Salarium 1.0 portfolio architecture. It uses the 20D model, 10D rebalance cadence, 60D shrinkage covariance, 25% signal-aware weighting, and a 1.25x leverage ceiling.
            </p>
            <div className="mt-6 grid grid-cols-2 gap-4">
              <MiniMetric label="Core universe" value="500" />
              <MiniMetric label="Final positions" value="10" />
              <MiniMetric label="Signal influence" value="25%" />
              <MiniMetric label="Max name weight" value="18%" />
            </div>
          </article>

          <article className="border border-white/10 bg-black/25 p-6 sm:p-8">
            <p className="eyebrow">Candidate intelligence plane</p>
            <h2 className="mt-4 text-3xl font-medium">
              {compactStage(candidates.architecture.stages[0]?.count)} → {candidates.evidence_summary.candidate_count} monitored names
            </h2>
            <p className="mt-4 text-sm leading-7 text-white/42">
              A separate broad-universe funnel supports exploratory research, evidence collection, and qualitative review. It does not silently alter the production research universe or portfolio weights.
            </p>
            <div className="mt-6 grid grid-cols-2 gap-4">
              <MiniMetric label="Broad universe" value={String(candidates.architecture.stage_counts.universe)} />
              <MiniMetric label="Quant screen" value={String(candidates.architecture.stage_counts.quantitative)} />
              <MiniMetric label="Agentic research" value={String(candidates.architecture.stage_counts.agentic)} />
              <MiniMetric label="Final candidates" value={String(candidates.evidence_summary.candidate_count)} />
            </div>
          </article>
        </div>
      </section>

      <section className="page-section">
        <div className="max-w-3xl">
          <p className="eyebrow">Institutional research principles</p>
          <h2 className="mt-4 text-4xl font-medium tracking-tight text-balance">
            The system is designed to be challenged.
          </h2>
        </div>

        <div className="mt-9 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <Principle
            title="Point-in-time discipline"
            body="Annual expanding-window training and out-of-sample score artifacts reduce the chance that future information leaks into historical decisions."
          />
          <Principle
            title="Shared-score policy testing"
            body="Portfolio policies reuse the same score artifact so performance differences can be attributed to construction and risk choices."
          />
          <Principle
            title="Explicit rejection logs"
            body="Broad-universe, horizon, breadth, covariance, and signal-blend experiments remain archived even when the hypothesis failed."
          />
          <Principle
            title="Risk before leverage"
            body="The system first controls concentration, correlation, and drawdown. A leverage cap exists, but no mandate is required to use it."
          />
          <Principle
            title="Visible limitations"
            body="Survivorship, transaction-cost, covariance, regime, and overfitting risks are shown in the product instead of buried in a footnote."
          />
          <Principle
            title="Reproducible release gates"
            body="Python tests, web linting, production builds, tracked-file audits, route smoke tests, and committed data snapshots gate release changes."
          />
        </div>
      </section>

      <section className="page-section border-y border-white/8 bg-black/45">
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            label="Research period"
            value={release.research.period}
            detail="Annual expanding-window evaluation"
          />
          <MetricCard
            label="Core rebalances"
            value={String(release.results.core_balanced.num_rebalances)}
            detail="Across the committed walk-forward record"
          />
          <MetricCard
            label="Optimizer fallback"
            value={percent(release.results.core_balanced.optimizer_fallback_rate)}
            detail="For the selected 60D constructor"
            tone="positive"
          />
          <MetricCard
            label="Effective names"
            value={release.results.core_balanced.avg_base_effective_n.toFixed(2)}
            detail="Concentrated, but not equal-weighted"
          />
        </div>
      </section>

      <section className="page-section">
        <div className="grid gap-6 lg:grid-cols-[1fr_0.8fr]">
          <div className="border border-white/10 bg-white/[0.018] p-6 sm:p-8">
            <p className="eyebrow">Reproducibility</p>
            <h2 className="mt-4 text-3xl font-medium">The public evidence points back to source.</h2>
            <p className="mt-4 text-sm leading-7 text-white/42">
              The release snapshot records the source report, branch, commit, and locked architecture. The repository includes the exporter, governance tests, research reports, and web build gates.
            </p>
            <dl className="mt-6 grid gap-4 border-t border-white/10 pt-6 sm:grid-cols-2">
              <Provenance label="Branch" value={release.provenance.git_branch} />
              <Provenance label="Commit" value={release.provenance.git_commit.slice(0, 12)} />
              <Provenance label="Source report" value={release.provenance.source_report} />
              <Provenance label="Schema" value={release.schema_version} />
            </dl>
            <div className="mt-7 flex flex-wrap gap-3">
              <a href={RELEASE_BRANCH_URL} target="_blank" rel="noreferrer" className="button-primary">
                Open release source ↗
              </a>
              <a href="/data/release_snapshot.json" className="button-secondary">
                Inspect release JSON
              </a>
            </div>
          </div>

          <div className="border border-red-400/20 bg-red-400/[0.025] p-6 sm:p-8">
            <p className="eyebrow text-red-400">System boundary</p>
            <h2 className="mt-4 text-2xl font-medium">What Salarium 1.0 does not do.</h2>
            <ul className="mt-5 grid gap-3 text-sm leading-6 text-white/42">
              <li>• It does not place live orders.</li>
              <li>• It does not promise institutional execution quality.</li>
              <li>• It does not remove survivorship, data, or overfitting risk.</li>
              <li>• It does not convert a research rank into personalized advice.</li>
            </ul>
            <Link href="/disclosures" className="text-link mt-7 inline-flex text-red-300 hover:text-red-200">
              Read complete boundaries <span aria-hidden="true">→</span>
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}

function ContractRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-5 border-t border-white/8 pt-4 first:border-t-0 first:pt-0">
      <dt className="text-[9px] uppercase tracking-[0.16em] text-white/25">{label}</dt>
      <dd className="max-w-[62%] text-right font-mono text-xs text-white/60">{value}</dd>
    </div>
  );
}

function MiniMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-white/10 bg-black/25 p-4">
      <p className="text-[8px] uppercase tracking-[0.15em] text-white/22">{label}</p>
      <p className="mt-2 font-mono text-xl text-white/80">{value}</p>
    </div>
  );
}

function Principle({ title, body }: { title: string; body: string }) {
  return (
    <article className="border border-white/10 bg-white/[0.018] p-6">
      <span className="block h-1.5 w-1.5 rounded-full bg-emerald-400" />
      <h3 className="mt-6 text-xl font-medium">{title}</h3>
      <p className="mt-3 text-sm leading-6 text-white/40">{body}</p>
    </article>
  );
}

function Provenance({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-[8px] uppercase tracking-[0.15em] text-white/22">{label}</dt>
      <dd className="mt-2 break-words font-mono text-xs text-white/55">{value}</dd>
    </div>
  );
}

function compactStage(value: number | undefined): string {
  if (typeof value !== "number") {
    return "Broad universe";
  }
  return value.toLocaleString();
}
