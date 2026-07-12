# Salarium Model Tournament Agent Report

**Status:** warn

**Summary:** Model tournament status: warn. Candidates evaluated: 34. Best in macro_holdout: technical_plus_macro_llm (score 1.3616). Best in strategy_walkforward: inflation_x_low_volatility (score 4.3292). Best in walkforward_rank: current_walkforward_rank_model (score 1.4581). Warnings: 4. Errors: 0.

## Tournament Leaderboard

| Group | Rank | Candidate | Score | Scope | Net Excess 5D | Long/Short 5D | Spearman IC | Excess Top-5 | AUC | Weak Periods |
|---|---:|---|---:|---|---:|---:|---:|---:|---:|---:|
| macro_holdout | 1 | `technical_plus_macro_llm` | 1.361600 | single_train_test_top5 |  |  |  | 0.001180 | 0.510000 |  |
| macro_holdout | 2 | `baseline_technical_only` | 1.053600 | single_train_test_top5 |  |  |  | 0.000870 | 0.508200 |  |
| strategy_walkforward | 1 | `inflation_x_low_volatility` | 4.329224 | top10_walkforward | 0.002948 | 0.004940 | 0.016170 |  |  | 5 |
| strategy_walkforward | 2 | `rate_policy_x_low_volatility` | 3.669603 | top10_walkforward | 0.002652 | 0.004334 | 0.010037 |  |  | 5 |
| strategy_walkforward | 3 | `return_1d_reversal` | 2.910777 | top10_walkforward | 0.001654 | 0.004040 | 0.023614 |  |  | 4 |
| strategy_walkforward | 4 | `five_day_bias_x_momentum_20d` | 1.126703 | top10_walkforward | 0.001035 | 0.003588 | 0.004780 |  |  | 7 |
| strategy_walkforward | 5 | `macro_tone_x_relative_strength` | 0.164853 | top10_walkforward | 0.000412 | 0.002393 | 0.005629 |  |  | 6 |
| strategy_walkforward | 6 | `rate_policy_x_price_vs_ma50` | -0.121163 | top10_walkforward | 0.001040 | 0.001178 | 0.000009 |  |  | 7 |
| strategy_walkforward | 7 | `macro_signal_x_momentum_20d` | -0.446560 | top10_walkforward | 0.000236 | 0.002073 | 0.003139 |  |  | 7 |
| strategy_walkforward | 8 | `macro_signal_x_relative_strength` | -0.446560 | top10_walkforward | 0.000236 | 0.002073 | 0.003139 |  |  | 7 |
| strategy_walkforward | 9 | `macro_signal_x_technical_combo` | -0.581042 | top10_walkforward | 0.000238 | 0.001757 | 0.005185 |  |  | 7 |
| strategy_walkforward | 10 | `risk_on_x_relative_strength` | -0.702849 | top10_walkforward | 0.000106 | 0.001812 | 0.003532 |  |  | 7 |
| strategy_walkforward | 11 | `risk_on_x_momentum_20d` | -0.702849 | top10_walkforward | 0.000106 | 0.001812 | 0.003532 |  |  | 7 |
| strategy_walkforward | 12 | `surprise_x_low_volatility` | -0.931044 | top10_walkforward | 0.000284 | -0.000451 | 0.001039 |  |  | 4 |
| strategy_walkforward | 13 | `macro_signal_x_price_vs_ma50` | -1.066803 | top10_walkforward | 0.000719 | 0.000560 | -0.006549 |  |  | 8 |
| strategy_walkforward | 14 | `growth_x_relative_strength` | -1.680546 | top10_walkforward | -0.000505 | 0.000608 | 0.001998 |  |  | 6 |
| strategy_walkforward | 15 | `volume_change_1d_only` | -2.600043 | top10_walkforward | -0.001610 | 0.001439 | 0.003987 |  |  | 7 |
| strategy_walkforward | 16 | `price_vs_ma50_only` | -2.835320 | top10_walkforward | 0.000002 | -0.000960 | -0.010685 |  |  | 9 |
| strategy_walkforward | 17 | `risk_off_x_low_volatility` | -2.877628 | top10_walkforward | -0.000586 | -0.002095 | 0.000620 |  |  | 5 |
| strategy_walkforward | 18 | `liquidity_x_relative_strength` | -3.058578 | top10_walkforward | -0.001198 | -0.000870 | 0.007451 |  |  | 6 |
| strategy_walkforward | 19 | `liquidity_x_momentum_20d` | -3.058578 | top10_walkforward | -0.001198 | -0.000870 | 0.007451 |  |  | 6 |
| strategy_walkforward | 20 | `relative_strength_only` | -3.917253 | top10_walkforward | -0.001167 | -0.000841 | -0.007959 |  |  | 9 |
| strategy_walkforward | 21 | `momentum_20d_only` | -3.917253 | top10_walkforward | -0.001167 | -0.000841 | -0.007959 |  |  | 9 |
| strategy_walkforward | 22 | `rsi_14d_only` | -3.972016 | top10_walkforward | -0.001220 | -0.000819 | -0.009278 |  |  | 9 |
| strategy_walkforward | 23 | `price_vs_ma20_only` | -5.065396 | top10_walkforward | -0.001509 | -0.002231 | -0.019117 |  |  | 9 |
| strategy_walkforward | 24 | `open_close_spread_only` | -5.762015 | top10_walkforward | -0.002379 | -0.002506 | -0.013018 |  |  | 8 |
| strategy_walkforward | 25 | `surprise_x_relative_strength` | -6.386151 | top10_walkforward | -0.002819 | -0.004116 | -0.000852 |  |  | 6 |
| strategy_walkforward | 26 | `return_1d_momentum` | -6.409846 | top10_walkforward | -0.002403 | -0.004040 | -0.023614 |  |  | 7 |
| strategy_walkforward | 27 | `technical_combo` | -6.527771 | top10_walkforward | -0.002369 | -0.003463 | -0.017700 |  |  | 9 |
| strategy_walkforward | 28 | `low_high_low_spread` | -6.706489 | top10_walkforward | -0.002708 | -0.003343 | -0.007696 |  |  | 9 |
| strategy_walkforward | 29 | `return_5d_momentum` | -6.939803 | top10_walkforward | -0.002344 | -0.004703 | -0.024450 |  |  | 8 |
| strategy_walkforward | 30 | `momentum_5d_only` | -6.939803 | top10_walkforward | -0.002344 | -0.004703 | -0.024450 |  |  | 8 |
| strategy_walkforward | 31 | `low_volatility_only` | -7.781169 | top10_walkforward | -0.002625 | -0.005995 | -0.015925 |  |  | 8 |
| walkforward_rank | 1 | `current_walkforward_rank_model` | 1.458118 | top10_walkforward | 0.001446 | 0.001887 | 0.006883 |  |  | 4 |

## Group Winners

- **macro_holdout**: `technical_plus_macro_llm` (score 1.3616, scope `single_train_test_top5`)
- **strategy_walkforward**: `inflation_x_low_volatility` (score 4.3292, scope `top10_walkforward`)
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
