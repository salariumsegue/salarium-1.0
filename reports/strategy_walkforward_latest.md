# Salarium Strategy Walkforward Agent Report

**Status:** warn

**Summary:** Strategy walk-forward status: warn. Strategies evaluated: 15. Best strategy: surprise_num_only (score 1.2409, net excess 5D 0.001500, IC 0.004038). Warnings: 3. Errors: 0.

## Run Settings

| Setting | Value |
|---|---|
| `training_data_path` | `data/processed/training_data_model_safe_with_macro.csv` |
| `return_column` | `target_5d_return` |
| `top_n` | `10` |
| `rebalance_step` | `5` |
| `transaction_cost_per_turnover` | `0.001` |
| `num_strategies` | `15` |

## Strategy Leaderboard

| Rank | Strategy | Score | Net Excess 5D | Long/Short 5D | Spearman IC | Net Sharpe | Max Drawdown | Weak Periods |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | `surprise_num_only` | 1.240913 | 0.001500 | 0.002571 | 0.004038 | 1.210335 | -0.315389 | 7 |
| 2 | `liquidity_num_only` | 0.596653 | 0.000999 | 0.002487 | 0.002420 | 1.041731 | -0.315389 | 7 |
| 3 | `growth_num_only` | -0.295015 | 0.000922 | 0.000378 | 0.002090 | 1.055877 | -0.315919 | 6 |
| 4 | `macro_signal_score_only` | -0.875503 | 0.000861 | 0.000468 | -0.001819 | 0.967595 | -0.315389 | 8 |
| 5 | `macro_tone_score_only` | -1.839868 | 0.000394 | -0.000288 | -0.006608 | 0.841130 | -0.315389 | 8 |
| 6 | `five_day_market_bias_score_only` | -2.141874 | 0.000497 | -0.000553 | -0.010251 | 0.856279 | -0.315389 | 9 |
| 7 | `price_vs_ma50_only` | -3.395086 | -0.000168 | -0.001492 | -0.009880 | 0.649525 | -0.372561 | 9 |
| 8 | `technical_plus_macro_combo` | -3.755114 | -0.000919 | -0.000964 | -0.012789 | 0.537959 | -0.434861 | 8 |
| 9 | `momentum_20d_only` | -4.021071 | -0.000974 | -0.000983 | -0.007130 | 0.468772 | -0.440529 | 9 |
| 10 | `relative_strength_only` | -4.021071 | -0.000974 | -0.000983 | -0.007130 | 0.468772 | -0.440529 | 9 |
| 11 | `rsi_14d_only` | -4.190662 | -0.001260 | -0.000824 | -0.009183 | 0.568945 | -0.277123 | 9 |
| 12 | `technical_combo` | -5.252529 | -0.001664 | -0.001815 | -0.014146 | 0.372451 | -0.435930 | 9 |
| 13 | `price_vs_ma20_only` | -5.711397 | -0.001708 | -0.002524 | -0.018492 | 0.331772 | -0.463591 | 9 |
| 14 | `momentum_5d_only` | -7.291140 | -0.002434 | -0.004456 | -0.025632 | 0.175979 | -0.486572 | 8 |
| 15 | `low_volatility_only` | -8.523250 | -0.002703 | -0.006728 | -0.014228 | 0.248121 | -0.243737 | 8 |

## Warnings

- Best strategy has positive but weak Spearman IC.
- Best strategy max drawdown is worse than -25%.
- Best strategy has three or more weak yearly periods.

## Next Step

Run the Model Tournament Agent again. This agent wrote `results/model_tournament_inputs.csv`, so the tournament should now include these strategy walk-forward candidates.
