# Salarium 1.0 Release Candidate Notes

## What Salarium has become

Salarium began as a small technical stock-ranking experiment and evolved into a modular quantitative equity research platform with point-in-time research controls, walk-forward validation, macro/risk context, portfolio-construction experiments, agentic research tooling, reproducible reports, a Streamlit command center, and a public Next.js research interface.

## Major research decisions carried into the release candidate

1. The official release research universe remains the Liquid-500 benchmark rather than the broader ~2,000-name universe. The broader universe is retained for research because the current model did not generalize uniformly across the expanded cross-section.
2. The original 5-day prediction/rebalance design is superseded by a 20-day prediction target with a 10-day rebalance cadence for the release candidate.
3. Alpha remains concentrated at the top of the ranking, so the release candidate retains a Top-10 portfolio rather than diluting the signal across 50-75 names.
4. Portfolio construction uses a 60-day Ledoit-Wolf shrinkage covariance estimate.
5. Maximum diversification is the primary covariance risk anchor; minimum variance is retained as a defensive comparator.
6. A 25% signal-aware weighting blend is retained as a challenger because it increases model influence and simulated return without allowing signal magnitude to dominate portfolio risk.
7. Maximum leverage is governed by a hard 1.25x ceiling. Leverage is optional and must be earned by the risk engine.

## Release philosophy

Salarium 1.0 is being released as a research system, not as a claim of a deployable trading edge. The release emphasizes reproducibility, architecture, research discipline, and honest presentation of both improvements and limitations.

## Post-freeze research candidate

The repository now contains a validated high-water-mark drawdown-budget candidate that reached a -21.6% simulated maximum drawdown. It is approved for a USD 100,000 paper-only shadow mandate, with no historical backfill, brokerage connection, orders, or live capital. It remains outside the canonical release pending independent forward or newly sequestered evidence plus separate release approval; the current 2024-2026 segment was inspected during design and is not represented as a pristine holdout.
