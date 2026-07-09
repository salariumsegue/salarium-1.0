# Salarium Strategy Walkforward Agent Report

**Status:** warn

**Summary:** Strategy walk-forward status: warn. Strategies evaluated: 31. Best strategy: inflation_x_low_volatility (score 4.2968, net excess 5D 0.002948, IC 0.016170). Warnings: 2. Errors: 0.

## Run Settings

| Setting | Value |
|---|---|
| `training_data_path` | `data/processed/training_data_top125_model_safe_with_global_macro.csv` |
| `return_column` | `target_5d_return` |
| `top_n` | `10` |
| `rebalance_step` | `5` |
| `transaction_cost_per_turnover` | `0.001` |
| `num_strategies` | `31` |

## Strategy Leaderboard

| Rank | Strategy | Score | Net Excess 5D | Long/Short 5D | Spearman IC | Net Sharpe | Max Drawdown | Weak Periods |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | `inflation_x_low_volatility` | 4.296765 | 0.002948 | 0.004940 | 0.016170 | 0.899804 | -0.533180 | 5 |
| 2 | `rate_policy_x_low_volatility` | 3.609448 | 0.002652 | 0.004334 | 0.010037 | 0.826809 | -0.533180 | 5 |
| 3 | `return_1d_reversal` | 2.796274 | 0.001654 | 0.004040 | 0.023614 | 0.756264 | -0.564239 | 4 |
| 4 | `five_day_bias_x_momentum_20d` | 0.997647 | 0.001035 | 0.003588 | 0.004780 | 0.701017 | -0.513934 | 7 |
| 5 | `macro_tone_x_relative_strength` | -0.007830 | 0.000412 | 0.002393 | 0.005629 | 0.607430 | -0.513934 | 6 |
| 6 | `rate_policy_x_price_vs_ma50` | -0.195627 | 0.001040 | 0.001178 | 0.000009 | 0.695074 | -0.404226 | 7 |
| 7 | `macro_signal_x_momentum_20d` | -0.632265 | 0.000236 | 0.002073 | 0.003139 | 0.579186 | -0.513934 | 7 |
| 8 | `macro_signal_x_relative_strength` | -0.632265 | 0.000236 | 0.002073 | 0.003139 | 0.579186 | -0.513934 | 7 |
| 9 | `macro_signal_x_technical_combo` | -0.739347 | 0.000238 | 0.001757 | 0.005185 | 0.571362 | -0.457705 | 7 |
| 10 | `risk_on_x_relative_strength` | -0.899238 | 0.000106 | 0.001812 | 0.003532 | 0.567140 | -0.518328 | 7 |
| 11 | `risk_on_x_momentum_20d` | -0.899238 | 0.000106 | 0.001812 | 0.003532 | 0.567140 | -0.518328 | 7 |
| 12 | `surprise_x_low_volatility` | -1.148721 | 0.000284 | -0.000451 | 0.001039 | 0.554170 | -0.575987 | 4 |
| 13 | `macro_signal_x_price_vs_ma50` | -1.164483 | 0.000719 | 0.000560 | -0.006549 | 0.644768 | -0.404226 | 8 |
| 14 | `growth_x_relative_strength` | -1.957040 | -0.000505 | 0.000608 | 0.001998 | 0.447271 | -0.586615 | 6 |
| 15 | `volume_change_1d_only` | -2.877803 | -0.001610 | 0.001439 | 0.003987 | 0.417515 | -0.318260 | 7 |
| 16 | `price_vs_ma50_only` | -2.915123 | 0.000002 | -0.000960 | -0.010685 | 0.744134 | -0.308642 | 9 |
| 17 | `risk_off_x_low_volatility` | -3.106094 | -0.000586 | -0.002095 | 0.000620 | 0.518627 | -0.484520 | 5 |
| 18 | `liquidity_x_relative_strength` | -3.408064 | -0.001198 | -0.000870 | 0.007451 | 0.361162 | -0.625575 | 6 |
| 19 | `liquidity_x_momentum_20d` | -3.408064 | -0.001198 | -0.000870 | 0.007451 | 0.361162 | -0.625575 | 6 |
| 20 | `rsi_14d_only` | -4.146804 | -0.001220 | -0.000819 | -0.009278 | 0.633183 | -0.275977 | 9 |
| 21 | `relative_strength_only` | -4.161120 | -0.001167 | -0.000841 | -0.007959 | 0.493206 | -0.428379 | 9 |
| 22 | `momentum_20d_only` | -4.161120 | -0.001167 | -0.000841 | -0.007959 | 0.493206 | -0.428379 | 9 |
| 23 | `price_vs_ma20_only` | -5.345970 | -0.001509 | -0.002231 | -0.019117 | 0.415064 | -0.442100 | 9 |
| 24 | `open_close_spread_only` | -6.190760 | -0.002379 | -0.002506 | -0.013018 | 0.232255 | -0.509726 | 8 |
| 25 | `return_1d_momentum` | -6.820745 | -0.002403 | -0.004040 | -0.023614 | 0.215304 | -0.518431 | 7 |
| 26 | `technical_combo` | -6.906127 | -0.002369 | -0.003463 | -0.017700 | 0.261393 | -0.472838 | 9 |
| 27 | `surprise_x_relative_strength` | -6.913748 | -0.002819 | -0.004116 | -0.000852 | 0.113362 | -0.717762 | 6 |
| 28 | `low_high_low_spread` | -7.097494 | -0.002708 | -0.003343 | -0.007696 | 0.274928 | -0.284001 | 9 |
| 29 | `return_5d_momentum` | -7.319716 | -0.002344 | -0.004703 | -0.024450 | 0.227378 | -0.504724 | 8 |
| 30 | `momentum_5d_only` | -7.319716 | -0.002344 | -0.004703 | -0.024450 | 0.227378 | -0.504724 | 8 |
| 31 | `low_volatility_only` | -8.088338 | -0.002625 | -0.005995 | -0.015925 | 0.327435 | -0.245217 | 8 |

## Warnings

- Best strategy max drawdown is worse than -25%.
- Best strategy has three or more weak yearly periods.

## Next Step

Run the Model Tournament Agent again. This agent wrote `results/model_tournament_inputs.csv`, so the tournament should now include these strategy walk-forward candidates.
