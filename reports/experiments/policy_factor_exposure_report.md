# Salarium Factor Exposure Analysis

These exposures are Salarium technical factor proxies, not canonical academic factor-return regressions.

## Factor Exposure Summary

| policy | factor | mean_exposure | median_exposure | p10_exposure | p90_exposure | mean_absolute_exposure | maximum_absolute_exposure | average_covered_weight |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_equal_weight | low_volatility_z | -2.372246 | -2.444645 | -2.836672 | -1.724638 | 2.372246 | 3.000000 | 1.000000 |
| baseline_equal_weight | market_beta_60d | 2.307532 | 2.264249 | 1.588246 | 3.096529 | 2.307532 | 3.962209 | 0.986594 |
| baseline_equal_weight | momentum_20d_z | -0.105446 | 0.069644 | -1.956873 | 1.441602 | 1.038288 | 2.866469 | 1.000000 |
| baseline_equal_weight | relative_strength_z | -0.105446 | 0.069644 | -1.956873 | 1.441602 | 1.038288 | 2.866469 | 1.000000 |
| baseline_equal_weight | short_term_reversal_z | 0.672824 | 0.666657 | -0.219029 | 1.657107 | 0.799165 | 2.815644 | 1.000000 |
| turnover_buffer_inverse_volatility_risk_scaled | low_volatility_z | -1.198782 | -1.102186 | -2.007839 | -0.740431 | 1.198782 | 2.981463 | 0.532790 |
| turnover_buffer_inverse_volatility_risk_scaled | market_beta_60d | 1.231521 | 1.036400 | 0.729825 | 2.118152 | 1.231521 | 3.637190 | 0.525458 |
| turnover_buffer_inverse_volatility_risk_scaled | momentum_20d_z | -0.054644 | -0.010458 | -0.866239 | 0.661321 | 0.513706 | 2.402355 | 0.532790 |
| turnover_buffer_inverse_volatility_risk_scaled | relative_strength_z | -0.054644 | -0.010458 | -0.866239 | 0.661321 | 0.513706 | 2.402355 | 0.532790 |
| turnover_buffer_inverse_volatility_risk_scaled | short_term_reversal_z | 0.331401 | 0.294740 | -0.124770 | 0.795322 | 0.390262 | 2.147045 | 0.532790 |

## Weight-Level Concentration

| policy | avg_maximum_weight | worst_maximum_weight | avg_hhi | avg_effective_names | min_effective_names |
| --- | --- | --- | --- | --- | --- |
| baseline_equal_weight | 0.100000 | 0.100000 | 0.100000 | 10.000000 | 10.000000 |
| turnover_buffer_inverse_volatility_risk_scaled | 0.136549 | 0.180000 | 0.105778 | 9.464122 | 7.705311 |

## Coverage

- `weight_level_asset_concentration`: `available_reconstructed_from_policy_holdings`
- `market_beta`: `available_60d_rolling_proxy`
- `momentum`: `available_20d_cross_sectional_proxy`
- `relative_strength`: `available_cross_sectional_proxy`
- `low_volatility`: `available_cross_sectional_proxy`
- `short_term_reversal`: `available_5d_cross_sectional_proxy`
- `size_factor`: `unavailable_no_point_in_time_market_cap`
- `value_factor`: `unavailable_no_point_in_time_fundamentals`
- `quality_factor`: `unavailable_no_point_in_time_fundamentals`
- `sector_exposure`: `unavailable_no_sector_metadata`
- `industry_exposure`: `unavailable_no_industry_metadata`

## Methodology

- Alpha benchmark positions are equal weighted.
- Risk-managed positions reconstruct inverse-volatility weights with an 18% single-name cap and apply the persisted portfolio exposure scalar.
- Sector analysis is emitted only when sector metadata exists.
