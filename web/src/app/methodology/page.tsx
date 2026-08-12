import type { Metadata } from "next";

import ProvenanceDisclosure from "@/components/provenance-disclosure";
import { PageIntro } from "@/components/ui";
import { humanize, percent } from "@/lib/format";
import { loadReleaseSnapshot } from "@/lib/site-data";

export const metadata: Metadata = { title: "Methodology", description: "Inspect Salarium's verified research configuration, rationale, validation design, and documentation boundaries.", alternates: { canonical: "/methodology" } };

export default function MethodologyPage() {
  const release = loadReleaseSnapshot(); const a = release.architecture;
  const configuration = [
    ["Universe", a.universe], ["Forward target", `${a.model_horizon_days} trading days`], ["Rebalance", `${a.rebalance_every_days} trading days`], ["Validation", "Annual expanding-window out-of-sample"], ["Portfolio", `Top-${a.top_n}`], ["Persistence buffer", `Rank ${a.buffer_rank}`], ["Covariance", `${a.covariance_lookback_days}-day ${a.covariance_estimator}`], ["Risk anchor", humanize(a.primary_risk_anchor)], ["Signal blend", percent(a.signal_blend, 0)], ["Maximum position", percent(a.max_single_name_weight, 0)], ["Maximum exposure", `${a.leverage_cap.toFixed(2)}x`], ["Direction", a.long_only ? "Long only" : "Not specified"],
  ];
  const explanations = [
    ["Why this prediction horizon?", "The horizon/rebalance tournament found the 20D target with a 10D cadence stronger than the original 5D/5D design on the committed comparison."],
    ["Why this rebalance frequency?", "Prediction horizon and trading cadence were tested separately. Ten trading days retained the slower-moving 20D signal while reducing unnecessary activity."],
    ["Why this portfolio breadth?", "Broader 20–75 name portfolios reduced volatility and turnover but diluted return faster than they improved risk-adjusted performance."],
    ["Why this persistence buffer?", "The locked model card specifies rank 15 to reduce turnover around the Top-10 boundary. A separate causal ablation for the exact buffer is not included in the public release snapshot."],
    ["Why shrinkage covariance?", "The 60D Ledoit-Wolf maximum-diversification constructor improved the selected risk/return comparison versus inverse-volatility weighting without optimizer fallback."],
    ["Why the risk/signal blend?", "A 25% signal allocation increased simulated return while leaving overall Sharpe close to the pure risk anchor. Larger blends increased volatility and drawdown."],
    ["Why the position cap?", "The 18% cap is part of the locked governance contract. The public artifact does not include a standalone cap ablation, so no stronger causal claim is made."],
    ["Why the exposure ceiling?", "The 1.25x ceiling is permission, not a target. The selected research candidate never exceeded 1.00x and spent most periods below full exposure."],
    ["What transaction costs are modeled?", "The reported net results include an average transaction-cost field and turnover-derived costs. Market impact, taxes, borrow constraints, and realized execution remain outside the public contract."],
    ["How is look-ahead leakage prevented?", "Annual expanding-window fits generate out-of-sample scores for each test year. The repository also includes data-quality and leakage audits; residual data and universe-selection risk remains."],
    ["How are training, validation, and walk-forward periods separated?", "The public model card verifies annual expanding-window out-of-sample evaluation across 2021–2026. It does not publish a separate final untouched live holdout, and results must be read with model-selection bias in mind."],
  ];
  return <main id="main-content" className="site-main"><section className="page-section"><PageIntro eyebrow="GOVERNED METHODOLOGY" title="Every parameter has a source." muted="Every gap stays visible." description="This page distinguishes the locked production-research configuration from the evidence used to select it—and from decisions the public artifacts do not independently prove." />
    <div className="mt-10 methodology-grid"><div><p className="eyebrow">CURRENT CONFIGURATION</p><dl className="config-ledger">{configuration.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl></div><div><p className="eyebrow">DECISION NOTES</p><div className="mt-5 space-y-2">{explanations.map(([question, answer]) => <details key={question} className="methodology-disclosure"><summary>{question}<span aria-hidden="true">＋</span></summary><p>{answer}</p></details>)}</div></div></div>
    <div className="mt-10"><ProvenanceDisclosure record={{ source: "Salarium 1.0 model card and governed release snapshot", artifact: release.provenance.source_report, outOfSamplePeriod: release.research.period, portfolio: "Core balanced", model: `${a.model_horizon_days}D expanding-window rank model`, commit: release.provenance.git_commit, generatedAt: release.generated_at_utc }} /></div>
  </section></main>;
}
