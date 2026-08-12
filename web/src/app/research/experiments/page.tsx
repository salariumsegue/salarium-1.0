import type { Metadata } from "next";

import { PageIntro, StatusBadge } from "@/components/ui";
import { formatDateTime, percent } from "@/lib/format";
import { loadCrisisDiversifierResearch, loadReleaseSnapshot } from "@/lib/site-data";

export const metadata: Metadata = {
  title: "Experiment Archive",
  description: "Accepted, rejected, and active Salarium research hypotheses with evidence, decisions, and provenance.",
  alternates: { canonical: "/research/experiments" },
};

const gateLabels: Array<[string, string]> = [
  ["drawdown_gate", "Maximum drawdown"],
  ["expected_shortfall_gate", "Expected shortfall"],
  ["recovery_gate", "Recovery time"],
  ["return_drag_gate", "Return drag"],
  ["sharpe_gate", "Net Sharpe"],
  ["yearly_drawdown_gate", "Yearly consistency"],
  ["holdout_drawdown_gate", "Holdout drawdown"],
  ["holdout_sharpe_gate", "Holdout Sharpe"],
  ["cost_stress_gate", "25 bp cost stress"],
];

export default function ExperimentsPage() {
  const release = loadReleaseSnapshot();
  const crisis = loadCrisisDiversifierResearch();
  const comparator = crisis.overall.find((row) => row.policy === crisis.comparator && row.period === "overall");
  const leadingGate = [...crisis.acceptance].sort((left, right) => right.drawdown_absolute_improvement - left.drawdown_absolute_improvement)[0];
  const leading = crisis.robustness.find(
    (row) => row.policy === leadingGate.policy && row.period === "overall" && row.turnover_bps === 10 && row.sleeve_budget === leadingGate.sleeve_budget,
  );
  if (!comparator || !leading) throw new Error("Crisis-diversifier public artifact is incomplete");

  const stressAssets = ["SPY", "GLD", "USO", "TLT"];
  const stressWindows = [...new Map(crisis.stress_windows.map((row) => [row.window, row.window_label])).entries()];

  return (
    <main id="main-content" className="site-main">
      <section className="page-section">
        <PageIntro eyebrow="EXPERIMENT ARCHIVE" title="Failure is signal." muted="The gate stays closed." description="Salarium preserves attractive hypotheses that failed governance alongside the decisions that shaped the locked release. Nothing is promoted because one aggregate number looks good." />

        <section className="crisis-research mt-12" aria-labelledby="crisis-title">
          <header className="crisis-research-header">
            <div>
              <p className="roman-inscription">ACTIVE RESEARCH / VII</p>
              <h2 id="crisis-title">Crisis-diversifier sleeve.</h2>
              <p>Gold, oil, Treasuries, commodities, inflation protection, cash, and cross-asset trend were tested as governed portfolio sleeves.</p>
            </div>
            <StatusBadge tone="negative">NOT PROMOTED</StatusBadge>
          </header>

          <div className="crisis-result-grid">
            <div><span>LEADING VARIANT</span><strong>{Math.round(leadingGate.sleeve_budget * 100)}% {leading.policy_label.replace(/^Strategic 10% /, "")}</strong><small>research leader, not selected policy</small></div>
            <div><span>ANNUALIZED NET</span><strong>{percent(leading.annualized_net_return)}</strong><small>{percent(comparator.annualized_net_return)} cash-yield comparator</small></div>
            <div><span>MAX DRAWDOWN</span><strong className="positive-number">{percent(leading.max_drawdown)}</strong><small>{percent(comparator.max_drawdown)} comparator</small></div>
            <div><span>NET SHARPE</span><strong>{leading.net_sharpe.toFixed(3)}</strong><small>{comparator.net_sharpe.toFixed(3)} comparator</small></div>
          </div>

          <div className="crisis-decision-grid">
            <div className="crisis-gates">
              <div className="crisis-subheading"><span>FROZEN ACCEPTANCE GATES</span><strong>{gateLabels.filter(([key]) => leadingGate[key as keyof typeof leadingGate] === true).length} / {gateLabels.length} passed</strong></div>
              {gateLabels.map(([key, label]) => {
                const passed = leadingGate[key as keyof typeof leadingGate] === true;
                return <div key={key}><span>{label}</span><b className={passed ? "gate-pass" : "gate-fail"}>{passed ? "PASS" : "FAIL"}</b></div>;
              })}
            </div>
            <div className="crisis-verdict">
              <p className="roman-inscription">DECISION / NON PROMOVETUR</p>
              <h3>Promising sample.<br />Insufficient hedge.</h3>
              <p>The leading 20% oil comparator improved maximum drawdown by {percent(leadingGate.drawdown_absolute_improvement)} and Sharpe by {leadingGate.sharpe_delta.toFixed(3)}, but reduced the longest recovery by only {percent(leadingGate.maximum_recovery_days_relative_reduction)} against a frozen 20% requirement.</p>
              <p>Its strength is concentrated in the inflationary sample. It is not reliable enough to alter the release architecture.</p>
            </div>
          </div>

          <div className="crisis-stress-table">
            <div className="crisis-subheading"><span>PRE-SPECIFIED STRESS WINDOWS / ETF TOTAL RETURN</span><strong>2008—2022</strong></div>
            <div className="crisis-stress-row crisis-stress-head"><span>Window</span>{stressAssets.map((asset) => <b key={asset}>{asset}</b>)}</div>
            {stressWindows.map(([window, label]) => <div className="crisis-stress-row" key={window}><span>{label}</span>{stressAssets.map((asset) => { const value = crisis.stress_windows.find((row) => row.window === window && row.asset === asset)?.total_return; return <b className={(value ?? 0) < 0 ? "negative-value" : "positive-number"} key={asset}>{value === undefined ? "—" : percent(value)}</b>; })}</div>)}
          </div>

          <p className="crisis-disclosure">ETF proxies, not contract-level futures. Integrated Salarium evidence covers {crisis.period.rebalances} simulated out-of-sample rebalances from 2021–2026; 2026 is partial. The fair comparator adds Treasury-bill yield to unused capital. No live performance.</p>
        </section>

        <section className="mt-16">
          <p className="roman-inscription">LOCKED RELEASE LEDGER / I—VI</p>
          <div className="mt-7 grid gap-4 lg:grid-cols-2">{release.research.decisions.map((item)=><article key={item.key} className="experiment-card"><div className="flex items-center justify-between gap-4"><span className="font-mono text-xs text-white/30">EXP {item.step}</span><StatusBadge tone={item.status==="rejected"?"negative":"positive"}>{item.status==="rejected"?"REJECTED":"ACCEPTED"}</StatusBadge></div><h2>{item.title}</h2><dl><div><dt>Hypothesis</dt><dd>{item.question}</dd></div><div><dt>Result</dt><dd>{item.finding}</dd></div><div><dt>Decision</dt><dd>{item.decision}</dd></div><div><dt>Evaluation period</dt><dd>{release.research.period}</dd></div><div><dt>Source artifact</dt><dd>{item.source_report}</dd></div><div><dt>Commit / updated</dt><dd>{release.provenance.git_commit.slice(0,12)} · {formatDateTime(release.generated_at_utc)}</dd></div></dl></article>)}</div>
        </section>
      </section>
    </main>
  );
}
