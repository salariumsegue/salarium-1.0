import SiteNav from "@/components/site-nav";
import fs from "fs";
import path from "path";
import Link from "next/link";
import RobustnessPanel, {
  type RobustnessData,
} from "@/components/robustness-panel";
import FactorExposurePanel, {
  type FactorExposureData,
} from "@/components/factor-exposure-panel";

type PolicyResult = {
  policy: string;
  period: string;
  num_rebalances: number;
  avg_net_portfolio_5d: number;
  avg_net_excess_5d: number;
  avg_long_short_5d: number;
  avg_spearman_ic: number;
  avg_turnover: number;
  avg_transaction_cost: number;
  avg_exposure: number;
  annualized_net_return: number;
  net_sharpe: number;
  excess_sharpe: number;
  max_drawdown: number;
};

type Snapshot = {
  research_results: {
    overall: PolicyResult[];
    yearly: PolicyResult[];
  };
  approved_policies: {
    alpha_benchmark: string;
    risk_managed_candidate: string;
  };
  robustness: RobustnessData;
  factor_exposure: FactorExposureData;
  generated_at_utc: string;
};

function loadSnapshot(): Snapshot {
  const filePath = path.join(
    process.cwd(),
    "public",
    "data",
    "salarium_snapshot.json"
  );

  return JSON.parse(
    fs.readFileSync(filePath, "utf8")
  );
}

