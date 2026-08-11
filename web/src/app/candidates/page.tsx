import fs from "fs";
import path from "path";
import Link from "next/link";

import SiteNav from "@/components/site-nav";

type Stage = {
  key: string;
  label: string;
  count: number;
  description: string;
};

type CandidateScores = {
  agentic: number | null;
  advanced: number | null;
  model: number | null;
  quantitative: number | null;
  fundamental: number | null;
  risk: number | null;
  catalyst: number | null;
  macro_fit: number | null;
  evidence: number | null;
  confidence: number | null;
};

type Candidate = {
  rank: number;
  ticker: string;
  company_name: string | null;
  exchange: string | null;
  security_type: string | null;
  last_price: number | null;
  median_dollar_volume: number | null;
  scores: CandidateScores;
  model_uncertainty: number | null;
  drawdown_resilience: number | null;
  data_quality_score: number | null;
  red_flag_count: number;
  evidence_count: number;
  source_types: string[];
  primary_evidence_supported: boolean;
  external_catalyst_evidence: boolean;
  review_status: string;
  thesis: string | null;
  risk_summary: string | null;
  catalyst_summary: string | null;
};

type CandidateSnapshot = {
  generated_at_utc: string;
  as_of_date: string | null;
  provenance: {
    run_id: string;
    run_created_at_utc: string;
    git: {
      commit?: string;
      branch?: string;
      dirty?: boolean;
    };
  };
  architecture: {
    stages: Stage[];
    stage_counts: Record<string, number>;
  };
  evidence_summary: {
    candidate_count: number;
    primary_evidence_supported: number;
    internal_evidence_only: number;
    external_catalyst_evidence: number;
    neutral_catalyst_assessments: number;
    fundamental_neutral_assessments: number;
    red_flag_free_candidates: number;
    high_confidence_candidates: number;
    confidence_cap_without_primary: number;
  };
  candidates: Candidate[];
  disclosures: string[];
};

function loadSnapshot(): CandidateSnapshot {
  const filePath = path.join(
    process.cwd(),
    "public",
    "data",
    "candidate_funnel_snapshot.json"
  );

  return JSON.parse(
    fs.readFileSync(
      filePath,
      "utf8"
    )
  );
}

function formatScore(
  value: number | null,
  decimals = 3
) {
  return typeof value === "number"
    ? value.toFixed(decimals)
    : "—";
}

function formatPercent(
  value: number | null
) {
  return typeof value === "number"
    ? `${(value * 100).toFixed(1)}%`
    : "—";
}

function formatMoney(
  value: number | null
) {
  if (typeof value !== "number") {
    return "—";
  }

  if (value >= 1_000_000_000) {
    return `$${(
      value / 1_000_000_000
    ).toFixed(1)}B`;
  }

  if (value >= 1_000_000) {
    return `$${(
      value / 1_000_000
    ).toFixed(1)}M`;
  }

  return `$${value.toLocaleString()}`;
}

