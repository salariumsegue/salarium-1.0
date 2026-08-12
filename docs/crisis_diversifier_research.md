# Crisis-Diversifier Sleeve Research Protocol

## Research question

Can Salarium use a bounded portion of capital as a crisis-diversifier sleeve to reduce tail loss and recovery time without materially diluting the governed equity return stream?

This is an experimental portfolio-governance layer. It does not change the Liquid-500 universe, 20-day alpha model, Top-10 selection, covariance optimizer, signal blend, or existing equity exposure governor.

## Why the sleeve is cash-funded

The selected Salarium policy already reduces equity exposure to 0.45x in its risk-off state. The primary sleeve experiments may invest at most part of the remaining defensive reserve. Total capital is capped at 1.0x and the experiment does not introduce leverage into the release portfolio.

Permanent 10% gold, oil, and diversified allocations are retained as direct comparators. They proportionally reduce the equity stream so that the original hypothesis is tested rather than assumed.

## Tradable proxies

The first research pass uses adjusted-close ETF total-return histories:

- GLD: physical gold exposure;
- USO: WTI futures-roll exposure;
- DBC: diversified commodity futures-roll exposure;
- TLT: long-duration US Treasury exposure;
- TIP: inflation-linked US Treasury exposure;
- BIL: Treasury-bill collateral and cash yield;
- UUP: long-US-dollar futures-roll exposure;
- SPY: equity stress benchmark and one market in the trend overlay.

ETF histories are used because they represent investable, cost-bearing implementations and capture fund-level roll effects where applicable. They are not a substitute for institutional futures histories. Promotion beyond research would require contract-level futures data, explicit roll rules, collateral accounting, margin, and capacity analysis.

## Point-in-time rules

- Every allocation decision uses only prices available through the session before the rebalance date.
- Trend votes use 63-, 126-, and 252-session total returns.
- An asset is eligible for the long-only trend sleeve when at least two horizons are positive.
- Eligible assets are inverse-volatility weighted using a trailing 60-session window.
- The long/short overlay takes the majority trend direction and scales absolute weights by trailing volatility.
- The existing Salarium risk state sets the maximum cash-funded sleeve budget: 20% risk-off, 10% neutral, and 0% risk-on.
- If no defensive asset has a qualifying positive trend, the sleeve remains in the Treasury-bill proxy.

## Costs and accounting

The existing equity return stream remains net of its modeled transaction costs. The sleeve adds turnover costs independently, with 10 basis points as the base assumption and 5/10/25/50 basis-point stress cases. Short positions include a 50-basis-point annual borrow assumption. Adjusted ETF histories incorporate fund expenses and distributions but not investor taxes.

## Validation design

- Integrated out-of-sample Salarium comparison: 2021-2026, 139 rebalance observations.
- Development segment: 2021-2023.
- Confirmatory holdout: 2024-2026, with 2026 explicitly partial.
- Independent proxy stress windows: 2008 financial crisis, 2011 debt/euro stress, Q4 2018, the 2020 COVID crash, and the 2022 inflation/rate bear market.
- Robustness grid: 5%, 10%, 15%, and 20% sleeve budgets; 5, 10, 25, and 50 basis-point turnover costs.
- Paired moving-block bootstrap: 10,000 samples with six-rebalance blocks.

## Frozen promotion gates

A candidate must satisfy every gate specified in `configs/crisis_diversifier_research.json`. The principal requirements are at least eight percentage points of maximum-drawdown improvement, at least 10% relative expected-shortfall improvement, at least 20% shorter maximum recovery, no more than five percentage points of annualized return drag, no Sharpe deterioration, drawdown improvement in at least four calendar years, non-worsening holdout drawdown and Sharpe, and survival at 25-basis-point turnover cost.

Failure is evidence. An attractive aggregate result that fails a holdout, robustness, provenance, or implementation gate remains experimental and is not added to the locked Salarium release architecture.
