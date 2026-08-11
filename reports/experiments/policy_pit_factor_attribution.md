# Salarium Point-in-Time Portfolio Factor Attribution

## Methodology

Portfolio exposures use only SEC fundamental values that were publicly available by the historical rebalance date.

The invested-sleeve exposure measures the weighted factor z-score among covered holdings.

The cash-scaled exposure multiplies that exposure by actual portfolio exposure, assigning cash zero factor exposure.

## Mean Exposure Summary

| policy | factor | mean_invested_sleeve_exposure | mean_cash_scaled_exposure | share_positive | mean_factor_coverage | minimum_factor_coverage |
| --- | --- | --- | --- | --- | --- | --- |
| baseline_equal_weight | book_to_market | 0.2206 | 0.2206 | 0.4855 | 0.5587 | 0.1000 |
| baseline_equal_weight | earnings_yield | -1.1294 | -1.1294 | 0.0255 | 0.6109 | 0.0000 |
| baseline_equal_weight | gross_profitability | -0.5195 | -0.5195 | 0.1673 | 0.5467 | 0.0000 |
| baseline_equal_weight | leverage | -0.5149 | -0.5149 | 0.1341 | 0.8304 | 0.5000 |
| baseline_equal_weight | operating_profitability | -1.2961 | -1.2961 | 0.0072 | 0.8134 | 0.4000 |
| baseline_equal_weight | quality | -1.2069 | -1.2069 | 0.0036 | 0.8543 | 0.4000 |
| baseline_equal_weight | roa | -1.2414 | -1.2414 | 0.0109 | 0.8518 | 0.4000 |
| baseline_equal_weight | roe | -0.8013 | -0.8013 | 0.0036 | 0.7601 | 0.3000 |
| baseline_equal_weight | size | -1.8304 | -1.8304 | 0.0036 | 0.6638 | 0.1000 |
| baseline_equal_weight | value | -0.6539 | -0.6539 | 0.0797 | 0.6225 | 0.1000 |
| turnover_buffer_inverse_volatility_risk_scaled | book_to_market | 0.2165 | 0.1081 | 0.4964 | 0.5646 | 0.0958 |
| turnover_buffer_inverse_volatility_risk_scaled | earnings_yield | -1.0910 | -0.5667 | 0.0327 | 0.6127 | 0.0000 |
| turnover_buffer_inverse_volatility_risk_scaled | gross_profitability | -0.5236 | -0.2791 | 0.1673 | 0.5554 | 0.0000 |
| turnover_buffer_inverse_volatility_risk_scaled | leverage | -0.5290 | -0.2797 | 0.1268 | 0.8326 | 0.4131 |
| turnover_buffer_inverse_volatility_risk_scaled | operating_profitability | -1.2613 | -0.6666 | 0.0036 | 0.8204 | 0.3643 |
| turnover_buffer_inverse_volatility_risk_scaled | quality | -1.1811 | -0.6270 | 0.0036 | 0.8612 | 0.3643 |
| turnover_buffer_inverse_volatility_risk_scaled | roa | -1.2153 | -0.6410 | 0.0109 | 0.8582 | 0.3643 |
| turnover_buffer_inverse_volatility_risk_scaled | roe | -0.7949 | -0.4245 | 0.0072 | 0.7683 | 0.3520 |
| turnover_buffer_inverse_volatility_risk_scaled | size | -1.7698 | -0.9390 | 0.0000 | 0.6650 | 0.1823 |
| turnover_buffer_inverse_volatility_risk_scaled | value | -0.6272 | -0.3300 | 0.0797 | 0.6254 | 0.0968 |

## Latest Rebalance

| policy | factor | invested_sleeve_exposure | cash_scaled_exposure | covered_normalized_weight |
| --- | --- | --- | --- | --- |
| baseline_equal_weight | book_to_market | -0.6495 | -0.6495 | 0.5000 |
| baseline_equal_weight | earnings_yield | -0.1392 | -0.1392 | 0.7000 |
| baseline_equal_weight | gross_profitability | 0.1002 | 0.1002 | 0.7000 |
| baseline_equal_weight | leverage | -0.1611 | -0.1611 | 0.9000 |
| baseline_equal_weight | operating_profitability | -0.8032 | -0.8032 | 1.0000 |
| baseline_equal_weight | quality | -0.7668 | -0.7668 | 1.0000 |
| baseline_equal_weight | roa | -0.7105 | -0.7105 | 1.0000 |
| baseline_equal_weight | roe | -0.4941 | -0.4941 | 0.8000 |
| baseline_equal_weight | size | -0.2229 | -0.2229 | 0.7000 |
| baseline_equal_weight | value | -0.3058 | -0.3058 | 0.7000 |
| turnover_buffer_inverse_volatility_risk_scaled | book_to_market | -0.6195 | -0.2788 | 0.4540 |
| turnover_buffer_inverse_volatility_risk_scaled | earnings_yield | -0.0717 | -0.0323 | 0.6957 |
| turnover_buffer_inverse_volatility_risk_scaled | gross_profitability | 0.6797 | 0.3059 | 0.6524 |
| turnover_buffer_inverse_volatility_risk_scaled | leverage | 0.1722 | 0.0775 | 0.8837 |
| turnover_buffer_inverse_volatility_risk_scaled | operating_profitability | -0.7662 | -0.3448 | 1.0000 |
| turnover_buffer_inverse_volatility_risk_scaled | quality | -0.6956 | -0.3130 | 1.0000 |
| turnover_buffer_inverse_volatility_risk_scaled | roa | -0.7223 | -0.3250 | 1.0000 |
| turnover_buffer_inverse_volatility_risk_scaled | roe | -0.5107 | -0.2298 | 0.7584 |
| turnover_buffer_inverse_volatility_risk_scaled | size | -0.2866 | -0.1290 | 0.6957 |
| turnover_buffer_inverse_volatility_risk_scaled | value | -0.2302 | -0.1036 | 0.6957 |

## Interpretation Rules

- Positive `size` means a tilt toward larger companies.
- Positive `value` means a tilt toward cheaper companies on the point-in-time value composite.
- Positive `quality` means a tilt toward stronger profitability.
- Positive `leverage` means a tilt toward more leveraged companies.

These are exposure diagnostics, not proof that the corresponding factor caused portfolio returns.