export default function CandidatesPage() {
  const snapshot = loadSnapshot();

  return (
    <main className="min-h-screen bg-black text-white">
      <div className="grid-overlay pointer-events-none fixed inset-0" />

      <header className="relative border-b border-white/10 px-6 py-5 lg:px-12">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-8">
          <Link href="/">
            <p className="text-xs tracking-[0.42em] text-white/40">
              AUTONOMOUS EQUITY INTELLIGENCE
            </p>

            <h1 className="mt-2 text-2xl font-semibold tracking-[0.3em]">
              SALARIUM
            </h1>
          </Link>

          <SiteNav active="candidates" />
        </div>
      </header>

      <section className="relative mx-auto max-w-7xl px-6 py-14 lg:px-12">
        <div className="max-w-5xl">
          <p className="eyebrow">
            CANDIDATE INTELLIGENCE
          </p>

          <h2 className="mt-4 text-5xl font-semibold tracking-tight lg:text-7xl">
            From market universe
            <span className="block text-white/35">
              to governed conviction.
            </span>
          </h2>

          <p className="mt-6 max-w-3xl text-base leading-7 text-white/50">
            Salarium compresses a broad liquid
            universe through quantitative,
            advanced-model, and evidence-governed
            research layers. The final names are
            monitored research candidates—not
            trades, allocations, or investment
            recommendations.
          </p>
        </div>

        <section className="mt-12 grid gap-3 md:grid-cols-3 lg:grid-cols-6">
          {snapshot.architecture.stages.map(
            (stage, index) => (
              <div
                key={stage.key}
                className="relative min-h-44 border border-white/10 bg-white/[0.018] p-5"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[10px] text-emerald-400">
                    STAGE{" "}
                    {String(
                      index + 1
                    ).padStart(2, "0")}
                  </span>

                  <span className="h-1.5 w-1.5 rounded-full bg-white/25" />
                </div>

                <p className="mt-8 font-mono text-3xl text-white/90">
                  {stage.count.toLocaleString()}
                </p>

                <p className="mt-3 text-[10px] uppercase tracking-[0.16em] text-white/55">
                  {stage.label}
                </p>

                <p className="mt-3 text-xs leading-5 text-white/30">
                  {stage.description}
                </p>

                {index <
                  snapshot.architecture
                    .stages.length -
                    1 && (
                  <span className="absolute -right-3 top-1/2 z-10 hidden text-white/20 lg:block">
                    →
                  </span>
                )}
              </div>
            )
          )}
        </section>

        <section className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            label="FINAL RESEARCH SET"
            value={String(
              snapshot.evidence_summary
                .candidate_count
            )}
            detail="governed candidates"
          />

          <MetricCard
            label="PRIMARY EVIDENCE"
            value={String(
              snapshot.evidence_summary
                .primary_evidence_supported
            )}
            detail="filing-supported names"
          />

          <MetricCard
            label="INTERNAL ONLY"
            value={String(
              snapshot.evidence_summary
                .internal_evidence_only
            )}
            detail="confidence-capped names"
          />

          <MetricCard
            label="EXTERNAL CATALYSTS"
            value={String(
              snapshot.evidence_summary
                .external_catalyst_evidence
            )}
            detail="currently verified"
            danger={
              snapshot.evidence_summary
                .external_catalyst_evidence ===
              0
            }
          />
        </section>

        <section className="panel mt-6">
          <div className="panel-header">
            <div>
              <p className="eyebrow">
                FINAL RESEARCH CANDIDATES
              </p>

              <h3 className="panel-title">
                Evidence-weighted candidate stack
              </h3>
            </div>

            <span className="status-chip">
              {snapshot.as_of_date ??
                "LATEST COMPLETE RUN"}
            </span>
          </div>

          <div className="overflow-x-auto">
            <div className="min-w-[1040px]">
              <div className="grid grid-cols-[60px_90px_1.3fr_repeat(5,110px)] border-b border-white/10 px-4 py-3 text-[9px] tracking-[0.15em] text-white/30">
                <span>RANK</span>
                <span>TICKER</span>
                <span>EVIDENCE STATUS</span>
                <span>AGENTIC</span>
                <span>MODEL</span>
                <span>QUANT</span>
                <span>FUND.</span>
                <span>CONF.</span>
              </div>

              <div className="divide-y divide-white/5">
                {snapshot.candidates.map(
                  (candidate) => (
                    <div
                      key={candidate.ticker}
                      className="grid grid-cols-[60px_90px_1.3fr_repeat(5,110px)] items-center px-4 py-4 transition hover:bg-white/[0.02]"
                    >
                      <span className="font-mono text-sm text-white/25">
                        {String(
                          candidate.rank
                        ).padStart(2, "0")}
                      </span>

                      <div>
                        <p className="font-medium tracking-[0.16em]">
                          {candidate.ticker}
                        </p>

                        <p className="mt-1 text-[10px] text-white/25">
                          {candidate.exchange ?? "—"}
                        </p>
                      </div>

                      <div className="flex items-center gap-3">
                        <span
                          className={`inline-flex border px-2 py-1 text-[9px] tracking-[0.12em] ${
                            candidate.primary_evidence_supported
                              ? "border-emerald-500/25 text-emerald-400"
                              : "border-white/10 text-white/35"
                          }`}
                        >
                          {candidate.primary_evidence_supported
                            ? "PRIMARY SUPPORTED"
                            : "INTERNAL ONLY"}
                        </span>

                        {candidate.red_flag_count >
                          0 && (
                          <span className="text-[9px] tracking-[0.12em] text-red-400">
                            {
                              candidate.red_flag_count
                            }{" "}
                            FLAG
                          </span>
                        )}
                      </div>

                      <ScoreCell
                        value={
                          candidate.scores.agentic
                        }
                      />

                      <ScoreCell
                        value={
                          candidate.scores.model
                        }
                        decimals={5}
                      />

                      <ScoreCell
                        value={
                          candidate.scores
                            .quantitative
                        }
                      />

                      <ScoreCell
                        value={
                          candidate.scores
                            .fundamental
                        }
                      />

                      <ScoreCell
                        value={
                          candidate.scores
                            .confidence
                        }
                        accent={
                          candidate
                            .primary_evidence_supported
                        }
                      />
                    </div>
                  )
                )}
              </div>
            </div>
          </div>
        </section>

        <section className="mt-6 grid gap-4 lg:grid-cols-2">
          {snapshot.candidates.map(
            (candidate) => (
              <details
                key={candidate.ticker}
                className="group border border-white/10 bg-white/[0.018] open:bg-white/[0.028]"
              >
                <summary className="flex cursor-pointer list-none items-center justify-between gap-6 p-5">
                  <div className="flex items-center gap-5">
                    <span className="font-mono text-xs text-white/25">
                      {String(
                        candidate.rank
                      ).padStart(2, "0")}
                    </span>

                    <div>
                      <p className="text-lg font-medium tracking-[0.18em]">
                        {candidate.ticker}
                      </p>

                      <p className="mt-1 max-w-sm truncate text-xs text-white/30">
                        {candidate.company_name ??
                          "Research candidate"}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-5">
                    <div className="text-right">
                      <p className="font-mono text-sm text-emerald-400">
                        {formatScore(
                          candidate.scores
                            .agentic
                        )}
                      </p>

                      <p className="mt-1 text-[9px] tracking-[0.15em] text-white/25">
                        AGENTIC
                      </p>
                    </div>

                    <span className="text-white/25 transition group-open:rotate-45">
                      +
                    </span>
                  </div>
                </summary>

                <div className="border-t border-white/10 p-5">
                  <div className="grid gap-4 sm:grid-cols-3">
                    <DetailMetric
                      label="FUNDAMENTAL"
                      value={formatScore(
                        candidate.scores
                          .fundamental
                      )}
                    />

                    <DetailMetric
                      label="RISK"
                      value={formatScore(
                        candidate.scores.risk
                      )}
                    />

                    <DetailMetric
                      label="MACRO FIT"
                      value={formatScore(
                        candidate.scores
                          .macro_fit
                      )}
                    />

                    <DetailMetric
                      label="EVIDENCE"
                      value={formatScore(
                        candidate.scores
                          .evidence
                      )}
                    />

                    <DetailMetric
                      label="CONFIDENCE"
                      value={formatPercent(
                        candidate.scores
                          .confidence
                      )}
                    />

                    <DetailMetric
                      label="LIQUIDITY"
                      value={formatMoney(
                        candidate
                          .median_dollar_volume
                      )}
                    />
                  </div>

                  <div className="mt-6 space-y-5">
                    <ResearchText
                      label="THESIS"
                      value={candidate.thesis}
                    />

                    <ResearchText
                      label="RISK ASSESSMENT"
                      value={
                        candidate.risk_summary
                      }
                      danger
                    />

                    <ResearchText
                      label="CATALYST STATUS"
                      value={
                        candidate.catalyst_summary
                      }
                    />
                  </div>

                  <div className="mt-6 flex flex-wrap gap-2">
                    {candidate.source_types.map(
                      (sourceType) => (
                        <span
                          key={sourceType}
                          className="border border-white/10 px-2 py-1 font-mono text-[9px] text-white/30"
                        >
                          {sourceType
                            .replaceAll(
                              "_",
                              " "
                            )
                            .toUpperCase()}
                        </span>
                      )
                    )}
                  </div>
                </div>
              </details>
            )
          )}
        </section>

        <section className="mt-6 border border-red-500/15 bg-red-500/[0.025] p-6">
          <p className="eyebrow text-red-400">
            CANDIDATE DISCLOSURES
          </p>

          <div className="mt-5 grid gap-4 md:grid-cols-2">
            {snapshot.disclosures.map(
              (disclosure) => (
                <p
                  key={disclosure}
                  className="text-sm leading-6 text-white/45"
                >
                  {disclosure}
                </p>
              )
            )}
          </div>
        </section>

        <footer className="mt-10 flex flex-col gap-3 border-t border-white/10 py-8 font-mono text-[10px] text-white/25 md:flex-row md:items-center md:justify-between">
          <span>
            RUN {snapshot.provenance.run_id}
          </span>

          <span>
            GENERATED{" "}
            {new Date(
              snapshot.generated_at_utc
            ).toLocaleString()}
          </span>
        </footer>
      </section>
    </main>
  );
}

