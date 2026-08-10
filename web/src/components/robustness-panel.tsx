export type RobustnessSummary = {
  policy: string;
  median_net_5d_return: number;
  worst_decile_mean_net_return: number;
  expected_shortfall_95_return: number;
  worst_monthly_return: number;
  longest_underwater_calendar_days: number;
  max_drawdown: number;
  net_sharpe: number;
  excess_sharpe: number;
  avg_turnover: number;
};

export type BootstrapResult = {
  metric: string;
  observed_difference: number;
  ci_95_lower: number;
  ci_95_upper: number;
  probability_difference_positive: number;
  two_sided_bootstrap_p_value: number;
  statistically_significant_5pct: boolean;
};

export type CostStressResult = {
  policy: string;
  scenario: string;
  total_trading_cost_bps: number;
  annualized_net_return: number;
  net_sharpe: number;
  excess_sharpe: number;
  max_drawdown: number;
};

export type RobustnessData = {
  summary: RobustnessSummary[];
  bootstrap: BootstrapResult[];
  cost_stress: CostStressResult[];
  drawdown_episodes: Record<string, unknown>[];
  asset_concentration: Record<string, unknown>[];
  regime_exposure: Record<string, unknown>[];
  coverage: {
    asset_concentration: string;
    market_regime_exposure: string;
    sector_exposure: string;
    factor_exposure: string;
  };
};

const ALPHA = "baseline_equal_weight";
const RISK =
  "turnover_buffer_inverse_volatility_risk_scaled";

