# Macro Walk-Forward Verdict

## Decision

The technical-plus-macro model is not promoted as Salarium's core ranking model.

## Overall Results

| Metric | Technical Only | Technical Plus Macro |
|---|---:|---:|
| Average net excess 5D | 0.007242 | 0.000803 |
| Average long-short 5D | 0.003049 | -0.004641 |
| Average Spearman IC | 0.001622 | -0.002364 |
| Average turnover | 1.071014 | 1.297826 |
| Annualized net return | 0.477537 | 0.128710 |
| Net Sharpe | 0.912477 | 0.491419 |
| Excess Sharpe | 0.653082 | 0.084116 |
| Maximum drawdown | -0.821457 | -0.769989 |

## Interpretation

Adding macro features directly to the ranking model materially reduced excess return,
long-short performance, ranking IC, and risk-adjusted performance while increasing
turnover. Drawdown improved modestly but remained severe.

Macro improved some individual years, especially 2021, 2022, and 2026, suggesting
that macro information may be more useful as a conditional regime filter, confidence
modifier, or exposure-control layer than as a universal stock-ranking feature block.

## Next Research Step

Retain the technical-only model as the primary baseline and test portfolio-level risk
controls, turnover reduction, position persistence, and volatility-aware weighting.
