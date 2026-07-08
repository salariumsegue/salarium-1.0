# Salarium Data Quality & Leakage Agent Report

**Status:** warn

**Summary:** Data quality and leakage status: warn. Universe tickers: 125. Training rows: 261993. Training tickers: 125. Suspicious leakage columns: 0. Warnings: 3. Errors: 0.

## Check Summary

| Check | Status | Detail |
|---|---|---|
| `universe_readable` | **pass** | Loaded 125 rows from configs/stock_universe_top125_yahoo.csv |
| `universe_size` | **pass** | Universe has 125 rows and 125 unique tickers. |
| `universe_duplicates` | **pass** | No duplicate tickers. |
| `universe_missing_tickers` | **pass** | No missing ticker values. |
| `universe_sector_values` | **pass** | No missing sectors. |
| `training_data_readable` | **pass** | Loaded 261993 rows from data/processed/training_data_top125_model_safe_with_macro.csv |
| `training_duplicate_date_ticker` | **pass** | No duplicate date/ticker rows. |
| `training_missing_values` | **pass** | Missing ratio 0.28%. |
| `training_infinite_values` | **pass** | No infinite numeric values. |
| `training_ticker_coverage` | **pass** | Min rows 1293, median rows 2118.0. |
| `training_date_coverage` | **pass** | Min names/date 119, median 125.0. |
| `training_expected_features` | **pass** | All expected technical features present. |
| `training_universe_alignment` | **pass** | Training tickers match universe. |
| `training_target_variance` | **pass** | Target std 0.048919. |
| `leakage_multiple_target_columns` | **pass** | Only one known target column. |
| `leakage_suspicious_column_names` | **pass** | No suspicious future/forward/target-like feature names outside known target columns. |
| `leakage_high_target_correlation` | **pass** | No numeric feature has abs corr >= 0.98 with target. |
| `leakage_zero_variance_features` | **warn** | Zero-variance columns: ['macro_tone_num'] |
| `leakage_extreme_return_like_values` | **warn** | Extreme return-like values: {'target_5d_return': 4, 'return_5d': 4, 'momentum_5d': 4, 'momentum_20d': 76} |
| `macro_features_present` | **pass** | Found macro columns: ['macro_signal_score', 'macro_tone_score', 'surprise_num', 'inflation_num', 'growth_num', 'rate_policy_num', 'liquidity_num', 'reaction_quality_num', 'five_day_market_bias_score'] |
| `macro_same_date_consistency` | **warn** | Inconsistent macro columns: [{'column': 'macro_signal_score', 'inconsistent_dates': 1488, 'inconsistent_ratio': 0.7025495750708215}, {'column': 'macro_tone_score', 'inconsistent_dates': 1570, 'inconsistent_ratio': 0.7412653446647781}, {'column': 'surprise_num', 'inconsistent_dates': 596, 'inconsistent_ratio': 0.2813975448536355}, {'column': 'inflation_num', 'inconsistent_dates': 1570, 'inconsistent_ratio': 0.7412653446647781}, {'column': 'growth_num', 'inconsistent_dates': 1446, 'inconsistent_ratio': 0.6827195467422096}, {'column': 'rate_policy_num', 'inconsistent_dates': 1518, 'inconsistent_ratio': 0.71671388101983}, {'column': 'liquidity_num', 'inconsistent_dates': 166, 'inconsistent_ratio': 0.07837582625118036}, {'column': 'reaction_quality_num', 'inconsistent_dates': 1156, 'inconsistent_ratio': 0.5457979225684608}, {'column': 'five_day_market_bias_score', 'inconsistent_dates': 1570, 'inconsistent_ratio': 0.7412653446647781}] |
| `macro_missing_values` | **pass** | Macro missing ratio 0.00%. |

## Key Metrics

| Area | Metric | Value |
|---|---|---:|
| Universe | Unique tickers | 125 |
| Universe | Duplicate tickers | 0 |
| Training | Rows | 261993 |
| Training | Unique tickers | 125 |
| Training | Unique dates | 2118 |
| Training | Start date | 2018-01-09 |
| Training | End date | 2026-06-12 |
| Training | Missing value ratio | 0.002772 |
| Training | Duplicate date/ticker rows | 0 |
| Leakage | Suspicious target-like feature columns | 0 |
| Leakage | High target-correlation columns | 0 |
| Macro | Present macro columns | 9 |
| Macro | Macro missing ratio | 0.0 |

## Warnings

- Zero-variance numeric feature columns found: ['macro_tone_num']
- Extreme return-like values detected: {'target_5d_return': 4, 'return_5d': 4, 'momentum_5d': 4, 'momentum_20d': 76}
- Some macro columns vary across tickers on the same date. Check merge logic: [{'column': 'macro_signal_score', 'inconsistent_dates': 1488, 'inconsistent_ratio': 0.7025495750708215}, {'column': 'macro_tone_score', 'inconsistent_dates': 1570, 'inconsistent_ratio': 0.7412653446647781}, {'column': 'surprise_num', 'inconsistent_dates': 596, 'inconsistent_ratio': 0.2813975448536355}, {'column': 'inflation_num', 'inconsistent_dates': 1570, 'inconsistent_ratio': 0.7412653446647781}, {'column': 'growth_num', 'inconsistent_dates': 1446, 'inconsistent_ratio': 0.6827195467422096}, {'column': 'rate_policy_num', 'inconsistent_dates': 1518, 'inconsistent_ratio': 0.71671388101983}, {'column': 'liquidity_num', 'inconsistent_dates': 166, 'inconsistent_ratio': 0.07837582625118036}, {'column': 'reaction_quality_num', 'inconsistent_dates': 1156, 'inconsistent_ratio': 0.5457979225684608}, {'column': 'five_day_market_bias_score', 'inconsistent_dates': 1570, 'inconsistent_ratio': 0.7412653446647781}]

## Next Step

If this report is `pass` or `warn`, continue to Agent 5: Risk & Portfolio Agent. If this report is `fail`, fix the data issue before running more tournaments.
