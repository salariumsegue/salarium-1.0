"use client";
import { useState } from "react";
import type { ForwardPaperSnapshot } from "@/lib/site-types";
import { dependencyGroups } from "@/lib/dependencies";
import { percent } from "@/lib/format";
export default function DependencyMap({
  snapshot,
}: {
  snapshot: ForwardPaperSnapshot;
}) {
  const [selected, setSelected] = useState<string>(dependencyGroups[0].id);
  const group = dependencyGroups.find((g) => g.id === selected)!;
  const holdings = snapshot.forward_portfolio.holdings;
  const matched = holdings.filter((h) =>
    group.members.some((m) => m.ticker === h.ticker),
  );
  const taggedWeight = matched.reduce((sum, h) => sum + h.paper_weight, 0);
  const reviewed = new Set<string>(
    dependencyGroups.flatMap((g) => g.members.map((m) => m.ticker)),
  );
  const unreviewed = holdings.filter((h) => !reviewed.has(h.ticker));
  return (
    <div>
      <div
        className="dependency-tabs"
        role="group"
        aria-label="Research themes"
      >
        {dependencyGroups.map((g) => (
          <button
            type="button"
            key={g.id}
            aria-pressed={g.id === selected}
            onClick={() => setSelected(g.id)}
          >
            {g.label}
          </button>
        ))}
      </div>
      <div className="dependency-network" aria-live="polite">
        <div className="dependency-hub">
          <p className="eyebrow">INFERRED THEME / CURRENT HOLDINGS</p>
          <h2>{group.label}</h2>
          <strong>{percent(taggedWeight)}</strong>
          <p>Tagged allocation as a share of paper NAV</p>
        </div>
        <div className="dependency-branches">
          {matched.map((h) => {
            const source = group.members.find((m) => m.ticker === h.ticker)!;
            return (
              <article key={h.ticker}>
                <div>
                  <b>{h.ticker}</b>
                  <span>{percent(h.paper_weight)} of NAV</span>
                </div>
                <p>{source.basis}</p>
                <a href={source.url} target="_blank" rel="noreferrer">
                  Company source ↗
                </a>
              </article>
            );
          })}
          {matched.length === 0 && <p>No current holdings match this theme.</p>}
        </div>
      </div>
      <p className="research-muted">
        {group.thesis} Allocation is calculated from published paper weights;
        the business links are editorial classifications reviewed October 6,
        2026. Themes overlap and must not be added together.
      </p>
      <div className="research-grid">
        <article className="research-panel">
          <p className="eyebrow">MEASURED / PORTFOLIO DIAGNOSTIC</p>
          <h2>
            {snapshot.forward_portfolio.portfolio_diagnostics.average_pairwise_correlation?.toFixed(
              3,
            ) ?? "Unavailable"}
          </h2>
          <p>
            Average pairwise correlation in the published covariance diagnostic.
            This is not a correlation estimate for the selected theme.
          </p>
        </article>
        <article className="research-panel">
          <p className="eyebrow">COVERAGE / STILL UNCLASSIFIED</p>
          <h2>{unreviewed.length} holdings</h2>
          <p>
            {unreviewed.map((h) => h.ticker).join(", ") ||
              "All current holdings have at least one reviewed tag."}
          </p>
          <p>
            Unclassified means unreviewed—not independent. No numerical rate
            sensitivity or revenue exposure is claimed.
          </p>
        </article>
      </div>
    </div>
  );
}
