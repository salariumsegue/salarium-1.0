# Salarium Policy Robustness Report

## Distribution, Tail Risk, and Drawdown

| policy | median_net_5d_return | worst_decile_mean_net_return | expected_shortfall_95_return | worst_monthly_return | longest_underwater_calendar_days | max_drawdown | net_sharpe | excess_sharpe | avg_turnover |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_equal_weight | 0.007655 | -0.138188 | -0.167664 | -0.258860 | 1094 | -0.768306 | 0.944517 | 0.672974 | 1.297826 |
| turnover_buffer_inverse_volatility_risk_scaled | 0.004277 | -0.081452 | -0.101693 | -0.199294 | 1367 | -0.578632 | 0.915077 | 0.619567 | 0.646603 |

## Paired Block-Bootstrap Comparison

| comparison | metric | observed_difference | ci_95_lower | ci_95_upper | probability_difference_positive | two_sided_bootstrap_p_value | statistically_significant_5pct | iterations | block_length_rebalances |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| risk_managed_minus_alpha_benchmark | mean_net_return | -0.005241 | -0.011072 | 0.000673 | 0.042600 | 0.085200 | False | 5000 | 6 |
| risk_managed_minus_alpha_benchmark | mean_excess_return | -0.003226 | -0.008026 | 0.001510 | 0.095000 | 0.190000 | False | 5000 | 6 |
| risk_managed_minus_alpha_benchmark | net_sharpe | -0.029440 | -0.405567 | 0.314400 | 0.440800 | 0.881600 | False | 5000 | 6 |
| risk_managed_minus_alpha_benchmark | excess_sharpe | -0.053407 | -0.457990 | 0.326963 | 0.404000 | 0.808000 | False | 5000 | 6 |
| risk_managed_minus_alpha_benchmark | max_drawdown | 0.189674 | 0.041224 | 0.356287 | 0.992200 | 0.015600 | True | 5000 | 6 |

## Cost Stress

| policy | scenario | total_trading_cost_bps | annualized_net_return | net_sharpe | excess_sharpe | max_drawdown |
| --- | --- | --- | --- | --- | --- | --- |
| baseline_equal_weight | current_assumption | 10.000000 | 0.486884 | 0.944517 | 0.672974 | -0.768306 |
| baseline_equal_weight | institutional_low | 5.000000 | 0.536107 | 0.996984 | 0.738511 | -0.759656 |
| baseline_equal_weight | realistic_base | 12.000000 | 0.467630 | 0.923530 | 0.646760 | -0.771680 |
| baseline_equal_weight | conservative | 30.000000 | 0.304971 | 0.734645 | 0.410846 | -0.801092 |
| baseline_equal_weight | stress | 60.000000 | 0.072237 | 0.419892 | 0.017830 | -0.860888 |
| turnover_buffer_inverse_volatility_risk_scaled | current_assumption | 10.000000 | 0.299846 | 0.915077 | 0.619567 | -0.578632 |
| turnover_buffer_inverse_volatility_risk_scaled | institutional_low | 5.000000 | 0.339338 | 0.999489 | 0.726795 | -0.554898 |
| turnover_buffer_inverse_volatility_risk_scaled | realistic_base | 12.000000 | 0.309393 | 0.936160 | 0.646021 | -0.570961 |
| turnover_buffer_inverse_volatility_risk_scaled | conservative | 30.000000 | 0.229746 | 0.759731 | 0.421052 | -0.613349 |
| turnover_buffer_inverse_volatility_risk_scaled | stress | 60.000000 | 0.105565 | 0.459033 | 0.037500 | -0.676097 |

## Exposure Coverage

- Asset concentration: available by holding frequency.
- Market risk-state exposure: available.
- Sector exposure: unavailable because the canonical universe has no sector metadata.
- Factor exposure: unavailable because no point-in-time factor dataset is present.
- Cost estimates are scenarios, not observed fills.