function pct(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

function num(value: number) {
  return value.toFixed(3);
}

function label(policy: string) {
  if (policy === "baseline_equal_weight") {
    return "Alpha Benchmark";
  }

  return "Risk-Managed Candidate";
}

export default function ResearchPage() {
  const snapshot = loadSnapshot();

  const years = Array.from(
    new Set(
      snapshot.research_results.yearly.map(
        (item) => item.period
      )
    )
  ).sort();

  const alpha = snapshot.research_results.overall.find(
    (item) =>
      item.policy ===
      snapshot.approved_policies.alpha_benchmark
  );

  const risk = snapshot.research_results.overall.find(
    (item) =>
      item.policy ===
      snapshot.approved_policies.risk_managed_candidate
  );

  return (
    <main className="min-h-screen bg-black text-white">
      <div className="grid-overlay fixed inset-0 pointer-events-none" />

      <header className="relative border-b border-white/10 px-6 py-5 lg:px-12">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <Link href="/">
            <p className="text-xs tracking-[0.42em] text-white/40">
              AUTONOMOUS EQUITY INTELLIGENCE
            </p>
            <h1 className="mt-2 text-2xl font-semibold tracking-[0.3em]">
              SALARIUM
            </h1>
          </Link>

          <SiteNav active="research" />
        </div>
      </header>

      <section className="relative mx-auto max-w-7xl px-6 py-14 lg:px-12">
        <div className="max-w-4xl">
          <p className="eyebrow">WALK-FORWARD EVIDENCE</p>

          <h2 className="mt-4 text-5xl font-semibold tracking-tight lg:text-6xl">
            Research history
            <span className="block text-white/35">
              across market regimes.
            </span>
          </h2>

          <p className="mt-6 max-w-2xl text-base leading-7 text-white/50">
            Annual expanding-window evaluation from 2021 through 2026,
            comparing maximum signal capture against a risk-managed
            portfolio policy.
          </p>
        </div>

        <div className="mt-12 grid gap-4 md:grid-cols-2">
          {alpha && (
            <OverallCard
              title="Alpha Benchmark"
              subtitle="Maximum signal capture"
              result={alpha}
            />
          )}

          {risk && (
            <OverallCard
              title="Risk-Managed Candidate"
              subtitle="Reduced exposure and drawdown"
              result={risk}
              risk
            />
          )}
        </div>

        <section className="panel mt-6">
          <div className="panel-header">
            <div>
              <p className="eyebrow">YEARLY COMPARISON</p>
              <h3 className="panel-title">
                Out-of-sample performance
              </h3>
            </div>

            <span className="status-chip">
              {years[0]}–{years[years.length - 1]}
            </span>
          </div>

          <div className="overflow-x-auto">
            <div className="min-w-[980px]">
              <div className="grid grid-cols-[90px_1.2fr_130px_130px_130px_130px] border-b border-white/10 px-4 py-3 text-[10px] tracking-[0.18em] text-white/30">
                <span>YEAR</span>
                <span>POLICY</span>
                <span>NET RETURN</span>
                <span>EXCESS SHARPE</span>
                <span>TURNOVER</span>
                <span>MAX DRAWDOWN</span>
              </div>

              <div className="divide-y divide-white/5">
                {years.flatMap((year) =>
                  snapshot.research_results.yearly
                    .filter((item) => item.period === year)
                    .map((item) => (
                      <div
                        key={`${year}-${item.policy}`}
                        className="grid grid-cols-[90px_1.2fr_130px_130px_130px_130px] items-center px-4 py-4"
                      >
                        <span className="font-mono text-sm text-white/40">
                          {year}
                        </span>

                        <div>
                          <p className="text-sm text-white/80">
                            {label(item.policy)}
                          </p>
                          <p className="mt-1 font-mono text-[10px] text-white/25">
                            {item.policy}
                          </p>
                        </div>

                        <span className="font-mono text-sm text-white/70">
                          {pct(item.annualized_net_return)}
                        </span>

                        <span
                          className={`font-mono text-sm ${
                            item.excess_sharpe >= 0
                              ? "text-emerald-400"
                              : "text-red-400"
                          }`}
                        >
                          {num(item.excess_sharpe)}
                        </span>

                        <span className="font-mono text-sm text-white/60">
                          {num(item.avg_turnover)}
                        </span>

                        <span className="font-mono text-sm text-red-400">
                          {pct(item.max_drawdown)}
                        </span>
                      </div>
                    ))
                )}
              </div>
            </div>
          </div>
        </section>

        <RobustnessPanel
          robustness={snapshot.robustness}
        />

        <FactorExposurePanel
          data={snapshot.factor_exposure}
        />

        <section className="mt-6 grid gap-6 lg:grid-cols-3">
          <Insight
            label="ALPHA"
            title="The benchmark captures more upside."
            body="The equal-weight benchmark retains the strongest overall excess Sharpe and net excess return, but requires substantially more turnover."
          />

          <Insight
            label="RISK"
            title="Exposure scaling improves survival."
            body="The risk-managed candidate materially reduces maximum drawdown and transaction costs while preserving most of the benchmark's risk-adjusted performance."
            risk
          />

          <Insight
            label="METHOD"
            title="Every policy uses identical scores."
            body="Both portfolio policies are evaluated from the same out-of-sample score artifact, isolating portfolio construction from alpha-model training."
          />
        </section>

        <footer className="mt-10 border-t border-white/10 py-8 text-xs text-white/30">
          Snapshot generated{" "}
          {new Date(snapshot.generated_at_utc).toLocaleString()}
        </footer>
      </section>
    </main>
  );
}

function OverallCard({
  title,
  subtitle,
  result,
  risk = false,
}: {
  title: string;
  subtitle: string;
  result: PolicyResult;
  risk?: boolean;
}) {
  return (
    <div className="border border-white/10 bg-white/[0.025] p-6">
      <div className="flex items-start justify-between gap-6">
        <div>
          <p className="text-lg font-medium">{title}</p>
          <p
            className={`mt-2 text-[10px] tracking-[0.2em] ${
              risk ? "text-red-400" : "text-emerald-400"
            }`}
          >
            {subtitle.toUpperCase()}
          </p>
        </div>

        <span className="font-mono text-xs text-white/25">
          {result.num_rebalances} REBALANCES
        </span>
      </div>

      <div className="mt-7 grid grid-cols-2 gap-5">
        <Metric
          label="ANNUALIZED NET"
          value={pct(result.annualized_net_return)}
        />
        <Metric
          label="NET SHARPE"
          value={num(result.net_sharpe)}
        />
        <Metric
          label="EXCESS SHARPE"
          value={num(result.excess_sharpe)}
        />
        <Metric
          label="MAX DRAWDOWN"
          value={pct(result.max_drawdown)}
          danger
        />
      </div>
    </div>
  );
}

function Metric({
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
        className={`mt-2 font-mono text-lg ${
          danger ? "text-red-400" : "text-white/80"
        }`}
      >
        {value}
      </p>
    </div>
  );
}

function Insight({
  label,
  title,
  body,
  risk = false,
}: {
  label: string;
  title: string;
  body: string;
  risk?: boolean;
}) {
  return (
    <div className="border border-white/10 bg-white/[0.02] p-6">
      <p
        className={`text-[10px] tracking-[0.22em] ${
          risk ? "text-red-400" : "text-emerald-400"
        }`}
      >
        {label}
      </p>

      <h3 className="mt-5 text-lg font-medium">
        {title}
      </h3>

      <p className="mt-4 text-sm leading-6 text-white/45">
        {body}
      </p>
    </div>
  );
}
