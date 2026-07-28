# Turnover Buffer Portfolio Verdict

## Decision

Promote the turnover-buffer portfolio construction as Salarium's preferred portfolio candidate.

## Overall Results

| Metric | Baseline Equal Weight | Turnover Buffer |
|---|---:|---:|
| Average net excess 5D | 0.007242 | 0.008633 |
| Average long-short 5D | 0.003049 | 0.004263 |
| Average turnover | 1.071014 | 0.892754 |
| Average transaction cost | 0.001071 | 0.000893 |
| Annualized net return | 0.477537 | 0.588288 |
| Net Sharpe | 0.912477 | 1.021261 |
| Excess Sharpe | 0.653082 | 0.787046 |
| Maximum drawdown | -0.821457 | -0.773453 |

## Interpretation

The turnover buffer reduced unnecessary portfolio replacement while preserving stronger-ranked existing holdings. It lowered turnover and transaction costs while improving net excess return, long-short performance, Sharpe ratios, annualized return, and overall maximum drawdown.

The improvement was not uniform in every year. The buffered portfolio lagged the baseline in some individual periods and still experienced severe drawdowns, especially in 2022 and 2023.

## Conclusion

The turnover buffer is promoted as the preferred portfolio construction candidate, but additional risk controls are still required before making any deployability or profitability claim.

## Next Research Step

Test volatility-aware weighting and explicit risk-exposure controls on top of the turnover-buffer selection rule.