function MetricCard({
  label,
  value,
  detail,
  danger = false,
}: {
  label: string;
  value: string;
  detail: string;
  danger?: boolean;
}) {
  return (
    <div className="border border-white/10 bg-white/[0.022] p-5">
      <p className="text-[9px] tracking-[0.2em] text-white/30">
        {label}
      </p>

      <p
        className={`mt-5 font-mono text-3xl ${
          danger
            ? "text-red-400"
            : "text-white"
        }`}
      >
        {value}
      </p>

      <p className="mt-2 text-xs text-white/30">
        {detail}
      </p>
    </div>
  );
}

function ScoreCell({
  value,
  decimals = 3,
  accent = false,
}: {
  value: number | null;
  decimals?: number;
  accent?: boolean;
}) {
  return (
    <span
      className={`font-mono text-sm ${
        accent
          ? "text-emerald-400"
          : "text-white/65"
      }`}
    >
      {formatScore(
        value,
        decimals
      )}
    </span>
  );
}

function DetailMetric({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="border border-white/10 bg-black/30 p-4">
      <p className="text-[9px] tracking-[0.16em] text-white/25">
        {label}
      </p>

      <p className="mt-2 font-mono text-sm text-white/70">
        {value}
      </p>
    </div>
  );
}

function ResearchText({
  label,
  value,
  danger = false,
}: {
  label: string;
  value: string | null;
  danger?: boolean;
}) {
  return (
    <div>
      <p
        className={`text-[9px] tracking-[0.18em] ${
          danger
            ? "text-red-400"
            : "text-emerald-400"
        }`}
      >
        {label}
      </p>

      <p className="mt-2 text-sm leading-6 text-white/45">
        {value ?? "No assessment available."}
      </p>
    </div>
  );
}
