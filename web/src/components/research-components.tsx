import { humanize, number, percent, signedNumber } from "@/lib/format";
import type { ResearchDecision, ResearchResult, RobustnessRow } from "@/lib/site-types";
import { StatusBadge } from "@/components/ui";

export function MandateCard({
  title,
  subtitle,
  result,
  featured = false,
  defensive = false,
}: {
  title: string;
  subtitle: string;
  result: ResearchResult;
  featured?: boolean;
  defensive?: boolean;
}) {
  return (
    <article className={`relative overflow-hidden border p-6 ${featured ? "border-emerald-400/30 bg-emerald-400/[0.045]" : defensive ? "border-white/15 bg-white/[0.025]" : "border-white/10 bg-white/[0.018]"}`}>
      {featured && <div className="absolute inset-x-0 top-0 h-px bg-emerald-300" />}
      <div className="flex items-start justify-between gap-5">
        <div>
          <p className="text-lg font-medium tracking-[-0.02em]">{title}</p>
          <p className={`mt-2 text-[9px] tracking-[0.18em] ${featured ? "text-emerald-300" : "text-white/30"}`}>{subtitle.toUpperCase()}</p>
        </div>
        <span className="font-mono text-[10px] text-white/30">{result.avg_exposure.toFixed(3)}x AVG</span>
      </div>
      <div className="mt-7 grid grid-cols-2 gap-x-5 gap-y-6">
        <ResultMetric label="NET RETURN" value={percent(result.annualized_net_return)} positive />
        <ResultMetric label="NET SHARPE" value={number(result.net_sharpe)} />
        <ResultMetric label="SORTINO" value={number(result.net_sortino)} />
        <ResultMetric label="MAX DRAWDOWN" value={percent(result.max_drawdown)} negative />
      </div>
      <div className="mt-6 border-t border-white/8 pt-4 text-xs leading-5 text-white/30">
        {humanize(result.risk_anchor)} · {Math.round(result.signal_blend * 100)}% signal blend · {humanize(result.exposure_policy)}
      </div>
    </article>
  );
}

export function DecisionCard({ decision }: { decision: ResearchDecision }) {
  const badgeTone = decision.status === "locked" ? "positive" : decision.status === "rejected" ? "negative" : "neutral";
  return (
    <article className="card card-hover p-6 sm:p-7">
      <div className="flex items-start justify-between gap-5">
        <span className="font-mono text-sm text-emerald-300">{decision.step}</span>
        <StatusBadge tone={badgeTone}>{decision.status.toUpperCase()}</StatusBadge>
      </div>
      <h3 className="mt-8 text-xl font-medium tracking-[-0.025em]">{decision.title}</h3>
      <p className="mt-3 text-xs font-medium uppercase tracking-[0.12em] text-white/28">{decision.question}</p>
      <p className="mt-5 text-sm leading-6 text-white/48">{decision.finding}</p>
      <div className="mt-5 border-l border-emerald-400/35 pl-4">
        <p className="text-[9px] tracking-[0.18em] text-emerald-300">DECISION</p>
        <p className="mt-2 text-sm leading-6 text-white/62">{decision.decision}</p>
      </div>
      <div className="mt-6 grid grid-cols-2 gap-3">
        {decision.metrics.map((metric) => (
          <div key={`${decision.key}-${metric.label}`} className="border border-white/8 bg-black/25 p-3">
            <p className={`font-mono text-sm ${metric.tone === "positive" ? "text-emerald-300" : metric.tone === "negative" ? "text-red-300" : "text-white/70"}`}>
              {formatMetric(metric.value, metric.format)}
            </p>
            <p className="mt-1 text-[8px] tracking-[0.12em] text-white/25">{metric.label.toUpperCase()}</p>
          </div>
        ))}
      </div>
      <p className="mt-5 break-all font-mono text-[9px] leading-4 text-white/18">SOURCE · {decision.source_report}</p>
    </article>
  );
}

export function RobustnessGrid({
  rows,
  title,
}: {
  rows: RobustnessRow[];
  title: string;
}) {
  return (
    <div className="card overflow-hidden">
      <div className="border-b border-white/10 px-5 py-4">
        <p className="text-sm font-medium">{title}</p>
        <p className="mt-1 text-xs text-white/30">Signal blend versus the same-anchor 0% signal baseline.</p>
      </div>
      <div className="grid grid-cols-[90px_repeat(3,1fr)] border-b border-white/8 px-5 py-3 text-[8px] tracking-[0.14em] text-white/25">
        <span>BLEND</span><span>SHARPE WINS</span><span>RETURN WINS</span><span>MEDIAN RETURN Δ</span>
      </div>
      <div className="divide-y divide-white/6">
        {rows.map((row) => (
          <div key={`${row.exposure_policy}-${row.signal_blend}`} className="grid grid-cols-[90px_repeat(3,1fr)] items-center px-5 py-4 font-mono text-xs text-white/55">
            <span className="text-emerald-300">{percent(row.signal_blend, 0)}</span>
            <span>{row.years_beating_anchor_sharpe}/{row.years}</span>
            <span>{row.years_beating_anchor_return}/{row.years}</span>
            <span className={row.median_return_delta_vs_anchor >= 0 ? "text-emerald-300" : "text-red-300"}>{percent(row.median_return_delta_vs_anchor, 1)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ComparisonBar({
  label,
  value,
  max,
  display,
  tone = "positive",
}: {
  label: string;
  value: number;
  max: number;
  display: string;
  tone?: "positive" | "negative" | "neutral";
}) {
  const width = Math.max(2, Math.min(100, Math.abs(value / max) * 100));
  const fill = tone === "negative" ? "bg-red-300" : tone === "neutral" ? "bg-white/45" : "bg-emerald-300";
  return (
    <div>
      <div className="flex items-center justify-between gap-4 text-xs">
        <span className="text-white/42">{label}</span>
        <span className="font-mono text-white/70">{display}</span>
      </div>
      <div className="mt-2 h-1 bg-white/8"><div className={`h-1 ${fill}`} style={{ width: `${width}%` }} /></div>
    </div>
  );
}

function ResultMetric({ label, value, positive = false, negative = false }: { label: string; value: string; positive?: boolean; negative?: boolean }) {
  return (
    <div>
      <p className="text-[8px] tracking-[0.16em] text-white/25">{label}</p>
      <p className={`mt-2 font-mono text-lg ${positive ? "text-emerald-300" : negative ? "text-red-300" : "text-white/80"}`}>{value}</p>
    </div>
  );
}

function formatMetric(value: number | string, format: "percent" | "number" | "text") {
  if (typeof value === "string") return value;
  if (format === "percent") return percent(value);
  if (format === "number") return signedNumber(value);
  return String(value);
}
