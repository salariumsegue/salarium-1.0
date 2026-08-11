# Horizon and Exposure Research

This branch tests two independent Salarium design questions without changing the production-approved policy registry:

1. Is the current five-trading-day prediction/rebalance horizon economically justified?
2. Can a bounded, risk-aware exposure controller improve the risk/return frontier without manufacturing backtest returns through static leverage?

## Horizon tournament

The controlled target/rebalance horizons are 1, 5, 10, and 20 trading days. The same liquid-500 feature population, technical feature policy, Random Forest class, clipping policy, annual expanding-window walk-forward discipline, and random seed are retained. The only intended alpha-model changes are:

- the forward-return label horizon;
- the matching purge length; and
- the matching non-overlapping rebalance cadence used by the tournament evaluator.

The existing feature builder already computes forward labels from adjusted prices for an arbitrary positive horizon. This experiment reconstructs those labels from the same discovery price caches and verifies that its rebuilt five-day target matches the canonical five-day target before training.

The column `target_return` in horizon score artifacts is generic by design. `target_horizon_days` records its exact meaning.

## Exposure tournament

Exposure is applied after stock ranking and base portfolio construction. The alpha model never receives leverage as a feature and never directly predicts portfolio exposure.

Research exposure policies:

- `static_1x`: no leverage or deleveraging.
- `legacy_risk_scaled`: existing Salarium regime exposure policy, which remains capped at 1.0x.
- `vol_target_max_1p25`: trailing realized unlevered portfolio volatility targeting, bounded to 0.50x-1.25x.
- `vol_target_max_1p50`: same, bounded to 0.50x-1.50x.
- `regime_dd_vol_target_max_1p25`: volatility targeting plus regime/confidence gates and drawdown brakes.
- `regime_dd_vol_target_max_1p50`: same with a 1.50x maximum.

Dynamic volatility estimates use only prior out-of-sample unlevered portfolio returns. They cannot use the current period's realized forward return. A minimum of six prior rebalance observations is required; before then exposure defaults to 1.0x unless the legacy risk policy is being evaluated.

The regime/drawdown controller prevents leverage when regime confidence is absent, prevents leverage in neutral states, caps risk-off exposure at 0.65x, and progressively limits exposure after 10%, 15%, and 20% strategy drawdowns.

## Costs

Transaction costs retain the existing 10 bps per dollar traded research assumption. Borrowed exposure above 1.0x receives a configurable annual financing-rate haircut, defaulting to 5% and prorated by the target horizon. This is deliberately a research haircut rather than a claim of historically exact financing rates.

## Governance

No production policy is promoted automatically. The tournament archives overall and yearly results, including return, Sharpe, Sortino, drawdown, turnover, financing cost, average/max exposure, share of periods using leverage, and yearly robustness versus the same horizon/base policy at static 1.0x.

The liquid-500 panel remains subject to its documented survivorship-bias limitation. These experiments are model-design research, not unbiased historical alpha claims.
