# Crisis-Diversifier Sleeve Verdict

## Decision

Do not promote any crisis-diversifier sleeve into the locked Salarium 1.0 architecture.

The experiment remains simulated research. The equity model is unchanged and no live trading capability is introduced.

## Governed comparison

| Policy | Ann. net return | Sharpe | Max drawdown | ES 95% | All gates |
|---|---:|---:|---:|---:|---|
| strategic_oil_10@20% | 48.07% | 1.497 | -33.44% | -9.17% | FAIL |
| strategic_oil_10@15% | 48.71% | 1.459 | -37.72% | -9.45% | FAIL |
| strategic_diversified_10@20% | 41.91% | 1.378 | -40.51% | -8.54% | FAIL |
| strategic_gold_10@20% | 43.74% | 1.419 | -40.71% | -8.57% | FAIL |
| strategic_oil_10@10% | 49.26% | 1.419 | -41.77% | -9.76% | FAIL |
| strategic_diversified_10@15% | 43.99% | 1.367 | -42.78% | -9.04% | FAIL |
| strategic_gold_10@15% | 45.38% | 1.396 | -42.93% | -9.05% | FAIL |
| strategic_diversified_10@10% | 46.05% | 1.355 | -45.00% | -9.55% | FAIL |
| strategic_gold_10@10% | 47.00% | 1.375 | -45.09% | -9.55% | FAIL |
| strategic_oil_10@5% | 49.74% | 1.377 | -45.61% | -10.07% | FAIL |
| strategic_diversified_10@5% | 48.10% | 1.345 | -47.15% | -10.06% | FAIL |
| strategic_gold_10@5% | 48.58% | 1.354 | -47.19% | -10.06% | FAIL |

## Oil is not a universal hedge

USO proxy returns across the pre-specified stress windows:

- Global financial crisis: -69.15%
- US debt downgrade / euro stress: -19.95%
- Q4 2018 equity selloff: -41.76%
- COVID-19 liquidity shock: -56.35%
- 2022 inflation/rate bear market: 29.36%

## Interpretation

The fair comparator is the governed equity portfolio plus Treasury-bill yield on uninvested capital. This prevents a sleeve from appearing successful merely because it earns interest on cash that the official release simulation leaves at zero.

ETF adjusted-close histories include fund-level expenses and distributions and, for futures-based funds, observed fund-level roll effects. They do not constitute a contract-level futures backtest. Institutional promotion would require explicit futures rolls, collateral, margin, tax, liquidity, and capacity analysis.

## Frozen protocol

Source: `configs/crisis_diversifier_research.json` (schema 1.0).
