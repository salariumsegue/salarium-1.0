export type FactorExposureRow = {
  policy: string;
  factor: string;
  mean_exposure: number;
  median_exposure: number;
  p10_exposure: number;
  p90_exposure: number;
  mean_absolute_exposure: number;
  maximum_absolute_exposure: number;
  average_covered_weight: number;
};

export type WeightedConcentrationRow = {
  policy: string;
  avg_maximum_weight: number;
  worst_maximum_weight: number;
  avg_hhi: number;
  avg_effective_names: number;
  min_effective_names: number;
};

export type FactorExposureData = {
  summary: FactorExposureRow[];
  weighted_concentration: WeightedConcentrationRow[];
  coverage: Record<string, string>;
  methodology: Record<string, string>;
  disclosure: string;
};

const ALPHA = "baseline_equal_weight";
const RISK =
  "turnover_buffer_inverse_volatility_risk_scaled";

const FACTOR_ORDER = [
  "market_beta_60d",
  "momentum_20d_z",
  "relative_strength_z",
  "low_volatility_z",
  "short_term_reversal_z",
];

const FACTOR_LABELS: Record<string, string> = {
  market_beta_60d: "Market Beta",
  momentum_20d_z: "Momentum",
  relative_strength_z: "Relative Strength",
  low_volatility_z: "Low Volatility",
  short_term_reversal_z: "Short-Term Reversal",
};

function policyLabel(policy: string) {
  return policy === ALPHA
    ? "Alpha Benchmark"
    : "Risk-Managed Candidate";
}

function exposure(value: number) {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(3)}`;
}

function pct(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

export default function FactorExposurePanel({
  data,
}: {
  data: FactorExposureData;
}) {
  const alphaRows = new Map(
    data.summary
      .filter((row) => row.policy === ALPHA)
      .map((row) => [row.factor, row])
  );

  const riskRows = new Map(
    data.summary
      .filter((row) => row.policy === RISK)
      .map((row) => [row.factor, row])
  );

  const concentrations =
    data.weighted_concentration;

  const unavailable = Object.entries(
    data.coverage
  ).filter(
    ([, value]) =>
      value.startsWith("unavailable")
  );

  return (
    <>
      <section className="panel mt-6">
        <div className="panel-header">
          <div>
            <p className="eyebrow">
              FACTOR ATTRIBUTION
            </p>
            <h3 className="panel-title">
              What economic exposures sit behind the signal?
            </h3>
          </div>

          <span className="status-chip">
            TECHNICAL FACTOR PROXIES
          </span>
        </div>

        <p className="mb-6 max-w-4xl text-xs leading-6 text-white/35">
          {data.disclosure}
        </p>

        <div className="overflow-x-auto">
          <div className="min-w-[800px]">
            <div className="grid grid-cols-[1.4fr_1fr_1fr_1fr_1fr] border-b border-white/10 px-4 py-3 text-[9px] tracking-[0.16em] text-white/30">
              <span>FACTOR</span>
              <span>ALPHA MEAN</span>
              <span>RISK-MANAGED MEAN</span>
              <span>ALPHA RANGE</span>
              <span>RISK RANGE</span>
            </div>

            <div className="divide-y divide-white/5">
              {FACTOR_ORDER.map((factor) => {
                const alpha =
                  alphaRows.get(factor);
                const risk =
                  riskRows.get(factor);

                if (!alpha || !risk) {
                  return null;
                }

                return (
                  <div
                    key={factor}
                    className="grid grid-cols-[1.4fr_1fr_1fr_1fr_1fr] items-center px-4 py-4 text-sm"
                  >
                    <span className="text-white/75">
                      {FACTOR_LABELS[factor]}
                    </span>

                    <span className="font-mono text-white/65">
                      {exposure(
                        alpha.mean_exposure
                      )}
                    </span>

                    <span className="font-mono text-white/65">
                      {exposure(
                        risk.mean_exposure
                      )}
                    </span>

                    <span className="font-mono text-xs text-white/35">
                      {exposure(
                        alpha.p10_exposure
                      )}{" "}
                      →{" "}
                      {exposure(
                        alpha.p90_exposure
                      )}
                    </span>

                    <span className="font-mono text-xs text-white/35">
                      {exposure(
                        risk.p10_exposure
                      )}{" "}
                      →{" "}
                      {exposure(
                        risk.p90_exposure
                      )}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      <section className="mt-6 grid gap-6 lg:grid-cols-2">
        <div className="panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">
                WEIGHT-LEVEL CONCENTRATION
              </p>
              <h3 className="panel-title">
                Effective diversification
              </h3>
            </div>
          </div>

          <div className="space-y-4">
            {concentrations.map((row) => (
              <div
                key={row.policy}
                className="border border-white/10 bg-black/35 p-5"
              >
                <p className="text-sm text-white/75">
                  {policyLabel(row.policy)}
                </p>

                <div className="mt-5 grid grid-cols-2 gap-5">
                  <Metric
                    label="AVG MAX WEIGHT"
                    value={pct(
                      row.avg_maximum_weight
                    )}
                  />
                  <Metric
                    label="WORST MAX WEIGHT"
                    value={pct(
                      row.worst_maximum_weight
                    )}
                  />
                  <Metric
                    label="AVG EFFECTIVE NAMES"
                    value={row.avg_effective_names.toFixed(
                      2
                    )}
                  />
                  <Metric
                    label="MIN EFFECTIVE NAMES"
                    value={row.min_effective_names.toFixed(
                      2
                    )}
                  />
                  <Metric
                    label="AVG HHI"
                    value={row.avg_hhi.toFixed(3)}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">
                ATTRIBUTION COVERAGE
              </p>
              <h3 className="panel-title">
                Remaining data gaps
              </h3>
            </div>
          </div>

          <div className="space-y-3">
            {unavailable.map(
              ([key, value]) => (
                <div
                  key={key}
                  className="border border-white/10 bg-black/35 px-4 py-4"
                >
                  <div className="flex items-center justify-between gap-4">
                    <span className="text-sm capitalize text-white/60">
                      {key
                        .replaceAll("_", " ")}
                    </span>

                    <span className="text-[9px] tracking-[0.14em] text-red-400">
                      UNAVAILABLE
                    </span>
                  </div>

                  <p className="mt-2 font-mono text-[10px] text-white/25">
                    {value}
                  </p>
                </div>
              )
            )}
          </div>
        </div>
      </section>
    </>
  );
}

function Metric({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div>
      <p className="text-[9px] tracking-[0.16em] text-white/30">
        {label}
      </p>

      <p className="mt-2 font-mono text-sm text-white/75">
        {value}
      </p>
    </div>
  );
}
