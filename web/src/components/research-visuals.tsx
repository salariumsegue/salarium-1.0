import { humanize, number, percent, signedNumber } from "@/lib/format";
import type { ResearchDecision, RobustnessRow, YearlyResearchResult } from "@/lib/site-types";
import { StatusBadge } from "@/components/ui";

export function ArchitectureNode({
  index,
  title,
  description,
  accent = false,
}: {
  index: number;
  title: string;
  description: string;
  accent?: boolean;
}) {
  return (
    <article className={`relative min-h-52 border p-5 ${accent ? "border-emerald-400/30 bg-emerald-400/[0.045]" : "border-white/10 bg-white/[0.018]"}`}>
      <div className="flex items-center justify-between">
        <span className={`font-mono text-xs ${accent ? "text-emerald-300" : "text-white/25"}`}>{String(index).padStart(2, "0")}</span>
        <span className={`h-1.5 w-1.5 rounded-full ${accent ? "bg-emerald-300" : "bg-white/20"}`} />
      </div>
      <h3 className="mt-10 text-lg font-medium tracking-[-0.02em]">{title}</h3>
      <p className="mt-3 text-sm leading-6 text-white/38">{description}</p>
    </article>
  );
}

export function AnnualPerformanceTable({
  core,
  aggressive,
  defensive,
}: {
  core: YearlyResearchResult[];
  aggressive: YearlyResearchResult[];
  defensive: YearlyResearchResult[];
}) {
  const years = Array.from(new Set(core.map((row) => row.period)));
  const byPeriod = (rows: YearlyResearchResult[], period: string) => rows.find((row) => row.period === period);

  return (
    <div className="card overflow-x-auto">
      <table className="min-w-[860px] w-full border-collapse text-left">
        <thead>
          <tr className="border-b border-white/10 text-[9px] uppercase tracking-[0.16em] text-white/25">
            <th className="px-5 py-4">Year</th>
            <th className="px-5 py-4">Core return</th>
            <th className="px-5 py-4">Core Sharpe</th>
            <th className="px-5 py-4">Aggressive return</th>
            <th className="px-5 py-4">Defensive return</th>
            <th className="px-5 py-4">Core drawdown</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/6 font-mono text-xs text-white/58">
          {years.map((year) => {
            const c = byPeriod(core, year);
            const a = byPeriod(aggressive, year);
            const d = byPeriod(defensive, year);
            return (
              <tr key={year} className="transition hover:bg-white/[0.025]">
                <td className="px-5 py-4 text-white/80">{year}</td>
                <td className={`px-5 py-4 ${tone(c?.annualized_net_return)}`}>{c ? percent(c.annualized_net_return) : "—"}</td>
                <td className="px-5 py-4">{c ? number(c.net_sharpe) : "—"}</td>
                <td className={`px-5 py-4 ${tone(a?.annualized_net_return)}`}>{a ? percent(a.annualized_net_return) : "—"}</td>
                <td className={`px-5 py-4 ${tone(d?.annualized_net_return)}`}>{d ? percent(d.annualized_net_return) : "—"}</td>
                <td className="px-5 py-4 text-red-300">{c ? percent(c.max_drawdown) : "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function DecisionGrid({ decisions }: { decisions: ResearchDecision[] }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {decisions.map((decision) => (
        <article key={decision.key} className="card card-hover p-6">
          <div className="flex items-start justify-between gap-4">
            <span className="font-mono text-sm text-emerald-300">{decision.step}</span>
            <StatusBadge tone={decision.status === "rejected" ? "negative" : decision.status === "locked" ? "positive" : "neutral"}>
              {decision.status.toUpperCase()}
            </StatusBadge>
          </div>
          <h3 className="mt-7 text-xl font-medium tracking-[-0.025em]">{decision.title}</h3>
          <p className="mt-3 text-[10px] uppercase tracking-[0.13em] text-white/25">{decision.question}</p>
          <p className="mt-5 text-sm leading-6 text-white/46">{decision.finding}</p>
          <div className="mt-5 border-l border-emerald-400/40 pl-4">
            <p className="text-[9px] uppercase tracking-[0.16em] text-emerald-300">Decision</p>
            <p className="mt-2 text-sm leading-6 text-white/64">{decision.decision}</p>
          </div>
          <div className="mt-6 grid grid-cols-2 gap-3">
            {decision.metrics.map((metric) => (
              <div key={`${decision.key}-${metric.label}`} className="border border-white/8 bg-black/30 p-3">
                <p className={`font-mono text-sm ${metric.tone === "positive" ? "text-emerald-300" : metric.tone === "negative" ? "text-red-300" : "text-white/70"}`}>
                  {formatMetric(metric.value, metric.format)}
                </p>
                <p className="mt-1 text-[8px] uppercase tracking-[0.12em] text-white/22">{metric.label}</p>
              </div>
            ))}
          </div>
        </article>
      ))}
    </div>
  );
}

export function RobustnessTable({ rows, title }: { rows: RobustnessRow[]; title: string }) {
  return (
    <div className="card overflow-hidden">
      <div className="border-b border-white/10 px-5 py-4">
        <h3 className="text-sm font-medium">{title}</h3>
        <p className="mt-1 text-xs text-white/30">Each signal blend is compared with the same risk anchor at 0% signal influence.</p>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-[620px] w-full border-collapse text-left">
          <thead>
            <tr className="border-b border-white/8 text-[8px] uppercase tracking-[0.14em] text-white/25">
              <th className="px-5 py-3">Blend</th>
              <th className="px-5 py-3">Sharpe wins</th>
              <th className="px-5 py-3">Return wins</th>
              <th className="px-5 py-3">Median Sharpe Δ</th>
              <th className="px-5 py-3">Median return Δ</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/6 font-mono text-xs text-white/55">
            {rows.map((row) => (
              <tr key={`${row.exposure_policy}-${row.signal_blend}`}>
                <td className="px-5 py-4 text-emerald-300">{percent(row.signal_blend, 0)}</td>
                <td className="px-5 py-4">{row.years_beating_anchor_sharpe}/{row.years}</td>
                <td className="px-5 py-4">{row.years_beating_anchor_return}/{row.years}</td>
                <td className={`px-5 py-4 ${tone(row.median_sharpe_delta_vs_anchor)}`}>{signedNumber(row.median_sharpe_delta_vs_anchor)}</td>
                <td className={`px-5 py-4 ${tone(row.median_return_delta_vs_anchor)}`}>{percent(row.median_return_delta_vs_anchor)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function ConstructorComparison({ rows }: { rows: Array<Record<string, string | number | boolean | null>> }) {
  const filtered = rows.filter((row) => row.top_n === 10 && row.covariance_lookback === 60 && row.exposure_policy === "static_1x");
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {filtered.map((row) => (
        <article key={String(row.base_policy)} className="card p-5">
          <p className="text-[9px] uppercase tracking-[0.15em] text-white/25">Portfolio constructor</p>
          <h3 className="mt-3 text-lg font-medium">{humanize(String(row.base_policy))}</h3>
          <div className="mt-6 grid grid-cols-2 gap-4">
            <Result label="Return" value={percent(asNumber(row.annualized_net_return))} positive />
            <Result label="Sharpe" value={number(asNumber(row.net_sharpe))} />
            <Result label="Max drawdown" value={percent(asNumber(row.max_drawdown))} negative />
            <Result label="Volatility" value={percent(asNumber(row.annualized_net_volatility))} />
          </div>
        </article>
      ))}
    </div>
  );
}

export function SignalBlendFrontier({ rows }: { rows: Array<Record<string, string | number | boolean | null>> }) {
  const filtered = rows
    .filter((row) => row.risk_anchor === "shrinkage_max_diversification" && row.exposure_policy === "legacy_risk_scaled")
    .sort((a, b) => asNumber(a.signal_blend) - asNumber(b.signal_blend));
  const maxReturn = Math.max(...filtered.map((row) => asNumber(row.annualized_net_return)), 0.01);
  return (
    <div className="card p-6">
      <div className="space-y-6">
        {filtered.map((row) => {
          const blend = asNumber(row.signal_blend);
          const result = asNumber(row.annualized_net_return);
          return (
            <div key={String(blend)}>
              <div className="flex items-center justify-between gap-5 text-xs">
                <span className="text-white/45">{percent(blend, 0)} signal influence</span>
                <span className="font-mono text-white/72">{percent(result)} return · {number(asNumber(row.net_sharpe))} Sharpe</span>
              </div>
              <div className="mt-2 h-1 bg-white/8"><div className="h-1 bg-emerald-300" style={{ width: `${Math.max(2, (result / maxReturn) * 100)}%` }} /></div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Result({ label, value, positive = false, negative = false }: { label: string; value: string; positive?: boolean; negative?: boolean }) {
  return <div><p className="text-[8px] uppercase tracking-[0.14em] text-white/22">{label}</p><p className={`mt-2 font-mono text-base ${positive ? "text-emerald-300" : negative ? "text-red-300" : "text-white/75"}`}>{value}</p></div>;
}

function asNumber(value: string | number | boolean | null | undefined): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function tone(value: number | undefined): string {
  if (typeof value !== "number") return "text-white/55";
  if (value > 0) return "text-emerald-300";
  if (value < 0) return "text-red-300";
  return "text-white/55";
}

function formatMetric(value: number | string, format: "percent" | "number" | "text") {
  if (typeof value === "string") return value;
  if (format === "percent") return percent(value);
  if (format === "number") return signedNumber(value);
  return String(value);
}
