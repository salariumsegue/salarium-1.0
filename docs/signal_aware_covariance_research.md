# Signal-Aware Covariance Optimization

This phase locks the strongest structural decisions from the preceding Salarium research and changes only the final Top-10 weights.

## Locked Salarium 1.0 research architecture

- liquid-500 investable universe;
- 20-trading-day model target;
- rebalance every 10 trading days;
- concentrated Top-10 portfolio;
- rank-15 persistence buffer;
- 60-session point-in-time Ledoit-Wolf covariance matrix;
- long-only weights summing to 100% before exposure scaling;
- 18% maximum position weight;
- 1.25x hard maximum portfolio leverage;
- existing transaction-cost and financing-cost treatment;
- no new alpha-model training in this phase.

The two retained covariance risk anchors are 60D shrinkage maximum diversification and 60D shrinkage minimum variance. Prior experiments showed that broadening beyond Top-10 diluted alpha and that 120D covariance estimates were less reliable.

## Signal-aware weighting

The current covariance optimizers know which ten stocks survived the alpha ranking but do not know whether stock #1 is materially more attractive than stock #10 when choosing weights.

For each rebalance date, the model score is standardized across the full liquid-500 cross section and clipped to limit outlier influence. The Top-10 scores are converted into a capped positive signal portfolio. Final weights are a governed convex blend:

`w_final = (1 - alpha) * w_covariance + alpha * w_signal`

The tournament tests only four economically interpretable signal shares: 0%, 25%, 50%, and 75%. A 100% signal portfolio is intentionally excluded because this phase is testing whether alpha information improves covariance weighting, not whether risk optimization should be discarded.

## Promotion standard

A signal-aware blend is not promoted because one aggregate Sharpe is highest. Promotion requires:

1. improvement versus the same covariance anchor at 0% signal blend;
2. credible year-by-year robustness;
3. no violation of the 18% position cap or 1.25x leverage cap;
4. no increase in optimizer fallback dependence;
5. a sensible return / Sharpe / drawdown tradeoff rather than a single optimized point.

The preferred outcome is a stable region such as 25%-50% signal influence rather than one isolated winning parameter.
