# Horizon x Rebalance x Leverage Research

## Purpose

The prior horizon experiment changed the prediction target and the rebalance cadence together. That established that 10D/10D and 20D/20D were stronger than the original 5D/5D design, but it did not isolate whether the gain came from the prediction horizon, the trading cadence, or both.

This phase separates those variables without retraining models.

## Design

Reuse the existing liquid-500 out-of-sample score streams for 5D, 10D, and 20D model targets. For each model horizon, evaluate realized returns at 5D, 10D, and 20D holding/rebalance intervals by joining the matching realized-return label from the corresponding horizon score stream.

The controlled matrix is:

- model target horizons: 5D, 10D, 20D;
- rebalance cadences: 5D, 10D, 20D;
- base portfolios: equal weight and buffered inverse volatility;
- exposure controls: static 1.0x, legacy risk scaling, volatility targeting, and volatility targeting with regime/drawdown brakes;
- target volatilities: 20%, 25%, 30%;
- leverage caps: 1.25x and 1.50x;
- transaction cost: 10 bps per dollar of turnover;
- financing haircut: 5% annualized on exposure above 1.0x.

## Governance

1. No model is retrained in this phase.
2. The score at date t always comes from the original OOS walk-forward model for that target horizon.
3. The realized return used to judge a rebalance cadence comes from that cadence's independently constructed forward-return label.
4. Volatility targeting uses only prior realized OOS portfolio returns.
5. Financing cost is charged only to borrowed exposure above 1.0x.
6. Regime and drawdown brakes can reduce, but never increase, the unconstrained volatility-target exposure.
7. The 5D-model/5D-rebalance/static-1x result is checked against the archived horizon experiment as a parity contract.
8. Results are treated as research evidence, not automatically promoted to production.

## Interpretation

The primary question is whether the longer target horizon remains superior when trading frequency is held constant. A secondary question is whether 25%-30% volatility targets cause controlled leverage to activate and whether that improves the risk/return frontier after financing and turnover costs.

Avoid selecting a single configuration solely because it has the highest full-sample Sharpe. Prefer broad stability across neighboring horizon/cadence settings, year-by-year robustness, and Pareto efficiency across return, Sharpe, and drawdown.
