# Drawdown-Budget Controller Verdict

## Decision

Retain the drawdown-budget controller as a validated research candidate; do not promote it into the canonical release yet.

The ranking model and covariance-aware Top-10 constructor are unchanged. This is a point-in-time exposure overlay, not a claim that losses are capped or guaranteed.
The 2024–2026 segment was inspected during exploratory design, so it is a temporal confirmation segment rather than a pristine holdout. Independent forward or newly sequestered evidence is still required for release promotion.
The candidate is approved for a zero-capital shadow mandate with 100,000 USD paper notional. It is awaiting the first eligible post-approval portfolio snapshot; historical results will not be backfilled into the forward ledger.

## Governed result

| Record | Ann. net return | Sharpe | Max drawdown |
|---|---:|---:|---:|
| Cash-yield comparator | 50.14% | 1.335 | -49.24% |
| Drawdown budget | 35.11% | 1.435 | -21.57% |
| Confirmation 2024–2026 | 75.93% | 2.208 | -12.23% |

## Robustness

- Frozen 25 bps turnover-cost stress maximum drawdown: -21.59%.
- Parameter-neighborhood drawdown pass rate: 100.0% across 27 period checks.
- Path-dependent block-bootstrap probability of a drawdown below 25%: 100.0% across 10,000 samples.
- Path-dependent block-bootstrap probability of improving drawdown versus the comparator: 99.5%.

## Important limit

The 78% high-water-mark floor is soft. A market gap between rebalance observations can breach it, and a prolonged loss can leave the strategy with very low exposure and a slow recovery. The historical maximum drawdown is evidence, not a guarantee.

## Frozen protocol

Source: `configs/drawdown_budget_research.json` (schema 1.0).
