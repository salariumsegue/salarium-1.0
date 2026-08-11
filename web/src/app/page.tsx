import SiteNav from "@/components/site-nav";
import fs from "fs";
import path from "path";

type LegacyRanking = {
  ticker: string;
  score: number;
  volatility_20d: number;
  risk_state: string;
  regime_is_confident: boolean;
  model_configuration: string;
};

type LegacySnapshot = {
  latest_signal_state: {
    date: string;
    count: number;
    rankings: LegacyRanking[];
  };
};

type Result = {
  risk_anchor: string;
  signal_blend: number;
  exposure_policy: string;
  annualized_net_return: number;
  net_sharpe: number;
  net_sortino: number;
  max_drawdown: number;
  annualized_net_volatility: number;
  avg_exposure: number;
  max_exposure: number;
};

type ReleaseSnapshot = {
  generated_at_utc: string;
  release: {
    name: string;
    version: string;
    status: string;
  };
  architecture: {
    universe: string;
    model_horizon_days: number;
    rebalance_every_days: number;
    top_n: number;
    buffer_rank: number;
    covariance_estimator: string;
    covariance_lookback_days: number;
    primary_risk_anchor: string;
    signal_blend: number;
    leverage_cap: number;
  };
  results: {
    core_balanced: Result;
    pure_risk_anchor: Result;
    aggressive: Result;
    defensive: Result;
  };
  provenance: {
    git_branch: string;
    git_commit: string;
    git_dirty: boolean;
  };
};

