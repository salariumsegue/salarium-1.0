import fs from "fs";
import path from "path";

type PolicyResult = {
  policy: string;
  period: string;
  num_rebalances: number;
  avg_net_excess_5d: number;
  avg_turnover: number;
  annualized_net_return: number;
  net_sharpe: number;
  excess_sharpe: number;
  max_drawdown: number;
};

type Ranking = {
  ticker: string;
  score: number;
  volatility_20d: number;
  risk_state: string;
  regime_is_confident: boolean;
  model_configuration: string;
};

type Snapshot = {
  generated_at_utc: string;
  system: {
    name: string;
    type: string;
    research_status: string;
  };
  provenance: {
    git_commit: string;
    git_branch: string;
    git_dirty: boolean;
  };
  architecture: {
    model_fit_reduction: {
      previous_model_fits: number;
      current_model_fits: number;
      reduction_percent: number;
    };
    pipeline: string[];
  };
  research_results: {
    overall: PolicyResult[];
    yearly: PolicyResult[];
  };
  latest_signal_state: {
    date: string;
    count: number;
    rankings: Ranking[];
  };
  disclosures: string[];
};

function loadSnapshot(): Snapshot {
  const filePath = path.join(
    process.cwd(),
    "public",
    "data",
    "salarium_snapshot.json"
  );

  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function percent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

function number(value: number) {
  return value.toFixed(3);
}

export default function Home() {
  const snapshot = loadSnapshot();

  const alpha = snapshot.research_results.overall.find(
    (item) => item.policy === "baseline_equal_weight"
  );

  const risk = snapshot.research_results.overall.find(
    (item) =>
      item.policy ===
      "turnover_buffer_inverse_volatility_risk_scaled"
  );

  return (
    <main className="min-h-screen bg-black text-white">
      <div className="grid-overlay fixed inset-0 pointer-events-none" />

      <header className="relative border-b border-white/10 px-6 py-5 lg:px-12">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div>
            <p className="text-xs tracking-[0.42em] text-white/40">
              AUTONOMOUS EQUITY INTELLIGENCE
            </p>
            <h1 className="mt-2 text-2xl font-semibold tracking-[0.3em]">
              SALARIUM
            </h1>
          </div>

          <div className="flex items-center gap-3 text-xs text-white/50">
            <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" />
            SYSTEM ONLINE
          </div>
        </div>
      </header>

      <section className="relative mx-auto max-w-7xl px-6 py-16 lg:px-12">
        <div className="max-w-4xl">
          <p className="mb-5 text-sm tracking-[0.35em] text-emerald-400">
            PHASE 4 RESEARCH ARCHITECTURE
          </p>

          <h2 className="text-5xl font-semibold leading-tight tracking-tight lg:text-7xl">
            Institutional-grade
            <span className="block text-white/40">
              market intelligence.
            </span>
          </h2>

          <p className="mt-7 max-w-2xl text-base leading-7 text-white/55">
            A governed quantitative research system that trains annual
            alpha models, generates out-of-sample rankings, and evaluates
            independent portfolio policies through a shared scoring layer.
          </p>
        </div>

        <div className="mt-14 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            label="MODEL FIT REDUCTION"
            value={`${snapshot.architecture.model_fit_reduction.reduction_percent}%`}
            detail={`${snapshot.architecture.model_fit_reduction.previous_model_fits} → ${snapshot.architecture.model_fit_reduction.current_model_fits}`}
          />

          <MetricCard
            label="LATEST SIGNAL DATE"
            value={snapshot.latest_signal_state.date}
            detail={`${snapshot.latest_signal_state.count} ranked securities`}
          />

          <MetricCard
            label="ALPHA EXCESS SHARPE"
            value={alpha ? number(alpha.excess_sharpe) : "—"}
            detail="research benchmark"
          />

          <MetricCard
            label="RISK MAX DRAWDOWN"
            value={risk ? percent(risk.max_drawdown) : "—"}
            detail="risk-managed candidate"
            danger
          />
        </div>

        <div className="mt-10 grid gap-6 lg:grid-cols-[1.4fr_0.9fr]">
          <section className="panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">LIVE RESEARCH OUTPUT</p>
                <h3 className="panel-title">Top-ranked securities</h3>
              </div>
              <span className="status-chip">
                {snapshot.latest_signal_state.date}
              </span>
            </div>

            <div className="divide-y divide-white/5">
              {snapshot.latest_signal_state.rankings
                .slice(0, 10)
                .map((item, index) => (
                  <div
                    key={item.ticker}
                    className="grid grid-cols-[48px_1fr_auto_auto] items-center gap-4 py-4"
                  >
                    <span className="font-mono text-sm text-white/25">
                      {String(index + 1).padStart(2, "0")}
                    </span>

                    <div>
                      <p className="font-medium tracking-[0.2em]">
                        {item.ticker}
                      </p>
                      <p className="mt-1 text-xs text-white/35">
                        {item.model_configuration}
                      </p>
                    </div>

                    <div className="text-right">
                      <p className="font-mono text-sm text-emerald-400">
                        {item.score.toFixed(5)}
                      </p>
                      <p className="mt-1 text-[10px] tracking-[0.2em] text-white/30">
                        SCORE
                      </p>
                    </div>

                    <div className="hidden text-right sm:block">
                      <p className="font-mono text-sm text-white/70">
                        {percent(item.volatility_20d)}
                      </p>
                      <p className="mt-1 text-[10px] tracking-[0.2em] text-white/30">
                        VOL 20D
                      </p>
                    </div>
                  </div>
                ))}
            </div>
          </section>

          <section className="panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">POLICY COMPARISON</p>
                <h3 className="panel-title">Research mandates</h3>
              </div>
            </div>

            <div className="space-y-5">
              {alpha && (
                <PolicyCard
                  title="Alpha Benchmark"
                  tag="MAXIMUM SIGNAL CAPTURE"
                  result={alpha}
                />
              )}

              {risk && (
                <PolicyCard
                  title="Risk-Managed Candidate"
                  tag="CAPITAL PRESERVATION"
                  result={risk}
                  risk
                />
              )}
            </div>
          </section>
        </div>

        <section className="panel mt-6">
          <div className="panel-header">
            <div>
              <p className="eyebrow">SYSTEM ARCHITECTURE</p>
              <h3 className="panel-title">Research pipeline</h3>
            </div>
          </div>

          <div className="grid gap-3 md:grid-cols-3 lg:grid-cols-6">
            {snapshot.architecture.pipeline.map((step, index) => (
              <div
                key={step}
                className="relative border border-white/10 bg-white/[0.02] px-4 py-5"
              >
                <p className="font-mono text-xs text-emerald-400">
                  0{index + 1}
                </p>
                <p className="mt-5 text-xs uppercase leading-5 tracking-[0.18em] text-white/65">
                  {step.replaceAll("_", " ")}
                </p>
              </div>
            ))}
          </div>
        </section>

        <section className="mt-6 border border-red-500/15 bg-red-500/[0.025] p-6">
          <p className="eyebrow text-red-400">RESEARCH DISCLOSURES</p>

          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {snapshot.disclosures.map((item) => (
              <p
                key={item}
                className="text-sm leading-6 text-white/45"
              >
                {item}
              </p>
            ))}
          </div>
        </section>

        <footer className="mt-10 flex flex-col gap-3 border-t border-white/10 py-8 text-xs text-white/30 md:flex-row md:items-center md:justify-between">
          <span>
            COMMIT {snapshot.provenance.git_commit.slice(0, 12)}
          </span>
          <span>
            GENERATED{" "}
            {new Date(snapshot.generated_at_utc).toLocaleString()}
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
    <div className="border border-white/10 bg-white/[0.025] p-5 backdrop-blur">
      <p className="text-[10px] tracking-[0.24em] text-white/35">
        {label}
      </p>
      <p
        className={`mt-5 font-mono text-2xl ${
          danger ? "text-red-400" : "text-white"
        }`}
      >
        {value}
      </p>
      <p className="mt-2 text-xs text-white/30">{detail}</p>
    </div>
  );
}

function PolicyCard({
  title,
  tag,
  result,
  risk = false,
}: {
  title: string;
  tag: string;
  result: PolicyResult;
  risk?: boolean;
}) {
  return (
    <div className="border border-white/10 bg-black/40 p-5">
      <div className="flex items-start justify-between gap-5">
        <div>
          <p className="text-sm font-medium">{title}</p>
          <p
            className={`mt-2 text-[10px] tracking-[0.22em] ${
              risk ? "text-red-400" : "text-emerald-400"
            }`}
          >
            {tag}
          </p>
        </div>

        <span className="font-mono text-xs text-white/25">
          {result.num_rebalances} RUNS
        </span>
      </div>

      <div className="mt-6 grid grid-cols-2 gap-4">
        <PolicyMetric label="NET SHARPE" value={number(result.net_sharpe)} />
        <PolicyMetric
          label="EXCESS SHARPE"
          value={number(result.excess_sharpe)}
        />
        <PolicyMetric
          label="TURNOVER"
          value={number(result.avg_turnover)}
        />
        <PolicyMetric
          label="MAX DRAWDOWN"
          value={percent(result.max_drawdown)}
          danger
        />
      </div>
    </div>
  );
}

function PolicyMetric({
  label,
  value,
  danger = false,
}: {
  label: string;
  value: string;
  danger?: boolean;
}) {
  return (
    <div>
      <p className="text-[9px] tracking-[0.2em] text-white/30">
        {label}
      </p>
      <p
        className={`mt-2 font-mono text-sm ${
          danger ? "text-red-400" : "text-white/80"
        }`}
      >
        {value}
      </p>
    </div>
  );
}
