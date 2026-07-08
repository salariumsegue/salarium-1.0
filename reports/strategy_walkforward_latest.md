# Salarium Strategy Walkforward Agent Report

**Status:** warn

**Summary:** Strategy walk-forward status: warn. Strategies evaluated: 8. Best strategy: price_vs_ma50_only (score -3.3951, net excess 5D -0.000168, IC -0.009880). Warnings: 5. Errors: 0.

## Run Settings

| Setting | Value |
|---|---|
| `training_data_path` | `data/processed/training_data_model_safe.csv` |
| `return_column` | `target_5d_return` |
| `top_n` | `10` |
| `rebalance_step` | `5` |
| `transaction_cost_per_turnover` | `0.001` |
| `num_strategies` | `8` |

## Strategy Leaderboard

| Rank | Strategy | Score | Net Excess 5D | Long/Short 5D | Spearman IC | Net Sharpe | Max Drawdown | Weak Periods |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | `price_vs_ma50_only` | -3.395086 | -0.000168 | -0.001492 | -0.009880 | 0.649525 | -0.372561 | 9 |
| 2 | `momentum_20d_only` | -4.021071 | -0.000974 | -0.000983 | -0.007130 | 0.468772 | -0.440529 | 9 |
| 3 | `relative_strength_only` | -4.021071 | -0.000974 | -0.000983 | -0.007130 | 0.468772 | -0.440529 | 9 |
| 4 | `rsi_14d_only` | -4.190662 | -0.001260 | -0.000824 | -0.009183 | 0.568945 | -0.277123 | 9 |
| 5 | `technical_combo` | -5.252529 | -0.001664 | -0.001815 | -0.014146 | 0.372451 | -0.435930 | 9 |
| 6 | `price_vs_ma20_only` | -5.711397 | -0.001708 | -0.002524 | -0.018492 | 0.331772 | -0.463591 | 9 |
| 7 | `momentum_5d_only` | -7.291140 | -0.002434 | -0.004456 | -0.025632 | 0.175979 | -0.486572 | 8 |
| 8 | `low_volatility_only` | -8.523250 | -0.002703 | -0.006728 | -0.014228 | 0.248121 | -0.243737 | 8 |

## Warnings

- No macro score columns found. Macro baseline strategies will be skipped.
- Best strategy has negative Spearman IC.
- Best strategy max drawdown is worse than -25%.
- Best strategy has three or more weak yearly periods.
- No macro strategy candidates were generated.

## Next Step

Run the Model Tournament Agent again. This agent wrote `results/model_tournament_inputs.csv`, so the tournament should now include these strategy walk-forward candidates.
