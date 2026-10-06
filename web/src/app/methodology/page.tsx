import type { Metadata } from "next";

import ProvenanceDisclosure from "@/components/provenance-disclosure";
import { PageIntro } from "@/components/ui";
import { humanize, percent } from "@/lib/format";
import { loadReleaseSnapshot } from "@/lib/site-data";

export const metadata: Metadata = { title: "Methodology", description: "Read the stock model's settings, why they were chosen, and what the tests do not prove.", alternates: { canonical: "/methodology" } };

export default function MethodologyPage() {
  const release = loadReleaseSnapshot(); const a = release.architecture;
  const configuration = [
    ["Universe", a.universe], ["Forward target", `${a.model_horizon_days} trading days`], ["Rebalance", `${a.rebalance_every_days} trading days`], ["Validation", "Annual expanding-window out-of-sample"], ["Portfolio", `Top-${a.top_n}`], ["Persistence buffer", `Rank ${a.buffer_rank}`], ["Covariance", `${a.covariance_lookback_days}-day ${a.covariance_estimator}`], ["Risk anchor", humanize(a.primary_risk_anchor)], ["Signal blend", percent(a.signal_blend, 0)], ["Maximum position", percent(a.max_single_name_weight, 0)], ["Maximum exposure", `${a.leverage_cap.toFixed(2)}x`], ["Direction", a.long_only ? "Long only" : "Not specified"],
  ];
  const explanations = [
    ["Why use a 20-day forecast?", "In the historical comparison, a 20-day forecast with a 10-day rebalance schedule beat the original 5-day forecast and rebalance schedule."],
    ["Why rebalance every 10 days?", "The forecast length and trading schedule were tested separately. Rebalancing every 10 trading days kept the longer signal and cut unnecessary trading."],
    ["Why hold 10 stocks?", "Wider portfolios lowered volatility and turnover, but diluted returns more than they improved risk-adjusted results."],
    ["Why keep stocks through rank 15?", "Keeping a stock until it falls below rank 15 can reduce trading near the 10-stock cutoff. The public results do not include a test of this rule on its own."],
    ["Why use shrinkage covariance?", "The 60-day Ledoit-Wolf estimate weights stocks by how they move together. It performed better in the selected comparison than weighting by volatility alone, and the optimizer did not fall back to a simpler method."],
    ["Why blend risk and model score?", "Giving the model score 25% of the weight raised simulated returns while keeping the Sharpe ratio close to the risk-only portfolio. Larger blends raised volatility and drawdown."],
    ["Why cap each stock at 18%?", "The model card sets this limit. The public results do not isolate the effect of the cap, so they cannot show that 18% is the best value."],
    ["Why set a 1.25x exposure limit?", "This is a ceiling, not a target. The selected portfolio stayed at or below 1.00x in the historical test and was usually below full exposure."],
    ["Which trading costs are included?", "Net results include modeled transaction costs based on turnover. They do not include market impact, taxes, borrowing costs, or the price a real order would receive."],
    ["How does the test avoid future data?", "Each year's scores come from a model fit on earlier years. The repository also contains date and data checks, but those checks cannot remove survivorship or every data risk."],
    ["Is there a final untouched test period?", "The model card reports annual out-of-sample results for 2021–2026. It does not show a separate final period that was never used during model selection."],
  ];
  return <main id="main-content" className="site-main"><section className="page-section"><PageIntro eyebrow="MODEL SETTINGS" title="How the stock model is set up" muted="And what the tests can tell us." description="See the current settings, why they were selected, and where the public research leaves questions open." />
    <div className="mt-10 methodology-grid"><div><p className="eyebrow">CURRENT SETTINGS</p><dl className="config-ledger">{configuration.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl></div><div><p className="eyebrow">WHY THESE SETTINGS?</p><div className="mt-5 space-y-2">{explanations.map(([question, answer]) => <details key={question} className="methodology-disclosure"><summary>{question}<span aria-hidden="true">＋</span></summary><p>{answer}</p></details>)}</div></div></div>
    <div className="mt-10"><ProvenanceDisclosure record={{ source: "Salarium 1.0 model card and governed release snapshot", artifact: release.provenance.source_report, outOfSamplePeriod: release.research.period, portfolio: "Core balanced", model: `${a.model_horizon_days}D expanding-window rank model`, commit: release.provenance.git_commit, generatedAt: release.generated_at_utc }} /></div>
  </section></main>;
}