function pct(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

function num(value: number) {
  return value.toFixed(3);
}

function days(value: number) {
  return `${Math.round(value).toLocaleString()} DAYS`;
}

function policyLabel(policy: string) {
  return policy === ALPHA
    ? "Alpha Benchmark"
    : "Risk-Managed Candidate";
}

export default function RobustnessPanel({
  robustness,
}: {
  robustness: RobustnessData;
}) {
  const alpha = robustness.summary.find(
    (row) => row.policy === ALPHA
  );

  const risk = robustness.summary.find(
    (row) => row.policy === RISK
  );

  const sharpeTest = robustness.bootstrap.find(
    (row) => row.metric === "excess_sharpe"
  );

  const drawdownTest = robustness.bootstrap.find(
    (row) => row.metric === "max_drawdown"
  );

  const stressRows = robustness.cost_stress.filter(
    (row) =>
      ["realistic_base", "conservative", "stress"].includes(
        row.scenario
      )
  );

  return (
    <>
      <section className="panel mt-6">
        <div className="panel-header">
          <div>
            <p className="eyebrow">
              INSTITUTIONAL VALIDATION
            </p>
            <h3 className="panel-title">
              Distribution and tail risk
            </h3>
          </div>

          <span className="status-chip">
            276 OOS REBALANCES
          </span>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          {[alpha, risk]
            .filter(
              (
                result
              ): result is RobustnessSummary =>
                Boolean(result)
            )
            .map((result) => (
              <div
                key={result.policy}
                className="border border-white/10 bg-black/35 p-6"
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-base font-medium">
                      {policyLabel(result.policy)}
                    </p>
                    <p className="mt-2 font-mono text-[10px] text-white/25">
                      {result.policy}
                    </p>
                  </div>

                  <span
                    className={
                      result.policy === RISK
                        ? "text-[10px] tracking-[0.18em] text-red-400"
                        : "text-[10px] tracking-[0.18em] text-emerald-400"
                    }
                  >
                    {result.policy === RISK
                      ? "TAIL CONTROL"
                      : "SIGNAL CAPTURE"}
                  </span>
                </div>

                <div className="mt-7 grid grid-cols-2 gap-5">
                  <Metric
                    label="MEDIAN 5D NET"
                    value={pct(
                      result.median_net_5d_return
                    )}
                  />
                  <Metric
                    label="WORST DECILE MEAN"
                    value={pct(
                      result.worst_decile_mean_net_return
                    )}
                    danger
                  />
                  <Metric
                    label="EXPECTED SHORTFALL 95"
                    value={pct(
                      result.expected_shortfall_95_return
                    )}
                    danger
                  />
                  <Metric
                    label="WORST MONTH"
                    value={pct(
                      result.worst_monthly_return
                    )}
                    danger
                  />
                  <Metric
                    label="LONGEST UNDERWATER"
                    value={days(
                      result.longest_underwater_calendar_days
                    )}
                  />
                  <Metric
                    label="MAX DRAWDOWN"
                    value={pct(result.max_drawdown)}
                    danger
                  />
                </div>
              </div>
            ))}
        </div>
      </section>

      <section className="mt-6 grid gap-6 lg:grid-cols-2">
        <div className="panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">
                STATISTICAL CONFIDENCE
              </p>
              <h3 className="panel-title">
                Paired block bootstrap
              </h3>
            </div>
          </div>

          <div className="space-y-4">
            {sharpeTest && (
              <EvidenceRow
                title="Excess Sharpe difference"
                result={sharpeTest}
                interpretation={
                  sharpeTest.statistically_significant_5pct
                    ? "Statistically distinguishable"
                    : "Not statistically distinguishable"
                }
              />
            )}

            {drawdownTest && (
              <EvidenceRow
                title="Maximum drawdown improvement"
                result={drawdownTest}
                interpretation={
                  drawdownTest.statistically_significant_5pct
                    ? "Statistically significant improvement"
                    : "Not statistically distinguishable"
                }
                positive
              />
            )}
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">DATA COVERAGE</p>
              <h3 className="panel-title">
                Exposure analysis
              </h3>
            </div>
          </div>

          <div className="space-y-3">
            <CoverageRow
              label="Asset concentration"
              value={robustness.coverage.asset_concentration}
              available
            />
            <CoverageRow
              label="Market-regime exposure"
              value={
                robustness.coverage.market_regime_exposure
              }
              available
            />
            <CoverageRow
              label="Sector exposure"
              value={robustness.coverage.sector_exposure}
            />
            <CoverageRow
              label="Factor exposure"
              value={robustness.coverage.factor_exposure}
            />
          </div>
        </div>
      </section>

      <section className="panel mt-6">
        <div className="panel-header">
          <div>
            <p className="eyebrow">
              EXECUTION COST STRESS
            </p>
            <h3 className="panel-title">
              Performance under harsher assumptions
            </h3>
          </div>
        </div>

        <div className="overflow-x-auto">
          <div className="min-w-[900px]">
            <div className="grid grid-cols-[1.4fr_1fr_100px_130px_110px_110px_130px] border-b border-white/10 px-4 py-3 text-[9px] tracking-[0.16em] text-white/30">
              <span>POLICY</span>
              <span>SCENARIO</span>
              <span>COST</span>
              <span>ANNUALIZED</span>
              <span>SHARPE</span>
              <span>EXCESS</span>
              <span>DRAWDOWN</span>
            </div>

            <div className="divide-y divide-white/5">
              {stressRows.map((row) => (
                <div
                  key={`${row.policy}-${row.scenario}`}
                  className="grid grid-cols-[1.4fr_1fr_100px_130px_110px_110px_130px] items-center px-4 py-4 text-sm"
                >
                  <span className="text-white/70">
                    {policyLabel(row.policy)}
                  </span>

                  <span className="font-mono text-xs text-white/40">
                    {row.scenario
                      .replaceAll("_", " ")
                      .toUpperCase()}
                  </span>

                  <span className="font-mono text-white/55">
                    {row.total_trading_cost_bps.toFixed(
                      0
                    )}{" "}
                    BPS
                  </span>

                  <span className="font-mono text-white/70">
                    {pct(row.annualized_net_return)}
                  </span>

                  <span className="font-mono text-white/70">
                    {num(row.net_sharpe)}
                  </span>

                  <span className="font-mono text-white/70">
                    {num(row.excess_sharpe)}
                  </span>

                  <span className="font-mono text-red-400">
                    {pct(row.max_drawdown)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </>
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
      <p className="text-[9px] tracking-[0.18em] text-white/30">
        {label}
      </p>

      <p
        className={`mt-2 font-mono text-sm ${
          danger ? "text-red-400" : "text-white/75"
        }`}
      >
        {value}
      </p>
    </div>
  );
}

function EvidenceRow({
  title,
  result,
  interpretation,
  positive = false,
}: {
  title: string;
  result: BootstrapResult;
  interpretation: string;
  positive?: boolean;
}) {
  return (
    <div className="border border-white/10 bg-black/35 p-5">
      <div className="flex items-start justify-between gap-5">
        <p className="text-sm text-white/75">
          {title}
        </p>

        <span
          className={`text-[10px] tracking-[0.15em] ${
            result.statistically_significant_5pct
              ? positive
                ? "text-emerald-400"
                : "text-red-400"
              : "text-white/35"
          }`}
        >
          {result.statistically_significant_5pct
            ? "SIGNIFICANT"
            : "NOT SIGNIFICANT"}
        </span>
      </div>

      <div className="mt-5 grid grid-cols-3 gap-4">
        <Metric
          label="OBSERVED"
          value={num(result.observed_difference)}
        />
        <Metric
          label="95% CI LOW"
          value={num(result.ci_95_lower)}
        />
        <Metric
          label="95% CI HIGH"
          value={num(result.ci_95_upper)}
        />
      </div>

      <p className="mt-4 text-xs leading-5 text-white/35">
        {interpretation}. Bootstrap p-value{" "}
        {result.two_sided_bootstrap_p_value.toFixed(4)}.
      </p>
    </div>
  );
}

function CoverageRow({
  label,
  value,
  available = false,
}: {
  label: string;
  value: string;
  available?: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-4 border border-white/10 bg-black/35 px-4 py-4">
      <span className="text-sm text-white/60">
        {label}
      </span>

      <span
        className={`font-mono text-[10px] tracking-[0.12em] ${
          available ? "text-emerald-400" : "text-red-400"
        }`}
      >
        {value.replaceAll("_", " ").toUpperCase()}
      </span>
    </div>
  );
}
