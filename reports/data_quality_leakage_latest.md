# Salarium Data Quality & Leakage Agent Report

**Status:** warn

**Summary:** Data quality and leakage status: warn. Universe tickers: 138. Training rows: 289527. Training tickers: 138. Suspicious leakage columns: 0. Warnings: 3. Errors: 0.

## Check Summary

| Check | Status | Detail |
|---|---|---|
| `universe_readable` | **pass** | Loaded 138 rows from configs/stock_universe_current_training.csv |
| `universe_size` | **warn** | Rows=138, unique_tickers=138, expected=125. |
| `universe_duplicates` | **pass** | No duplicate tickers. |
| `universe_missing_tickers` | **pass** | No missing ticker values. |
| `universe_sector_values` | **pass** | No missing sectors. |
| `training_data_readable` | **pass** | Loaded 289527 rows from data/processed/training_data_model_safe.csv |
| `training_duplicate_date_ticker` | **pass** | No duplicate date/ticker rows. |
| `training_missing_values` | **pass** | Missing ratio 0.43%. |
| `training_infinite_values` | **pass** | No infinite numeric values. |
| `training_ticker_coverage` | **pass** | Min rows 1293, median rows 2118.0. |
| `training_date_coverage` | **pass** | Min names/date 132, median 138.0. |
| `training_expected_features` | **pass** | All expected technical features present. |
| `training_universe_alignment` | **pass** | Training tickers match universe. |
| `training_target_variance` | **pass** | Target std 0.050034. |
| `leakage_multiple_target_columns` | **pass** | Only one known target column. |
| `leakage_suspicious_column_names` | **pass** | No suspicious future/forward/target-like feature names outside known target columns. |
| `leakage_high_target_correlation` | **pass** | No numeric feature has abs corr >= 0.98 with target. |
| `leakage_zero_variance_features` | **pass** | No zero-variance numeric features. |
| `leakage_extreme_return_like_values` | **warn** | Extreme return-like values: {'target_5d_return': 4, 'return_5d': 4, 'momentum_5d': 4, 'momentum_20d': 83} |
| `macro_features_present` | **warn** | No macro columns found. |

## Key Metrics

| Area | Metric | Value |
|---|---|---:|
| Universe | Unique tickers | 138 |
| Universe | Duplicate tickers | 0 |
| Training | Rows | 289527 |
| Training | Unique tickers | 138 |
| Training | Unique dates | 2118 |
| Training | Start date | 2018-01-09 |
| Training | End date | 2026-06-12 |
| Training | Missing value ratio | 0.004335 |
| Training | Duplicate date/ticker rows | 0 |
| Leakage | Suspicious target-like feature columns | 0 |
| Leakage | High target-correlation columns | 0 |
| Macro | Present macro columns | 0 |
| Macro | Macro missing ratio |  |

## Warnings

- Universe has 138 rows and 138 unique tickers; expected 125.
- Extreme return-like values detected: {'target_5d_return': 4, 'return_5d': 4, 'momentum_5d': 4, 'momentum_20d': 83}
- No macro feature columns found in training data.

## Next Step

If this report is `pass` or `warn`, continue to Agent 5: Risk & Portfolio Agent. If this report is `fail`, fix the data issue before running more tournaments.
