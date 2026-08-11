# Covariance-Aware Concentrated Portfolio Research

This phase keeps Salarium's leading alpha architecture fixed:

- liquid-500 research universe;
- 20-trading-day prediction target;
- rebalance every 10 trading days;
- concentrated Top-10 / Top-15 candidate portfolios.

The experiment changes portfolio construction rather than retraining the alpha model.

## Constructors

1. Governed capped inverse volatility (parity benchmark).
2. Ledoit-Wolf shrinkage minimum variance.
3. Ledoit-Wolf shrinkage equal-risk-contribution approximation.
4. Ledoit-Wolf shrinkage maximum diversification.

Covariance matrices use only historical daily adjusted-price returns available on or before each rebalance date. The tournament tests 60- and 120-session lookbacks and records optimizer fallbacks explicitly.

## Concentration governance

Portfolio weights are long-only, sum to 100% before the exposure controller, and are capped at 18% per security. The experiment intentionally avoids broad Top-50/Top-75 portfolios because prior research showed that breadth reduced volatility but diluted alpha materially.

## Exposure governance

The leverage cap is hard-limited to **1.25x**. Research exposure policies include static 1.0x, the existing Salarium regime controller, and volatility targets of 25%, 30%, and 35%, both with and without regime/drawdown brakes. Financing costs remain included.

The goal is not to force leverage. The goal is to determine whether covariance-aware construction lowers intrinsic portfolio risk enough that limited leverage becomes an efficient consequence of better diversification.

## Promotion standard

A covariance constructor should not replace the existing Top-10 inverse-volatility baseline merely because it lowers volatility. Promotion requires a credible improvement in the return / Sharpe / drawdown frontier, stable yearly behavior, low optimizer fallback rates, and no dependence on leverage above 1.25x.