function loadJson<T>(filename: string): T {
  const filePath = path.join(process.cwd(), "public", "data", filename);
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function pct(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

function num(value: number) {
  return value.toFixed(3);
}

function readable(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export default function Home() {
  const release = loadJson<ReleaseSnapshot>("release_snapshot.json");
  const legacy = loadJson<LegacySnapshot>("salarium_snapshot.json");
  const core = release.results.core_balanced;
  const aggressive = release.results.aggressive;
  const defensive = release.results.defensive;

  const architecture = [
    `${release.architecture.universe} research universe`,
    `${release.architecture.model_horizon_days}D alpha target`,
    `${release.architecture.rebalance_every_days}D rebalance`,
    `Top-${release.architecture.top_n} concentration`,
    `${release.architecture.covariance_lookback_days}D shrinkage covariance`,
    `${Math.round(release.architecture.signal_blend * 100)}% signal-aware weighting`,
  ];

  return (
    <main className="min-h-screen bg-black text-white">
      <div className="grid-overlay fixed inset-0 pointer-events-none" />
      <header className="relative border-b border-white/10 px-6 py-5 lg:px-12">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div>
            <p className="text-xs tracking-[0.42em] text-white/40">AUTONOMOUS EQUITY INTELLIGENCE</p>
            <h1 className="mt-2 text-2xl font-semibold tracking-[0.3em]">SALARIUM</h1>
          </div>
          <div className="flex items-center gap-3 text-xs text-white/50">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            RESEARCH BUILD ONLINE
          </div>
        </div>
        <div className="mx-auto flex max-w-7xl justify-end px-6 pb-5 lg:px-12">
          <SiteNav active="overview" />
        </div>
      </header>

      <section className="relative mx-auto max-w-7xl px-6 py-16 lg:px-12">
        <div className="max-w-5xl">
          <p className="mb-5 text-sm tracking-[0.35em] text-emerald-400">SALARIUM 1.0 RELEASE CANDIDATE</p>
          <h2 className="text-5xl font-semibold leading-tight tracking-tight lg:text-7xl">
            Concentrated alpha.
            <span className="block text-white/40">Governed portfolio risk.</span>
          </h2>
          <p className="mt-7 max-w-3xl text-base leading-7 text-white/55">
            An open-source quantitative equity research platform combining expanding-window walk-forward models,
            covariance-aware portfolio construction, signal-aware weighting, macro/risk controls, and reproducible research artifacts.
          </p>
          <p className="mt-4 max-w-3xl text-sm leading-6 text-white/35">
            Historical results shown below are simulated research results, not live trading performance or investment advice.
          </p>
        </div>

        <div className="mt-14 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <MetricCard label="CORE NET RETURN" value={pct(core.annualized_net_return)} detail="simulated annualized" />
          <MetricCard label="CORE NET SHARPE" value={num(core.net_sharpe)} detail="2021–2026 walk-forward" />
          <MetricCard label="CORE MAX DRAWDOWN" value={pct(core.max_drawdown)} detail="simulated" danger />
          <MetricCard label="MAX LEVERAGE" value={`${release.architecture.leverage_cap.toFixed(2)}x`} detail="hard governance ceiling" />
        </div>

        <div className="mt-10 grid gap-6 lg:grid-cols-[1.35fr_0.95fr]">
          <section className="panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">LOCKED RELEASE ARCHITECTURE</p>
                <h3 className="panel-title">Research pipeline</h3>
              </div>
              <span className="status-chip">{release.release.version.toUpperCase()}</span>
            </div>
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
              {architecture.map((item, index) => (
                <div key={item} className="border border-white/10 bg-black/30 p-5">
                  <p className="font-mono text-xs text-emerald-400">0{index + 1}</p>
                  <p className="mt-5 text-xs uppercase leading-5 tracking-[0.16em] text-white/65">{item}</p>
                </div>
              ))}
            </div>
            <div className="mt-4 border border-white/10 bg-white/[0.02] p-5">
              <p className="text-[10px] tracking-[0.22em] text-white/30">PRIMARY RISK ANCHOR</p>
              <p className="mt-3 text-sm text-white/70">{readable(release.architecture.primary_risk_anchor)}</p>
              <p className="mt-2 text-xs leading-5 text-white/35">
                Final Top-10 weights combine 75% covariance-risk structure with 25% model-signal influence before portfolio-level exposure control.
              </p>
            </div>
          </section>

          <section className="panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">RESEARCH MANDATES</p>
                <h3 className="panel-title">One model, multiple risk postures</h3>
              </div>
            </div>
            <div className="space-y-4">
              <PolicyCard title="Core Balanced" tag="RELEASE CANDIDATE" result={core} />
              <PolicyCard title="Aggressive Reference" tag="STATIC 1.00X" result={aggressive} />
              <PolicyCard title="Defensive Reference" tag="MINIMUM VARIANCE" result={defensive} risk />
            </div>
          </section>
        </div>

        <section className="panel mt-6">
          <div className="panel-header">
            <div>
              <p className="eyebrow">LATEST COMMITTED SIGNAL OUTPUT</p>
              <h3 className="panel-title">Top-ranked securities</h3>
            </div>
            <span className="status-chip">{legacy.latest_signal_state.date}</span>
          </div>
          <p className="mb-5 text-xs leading-5 text-white/35">
            This is the latest ranking snapshot committed to the repository. It is not represented as a live market feed.
          </p>
          <div className="divide-y divide-white/5">
            {legacy.latest_signal_state.rankings.slice(0, 10).map((item, index) => (
              <div key={item.ticker} className="grid grid-cols-[48px_1fr_auto_auto] items-center gap-4 py-4">
                <span className="font-mono text-sm text-white/25">{String(index + 1).padStart(2, "0")}</span>
                <div>
                  <p className="font-medium tracking-[0.2em]">{item.ticker}</p>
                  <p className="mt-1 text-xs text-white/35">{readable(item.risk_state)}</p>
                </div>
                <div className="text-right">
                  <p className="font-mono text-sm text-emerald-400">{item.score.toFixed(5)}</p>
                  <p className="mt-1 text-[10px] tracking-[0.2em] text-white/30">SCORE</p>
                </div>
                <div className="hidden text-right sm:block">
                  <p className="font-mono text-sm text-white/70">{pct(item.volatility_20d)}</p>
                  <p className="mt-1 text-[10px] tracking-[0.2em] text-white/30">VOL 20D</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="mt-6 border border-red-500/15 bg-red-500/[0.025] p-6">
          <p className="eyebrow text-red-400">RESEARCH DISCLOSURE</p>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <p className="text-sm leading-6 text-white/45">Historical results are simulated and do not represent live trading performance.</p>
            <p className="text-sm leading-6 text-white/45">The system remains exposed to data, model, universe-selection, transaction-cost, and regime risks.</p>
            <p className="text-sm leading-6 text-white/45">The 1.25x leverage limit is a hard ceiling, not a target. The current core research run did not exceed 1.00x.</p>
            <p className="text-sm leading-6 text-white/45">Salarium is an educational and research system and does not provide investment advice.</p>
          </div>
        </section>

        <footer className="mt-10 flex flex-col gap-3 border-t border-white/10 py-8 text-xs text-white/30 md:flex-row md:items-center md:justify-between">
          <span>COMMIT {release.provenance.git_commit.slice(0, 12)}</span>
          <span>RELEASE SNAPSHOT {new Date(release.generated_at_utc).toLocaleString()}</span>
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
      <p className="text-[10px] tracking-[0.24em] text-white/35">{label}</p>
      <p className={`mt-5 font-mono text-2xl ${danger ? "text-red-400" : "text-white"}`}>{value}</p>
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
  result: Result;
  risk?: boolean;
}) {
  return (
    <div className="border border-white/10 bg-black/40 p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium">{title}</p>
          <p className={`mt-2 text-[10px] tracking-[0.22em] ${risk ? "text-red-400" : "text-emerald-400"}`}>{tag}</p>
        </div>
        <span className="font-mono text-xs text-white/30">{result.avg_exposure.toFixed(3)}x AVG</span>
      </div>
      <div className="mt-5 grid grid-cols-2 gap-4">
        <PolicyMetric label="NET RETURN" value={pct(result.annualized_net_return)} />
        <PolicyMetric label="NET SHARPE" value={num(result.net_sharpe)} />
        <PolicyMetric label="SORTINO" value={num(result.net_sortino)} />
        <PolicyMetric label="MAX DD" value={pct(result.max_drawdown)} danger />
      </div>
    </div>
  );
}

function PolicyMetric({ label, value, danger = false }: { label: string; value: string; danger?: boolean }) {
  return (
    <div>
      <p className="text-[9px] tracking-[0.2em] text-white/30">{label}</p>
      <p className={`mt-2 font-mono text-sm ${danger ? "text-red-400" : "text-white/80"}`}>{value}</p>
    </div>
  );
}
