import type { Metadata } from "next";
import { loadCrisisDiversifierResearch } from "@/lib/site-data";
import { evaluateGates } from "@/lib/evidence";
import { percent } from "@/lib/format";
export const metadata: Metadata = {
  title: "Model courtroom",
  alternates: { canonical: "/research/courtroom" },
};
export default function CourtroomPage() {
  const research = loadCrisisDiversifierResearch();
  const row = research.acceptance.find(
    (r) => r.policy === "strategic_oil_10" && r.sleeve_budget === 0.2,
  );
  if (!row) throw new Error("Oil sleeve acceptance record missing");
  const verdict = evaluateGates(row as unknown as Record<string, unknown>);
  return (
    <main id="main-content" className="site-main research-page">
      <section className="site-container">
        <p className="eyebrow">MODEL COURTROOM / CASE 001</p>
        <h1>
          The oil hedge
          <br />
          on trial.
        </h1>
        <p className="research-lead">
          A 20% oil sleeve reduced simulated drawdown. It still did not earn a
          place in the released model.
        </p>
        <div className="verdict-banner">
          <strong>
            {verdict.eligible
              ? "Gates cleared; release approval still required"
              : "Not promoted"}
          </strong>
          <span>
            {verdict.passed} / {verdict.gates.length} recorded gates passed
          </span>
        </div>
        <div className="court-columns">
          <article className="research-panel">
            <p className="eyebrow">THE CASE FOR</p>
            <h2>A smaller loss in the tested sample.</h2>
            <p>
              Maximum drawdown improved by{" "}
              {(row.drawdown_absolute_improvement * 100).toFixed(1)} percentage
              points against the cash-yield comparator. Net Sharpe improved by{" "}
              {row.sharpe_delta.toFixed(3)}.
            </p>
            <p>
              Drawdown improved in {row.years_with_drawdown_improvement}{" "}
              evaluated years. The candidate also cleared the published holdout
              and cost-stress gates.
            </p>
          </article>
          <article className="research-panel objection">
            <p className="eyebrow">THE CASE AGAINST</p>
            <h2>Recovery barely changed.</h2>
            <p>
              The longest recovery shortened by{" "}
              {percent(row.maximum_recovery_days_relative_reduction)}, below the
              protocol’s 20% requirement. Annualized return drag was{" "}
              {(row.annualized_return_drag * 100).toFixed(1)} percentage points.
            </p>
            <p>
              Oil is not a general crisis hedge. ETF proxy behavior in
              inflationary conditions does not establish protection during
              deflationary or liquidity shocks.
            </p>
          </article>
        </div>
        <h2 className="research-section-title">
          The recorded acceptance tests
        </h2>
        <div className="gate-grid">
          {verdict.gates.map((g) => (
            <div
              className={`gate ${g.passed ? "" : "gate-failed"}`}
              key={g.key}
            >
              <span>{g.label}</span>
              <b>{g.passed ? "PASS" : "FAIL"}</b>
            </div>
          ))}
        </div>
        <p className="research-muted">
          Verdict computed from all nine published gate booleans. Missing or
          non-true gates fail closed. Clearing gates does not automatically
          change the release. Arguments are editorial summaries of the stored
          research, not independent AI testimony.
        </p>
        <details className="research-panel">
          <summary>Timing and evidentiary limits</summary>
          <p>
            The artifact claims a frozen protocol, but its generated timestamp (
            {research.generated_at_utc}) precedes its stated freeze time (
            {research.experiment.frozen_at_utc}). These timestamps alone do not
            independently establish preregistration.
          </p>
          <p>
            Integrated evidence is historical simulation across{" "}
            {research.period.rebalances} rebalances. ETF proxies are not
            contract-level futures execution. No live hedge was deployed.
          </p>
          <p className="hash-text">
            Source commit: {research.provenance.git_commit}
            <br />
            Configuration SHA-256: {research.provenance.config_sha256}
          </p>
          <a href="/data/crisis_diversifier_research.json">
            Read the complete case evidence ↗
          </a>
        </details>
        <a className="research-link" href="/api/evidence-bundle" download>
          Download the research bundle ↓
        </a>
      </section>
    </main>
  );
}
