# Salarium Factor-Adjusted Policy Return Analysis

## Question

How much of Salarium's net excess return remains after controlling for point-in-time size, value, quality, and leverage factor returns?

## Regression Summary

| policy | observations | hac_lag | unadjusted_mean_net_excess_5d | factor_adjusted_alpha_5d | factor_adjusted_alpha_annualized_arithmetic | alpha_hac_standard_error | alpha_hac_t_stat | r_squared | share_mean_excess_remaining_after_factor_adjustment |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_equal_weight | 276 | 3 | 0.00667 | -0.00274 | -0.13816 | 0.00272 | -1.00819 | 0.55586 | -0.41124 |
| turnover_buffer_inverse_volatility_risk_scaled | 276 | 3 | 0.00344 | -0.00167 | -0.08425 | 0.00170 | -0.98300 | 0.46574 | -0.48599 |

## Factor Coefficients

| policy | coefficient | estimate | hac_standard_error | hac_t_stat |
| --- | --- | --- | --- | --- |
| baseline_equal_weight | intercept | -0.00274 | 0.00272 | -1.00819 |
| baseline_equal_weight | size | -0.33358 | 0.22004 | -1.51597 |
| baseline_equal_weight | value | -0.10690 | 0.18612 | -0.57435 |
| baseline_equal_weight | quality | -1.01349 | 0.19284 | -5.25552 |
| baseline_equal_weight | leverage | -0.42501 | 0.20058 | -2.11889 |
| turnover_buffer_inverse_volatility_risk_scaled | intercept | -0.00167 | 0.00170 | -0.98300 |
| turnover_buffer_inverse_volatility_risk_scaled | size | -0.22930 | 0.11954 | -1.91824 |
| turnover_buffer_inverse_volatility_risk_scaled | value | -0.01271 | 0.09614 | -0.13218 |
| turnover_buffer_inverse_volatility_risk_scaled | quality | -0.50304 | 0.11440 | -4.39740 |
| turnover_buffer_inverse_volatility_risk_scaled | leverage | -0.19704 | 0.11829 | -1.66573 |

## Factor-Mimicking Returns

| factor | observations | mean_5d_return | annualized_arithmetic_return | annualized_sharpe | median_names_available | minimum_names_available |
| --- | --- | --- | --- | --- | --- | --- |
| leverage | 276 | -0.00082 | -0.04110 | -0.22411 | 348.00000 | 299 |
| quality | 276 | -0.00600 | -0.30256 | -1.31597 | 427.00000 | 380 |
| size | 276 | -0.00832 | -0.41912 | -1.79577 | 415.00000 | 390 |
| value | 276 | -0.00189 | -0.09545 | -0.48897 | 392.00000 | 364 |

## Selection Versus Cash-Scaling Decomposition

| policy | factor | mean_invested_sleeve_exposure | mean_cash_scaled_exposure | cash_scaling_attenuation | mean_factor_coverage |
| --- | --- | --- | --- | --- | --- |
| baseline_equal_weight | leverage | -0.51487 | -0.51487 | 1.00000 | 0.83043 |
| baseline_equal_weight | quality | -1.20694 | -1.20694 | 1.00000 | 0.85435 |
| baseline_equal_weight | size | -1.83037 | -1.83037 | 1.00000 | 0.66377 |
| baseline_equal_weight | value | -0.65388 | -0.65388 | 1.00000 | 0.62246 |
| turnover_buffer_inverse_volatility_risk_scaled | leverage | -0.52904 | -0.27971 | 0.52870 | 0.83264 |
| turnover_buffer_inverse_volatility_risk_scaled | quality | -1.18108 | -0.62704 | 0.53090 | 0.86119 |
| turnover_buffer_inverse_volatility_risk_scaled | size | -1.76983 | -0.93903 | 0.53058 | 0.66502 |
| turnover_buffer_inverse_volatility_risk_scaled | value | -0.62718 | -0.33001 | 0.52618 | 0.62537 |

## Interpretation

A positive regression intercept means average net excess return remains after the included factor controls.
Statistical evidence should be judged from the HAC alpha t-stat, not the intercept alone.
A low R-squared means these fundamental factors explain only a small portion of period-to-period policy return variation.
Cash-scaled exposure differences must not be mistaken for differences in stock-selection style.

## Limitation

The current 500-name historical universe is survivorship biased. This analysis improves factor attribution but does not remove that universe-level limitation.
