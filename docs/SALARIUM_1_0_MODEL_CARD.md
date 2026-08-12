# Salarium 1.0 Model Card

## Purpose

Salarium 1.0 is an open-source quantitative equity research system. It ranks a liquid U.S. equity universe, evaluates the rankings with expanding-window walk-forward tests, and converts the highest-ranked names into governed research portfolios.

It is not a brokerage, order-management system, live trading bot, or source of investment advice.

## Locked Release-Candidate Architecture

| Component | Release candidate |
|---|---|
| Research universe | Liquid-500 |
| Prediction target | 20 trading-day forward return |
| Rebalance cadence | Every 10 trading days |
| Portfolio breadth | Top 10 |
| Persistence buffer | Rank 15 |
| Covariance estimator | Ledoit-Wolf shrinkage |
| Covariance lookback | 60 trading days |
| Primary risk anchor | Shrinkage maximum diversification |
| Defensive risk anchor | Shrinkage minimum variance |
| Signal-aware blend | 25% signal / 75% covariance-risk challenger |
| Position direction | Long only |
| Maximum single-name weight | 18% |
| Maximum portfolio leverage | 1.25x hard ceiling |

## Core Balanced Research Candidate

The release candidate uses the 60-day shrinkage maximum-diversification risk anchor with a 25% signal-aware blend and Salarium's governed legacy risk-scaling layer.

The committed walk-forward research report currently shows approximately:

- Annualized simulated net return: 48.2%
- Net Sharpe: 1.298
- Net Sortino: 2.678
- Maximum drawdown: -49.6%
- Average exposure: 0.534x
- Maximum realized exposure in the research run: 1.00x

The 1.25x leverage ceiling is a permission limit, not an exposure target. The referenced research run did not require leverage above 1.00x.

## Validated Drawdown-Budget Candidate

A post-freeze research candidate applies a 78% soft high-water-mark floor and a 3x capital-cushion multiplier above the existing exposure layer. It reduced the observed simulated maximum drawdown to -21.6%, retained approximately 70% of the cash-yield comparator's annualized return, and improved full-period Sharpe.

It is not part of the locked release architecture. It is approved for a USD 100,000 paper-only shadow mandate with no brokerage connection, orders, or live capital. The full 2021-2026 record was inspected during design, so its 2024-2026 slice is not a pristine holdout. The floor is not a guarantee and the controller can become nearly cash-locked after a deep loss. See `docs/drawdown_budget_research.md` and `docs/drawdown_budget_shadow_mandate.md` for the evidence, activation rules, and limitations.

## Aggressive Research Reference

The same 25% signal-aware maximum-diversification portfolio at static 1.00x exposure produced a materially higher simulated return, but also materially higher volatility and drawdown. It is retained as a research comparison rather than the default release candidate.

## Defensive Research Reference

The 60-day shrinkage minimum-variance anchor with a 25% signal-aware blend and governed risk scaling is retained as a defensive comparator.

## Validation Design

Salarium uses annual expanding-window walk-forward evaluation across 2021-2026. Predictions are generated out-of-sample for each test year. Portfolio policies are then evaluated from those score streams with transaction-cost assumptions and explicit risk diagnostics.

The project also includes governance tests, leakage/data-quality checks, model tournaments, universe research, macro-regime research, portfolio breadth experiments, horizon/rebalance ablations, covariance-aware optimization, and signal-aware portfolio construction.

## Important Limitations

- Historical performance is simulated, not live performance.
- Backtests remain subject to model risk, data quality problems, survivorship/universe-selection effects, and regime dependence.
- A high historical return or Sharpe ratio is not evidence that future returns will match the backtest.
- The strategy has experienced large simulated drawdowns.
- Transaction cost and financing assumptions are approximations.
- The system does not currently execute trades.
- No research policy is represented as suitable for any person's real-money portfolio.

## Governance Principle

The release candidate freezes the upstream research architecture so release work can focus on reproducibility, transparency, documentation, deployment, and monitoring rather than continuing to optimize on the same historical sample.
