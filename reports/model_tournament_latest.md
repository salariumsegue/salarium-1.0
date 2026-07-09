# Salarium Model Tournament Agent Report

**Status:** warn

**Summary:** Model tournament status: warn. Candidates evaluated: 18. Best in macro_holdout: technical_plus_macro_llm (score 1.3616). Best in strategy_walkforward: price_vs_ma50_only (score -2.8353). Best in walkforward_rank: current_walkforward_rank_model (score 1.4581). Warnings: 4. Errors: 0.

## Tournament Leaderboard

| Group | Rank | Candidate | Score | Scope | Net Excess 5D | Long/Short 5D | Spearman IC | Excess Top-5 | AUC | Weak Periods |
|---|---:|---|---:|---|---:|---:|---:|---:|---:|---:|
| macro_holdout | 1 | `technical_plus_macro_llm` | 1.361600 | single_train_test_top5 |  |  |  | 0.001180 | 0.510000 |  |
| macro_holdout | 2 | `baseline_technical_only` | 1.053600 | single_train_test_top5 |  |  |  | 0.000870 | 0.508200 |  |
| strategy_walkforward | 1 | `price_vs_ma50_only` | -2.835320 | top10_walkforward | 0.000002 | -0.000960 | -0.010685 |  |  | 9 |
| strategy_walkforward | 2 | `macro_signal_score_only` | -3.323006 | top10_walkforward | -0.001178 | 0.000211 | 0.000000 |  |  | 9 |
| strategy_walkforward | 3 | `macro_tone_score_only` | -3.323006 | top10_walkforward | -0.001178 | 0.000211 | 0.000000 |  |  | 9 |
| strategy_walkforward | 4 | `surprise_num_only` | -3.323006 | top10_walkforward | -0.001178 | 0.000211 | 0.000000 |  |  | 9 |
| strategy_walkforward | 5 | `liquidity_num_only` | -3.323006 | top10_walkforward | -0.001178 | 0.000211 | 0.000000 |  |  | 9 |
| strategy_walkforward | 6 | `five_day_market_bias_score_only` | -3.323006 | top10_walkforward | -0.001178 | 0.000211 | 0.000000 |  |  | 9 |
| strategy_walkforward | 7 | `growth_num_only` | -3.323006 | top10_walkforward | -0.001178 | 0.000211 | 0.000000 |  |  | 9 |
| strategy_walkforward | 8 | `momentum_20d_only` | -3.917253 | top10_walkforward | -0.001167 | -0.000841 | -0.007959 |  |  | 9 |
| strategy_walkforward | 9 | `relative_strength_only` | -3.917253 | top10_walkforward | -0.001167 | -0.000841 | -0.007959 |  |  | 9 |
| strategy_walkforward | 10 | `rsi_14d_only` | -3.972016 | top10_walkforward | -0.001220 | -0.000819 | -0.009278 |  |  | 9 |
| strategy_walkforward | 11 | `technical_combo` | -4.657787 | top10_walkforward | -0.001380 | -0.001771 | -0.014210 |  |  | 9 |
| strategy_walkforward | 12 | `technical_plus_macro_combo` | -4.657787 | top10_walkforward | -0.001380 | -0.001771 | -0.014210 |  |  | 9 |
| strategy_walkforward | 13 | `price_vs_ma20_only` | -5.065396 | top10_walkforward | -0.001509 | -0.002231 | -0.019117 |  |  | 9 |
| strategy_walkforward | 14 | `momentum_5d_only` | -6.939803 | top10_walkforward | -0.002344 | -0.004703 | -0.024450 |  |  | 8 |
| strategy_walkforward | 15 | `low_volatility_only` | -7.781169 | top10_walkforward | -0.002625 | -0.005995 | -0.015925 |  |  | 8 |
| walkforward_rank | 1 | `current_walkforward_rank_model` | 1.458118 | top10_walkforward | 0.001446 | 0.001887 | 0.006883 |  |  | 4 |

## Group Winners

- **macro_holdout**: `technical_plus_macro_llm` (score 1.3616, scope `single_train_test_top5`)
- **strategy_walkforward**: `price_vs_ma50_only` (score -2.8353, scope `top10_walkforward`)
- **walkforward_rank**: `current_walkforward_rank_model` (score 1.4581, scope `top10_walkforward`)

## Interpretation

This is a tournament aggregator, not a full retraining engine yet. It ranks all available strategy/model result files using a consistent scoring formula. The next upgrade is to make every candidate run through the same walk-forward backtest.

## Warnings

- Walk-forward ranking IC is positive but weak.
- Walk-forward model has three or more weak periods.
- Macro holdout candidates are from a single train/test comparison. Current best macro-holdout candidate: technical_plus_macro_llm.
- Do not compare macro_holdout and walkforward_rank as identical tests yet. The next upgrade is to run every candidate through the same walk-forward engine.

## Score Formula

```json
{
  "avg_net_excess_5d": "1000x",
  "avg_long_short_5d": "500x",
  "avg_spearman_ic": "10x",
  "excess_top5_return": "1000x",
  "auc_above_0_5": "10x",
  "accuracy_above_0_5": "2x",
  "weak_period_count": "-0.25 each"
}
```
