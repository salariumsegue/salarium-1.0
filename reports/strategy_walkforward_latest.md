# Salarium Strategy Walkforward Agent Report

**Status:** warn

**Summary:** Strategy walk-forward status: warn. Strategies evaluated: 15. Best strategy: price_vs_ma50_only (score -2.9151, net excess 5D 0.000002, IC -0.010685). Warnings: 3. Errors: 0.

## Run Settings

| Setting | Value |
|---|---|
| `training_data_path` | `data/processed/training_data_top125_model_safe_with_global_macro.csv` |
| `return_column` | `target_5d_return` |
| `top_n` | `10` |
| `rebalance_step` | `5` |
| `transaction_cost_per_turnover` | `0.001` |
| `num_strategies` | `15` |

## Strategy Leaderboard

| Rank | Strategy | Score | Net Excess 5D | Long/Short 5D | Spearman IC | Net Sharpe | Max Drawdown | Weak Periods |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | `price_vs_ma50_only` | -2.915123 | 0.000002 | -0.000960 | -0.010685 | 0.744134 | -0.308642 | 9 |
| 2 | `macro_signal_score_only` | -3.559244 | -0.001178 | 0.000211 | 0.000000 | 0.673968 | -0.266857 | 9 |
| 3 | `macro_tone_score_only` | -3.559244 | -0.001178 | 0.000211 | 0.000000 | 0.673968 | -0.266857 | 9 |
| 4 | `surprise_num_only` | -3.559244 | -0.001178 | 0.000211 | 0.000000 | 0.673968 | -0.266857 | 9 |
| 5 | `liquidity_num_only` | -3.559244 | -0.001178 | 0.000211 | 0.000000 | 0.673968 | -0.266857 | 9 |
| 6 | `five_day_market_bias_score_only` | -3.559244 | -0.001178 | 0.000211 | 0.000000 | 0.673968 | -0.266857 | 9 |
| 7 | `growth_num_only` | -3.559244 | -0.001178 | 0.000211 | 0.000000 | 0.673968 | -0.266857 | 9 |
| 8 | `rsi_14d_only` | -4.146804 | -0.001220 | -0.000819 | -0.009278 | 0.633183 | -0.275977 | 9 |
| 9 | `momentum_20d_only` | -4.161120 | -0.001167 | -0.000841 | -0.007959 | 0.493206 | -0.428379 | 9 |
| 10 | `relative_strength_only` | -4.161120 | -0.001167 | -0.000841 | -0.007959 | 0.493206 | -0.428379 | 9 |
| 11 | `technical_combo` | -4.912351 | -0.001380 | -0.001771 | -0.014210 | 0.483932 | -0.414042 | 9 |
| 12 | `technical_plus_macro_combo` | -4.912351 | -0.001380 | -0.001771 | -0.014210 | 0.483932 | -0.414042 | 9 |
| 13 | `price_vs_ma20_only` | -5.345970 | -0.001509 | -0.002231 | -0.019117 | 0.415064 | -0.442100 | 9 |
| 14 | `momentum_5d_only` | -7.319716 | -0.002344 | -0.004703 | -0.024450 | 0.227378 | -0.504724 | 8 |
| 15 | `low_volatility_only` | -8.088338 | -0.002625 | -0.005995 | -0.015925 | 0.327435 | -0.245217 | 8 |

## Warnings

- Best strategy has negative Spearman IC.
- Best strategy max drawdown is worse than -25%.
- Best strategy has three or more weak yearly periods.

## Next Step

Run the Model Tournament Agent again. This agent wrote `results/model_tournament_inputs.csv`, so the tournament should now include these strategy walk-forward candidates.
