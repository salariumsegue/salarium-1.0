# Portfolio Breadth + Leverage Research

This research phase holds the current leading alpha architecture fixed at a **20-trading-day prediction target** and a **10-trading-day rebalance/holding period**. It changes only portfolio breadth and the post-portfolio exposure controller.

## Breadth grid

- Top 10
- Top 20
- Top 30
- Top 50
- Top 75

Both equal-weight and buffered inverse-volatility construction are evaluated. The turnover buffer scales proportionally with breadth at 1.5x the target holding count, preserving the original Top-10 / rank-15 design.

## Exposure grid

The experiment reuses the governed exposure specifications from the horizon/rebalance research: static 1.0x, legacy risk scaling, 20%/25%/30% volatility targets, 1.25x/1.50x leverage caps, and guarded regime/drawdown variants. Financing costs remain charged only to exposure above 1.0x.

## Research question

The goal is not to force leverage. The goal is to determine whether broader portfolios reduce realized volatility enough to preserve alpha while making occasional leverage economically defensible.

No model retraining is performed. Existing genuine OOS 20D score streams and 10D realized outcomes are reused.
