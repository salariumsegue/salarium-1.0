# Salarium Strategy Walkforward Agent Report

**Status:** warn

**Summary:** Strategy walk-forward status: warn. Strategies evaluated: 15. Best strategy: macro_signal_score_only (score -1.0518, net excess 5D 0.000633, IC -0.001839). Warnings: 3. Errors: 0.

## Run Settings

| Setting | Value |
|---|---|
| `training_data_path` | `data/processed/training_data_top125_model_safe_with_macro.csv` |
| `return_column` | `target_5d_return` |
| `top_n` | `10` |
| `rebalance_step` | `5` |
| `transaction_cost_per_turnover` | `0.001` |
| `num_strategies` | `15` |

## Strategy Leaderboard

| Rank | Strategy | Score | Net Excess 5D | Long/Short 5D | Spearman IC | Net Sharpe | Max Drawdown | Weak Periods |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | `macro_signal_score_only` | -1.051800 | 0.000633 | 0.000639 | -0.001839 | 1.013014 | -0.318840 | 8 |
| 2 | `growth_num_only` | -1.566624 | 0.000406 | 0.000094 | 0.001038 | 0.993680 | -0.353015 | 8 |
| 3 | `macro_tone_score_only` | -1.585603 | 0.000410 | 0.000176 | -0.006310 | 0.932979 | -0.318840 | 8 |
| 4 | `surprise_num_only` | -1.630437 | -0.000112 | 0.000983 | 0.004027 | 0.980724 | -0.266857 | 8 |
| 5 | `five_day_market_bias_score_only` | -1.713508 | 0.000510 | 0.000261 | -0.009682 | 0.949678 | -0.318840 | 9 |
| 6 | `price_vs_ma50_only` | -2.915123 | 0.000002 | -0.000960 | -0.010685 | 0.744134 | -0.308642 | 9 |
| 7 | `liquidity_num_only` | -3.638524 | -0.001315 | 0.000345 | 0.002470 | 0.618938 | -0.299292 | 9 |
| 8 | `technical_plus_macro_combo` | -3.771292 | -0.000804 | -0.000788 | -0.012955 | 0.626638 | -0.397345 | 9 |
| 9 | `rsi_14d_only` | -4.146804 | -0.001220 | -0.000819 | -0.009278 | 0.633183 | -0.275977 | 9 |
| 10 | `momentum_20d_only` | -4.161120 | -0.001167 | -0.000841 | -0.007959 | 0.493206 | -0.428379 | 9 |
| 11 | `relative_strength_only` | -4.161120 | -0.001167 | -0.000841 | -0.007959 | 0.493206 | -0.428379 | 9 |
| 12 | `technical_combo` | -4.912351 | -0.001380 | -0.001771 | -0.014210 | 0.483932 | -0.414042 | 9 |
| 13 | `price_vs_ma20_only` | -5.345970 | -0.001509 | -0.002231 | -0.019117 | 0.415064 | -0.442100 | 9 |
| 14 | `momentum_5d_only` | -7.319716 | -0.002344 | -0.004703 | -0.024450 | 0.227378 | -0.504724 | 8 |
| 15 | `low_volatility_only` | -8.088338 | -0.002625 | -0.005995 | -0.015925 | 0.327435 | -0.245217 | 8 |

## Warnings

- Best strategy has negative Spearman IC.
- Best strategy max drawdown is worse than -25%.
- Best strategy has three or more weak yearly periods.

## Next Step

Run the Model Tournament Agent again. This agent wrote `results/model_tournament_inputs.csv`, so the tournament should now include these strategy walk-forward candidates.
