# Salarium Security Metadata Audit

## Governance Rule

Current or merely dated security metadata must not be inserted into historical backtests unless its point-in-time provenance has been explicitly verified.

## Scan Summary

- CSV files scanned: 156
- Files containing candidate metadata: 6
- Candidate metadata fields detected: industry, market_cap, sector
- Point-in-time verified fields: none

## Files Containing Candidate Metadata

| path | size_mb | has_ticker | has_date | metadata_field_count | temporal_classification |
| --- | --- | --- | --- | --- | --- |
| configs/universe_snapshots/2026-07-08_market_cap_fetch_all.csv | 0.013 | True | False | 3 | current_or_dated_snapshot |
| configs/universe_snapshots/2026-07-08_market_cap_missing.csv | 0.000 | True | False | 3 | current_or_dated_snapshot |
| configs/universe_snapshots/2026-07-08_top125_yahoo.csv | 0.014 | True | False | 3 | current_or_dated_snapshot |
| configs/universe_snapshots/2026-07-12_liquid_125_validation.csv | 0.026 | True | False | 3 | current_or_dated_snapshot |
| data/processed/demo_stock_training_data.csv | 0.005 | True | True | 1 | historical_panel_unverified |
| data/processed/salarium_training_with_macro.csv | 10.894 | True | True | 1 | historical_panel_unverified |

## Detected Metadata Fields

| path | canonical_field | source_column | temporal_classification | point_in_time_verified | historical_backtest_eligible | eligibility_reason |
| --- | --- | --- | --- | --- | --- | --- |
| configs/universe_snapshots/2026-07-08_market_cap_fetch_all.csv | sector | sector | current_or_dated_snapshot | False | False | point_in_time_provenance_not_verified |
| configs/universe_snapshots/2026-07-08_market_cap_fetch_all.csv | industry | industry | current_or_dated_snapshot | False | False | point_in_time_provenance_not_verified |
| configs/universe_snapshots/2026-07-08_market_cap_fetch_all.csv | market_cap | market_cap | current_or_dated_snapshot | False | False | point_in_time_provenance_not_verified |
| configs/universe_snapshots/2026-07-08_market_cap_missing.csv | sector | sector | current_or_dated_snapshot | False | False | point_in_time_provenance_not_verified |
| configs/universe_snapshots/2026-07-08_market_cap_missing.csv | industry | industry | current_or_dated_snapshot | False | False | point_in_time_provenance_not_verified |
| configs/universe_snapshots/2026-07-08_market_cap_missing.csv | market_cap | market_cap | current_or_dated_snapshot | False | False | point_in_time_provenance_not_verified |
| configs/universe_snapshots/2026-07-08_top125_yahoo.csv | sector | sector | current_or_dated_snapshot | False | False | point_in_time_provenance_not_verified |
| configs/universe_snapshots/2026-07-08_top125_yahoo.csv | industry | industry | current_or_dated_snapshot | False | False | point_in_time_provenance_not_verified |
| configs/universe_snapshots/2026-07-08_top125_yahoo.csv | market_cap | market_cap | current_or_dated_snapshot | False | False | point_in_time_provenance_not_verified |
| configs/universe_snapshots/2026-07-12_liquid_125_validation.csv | sector | sector | current_or_dated_snapshot | False | False | point_in_time_provenance_not_verified |
| configs/universe_snapshots/2026-07-12_liquid_125_validation.csv | industry | industry | current_or_dated_snapshot | False | False | point_in_time_provenance_not_verified |
| configs/universe_snapshots/2026-07-12_liquid_125_validation.csv | market_cap | market_cap | current_or_dated_snapshot | False | False | point_in_time_provenance_not_verified |
| data/processed/demo_stock_training_data.csv | sector | sector | historical_panel_unverified | False | False | point_in_time_provenance_not_verified |
| data/processed/salarium_training_with_macro.csv | sector | sector | historical_panel_unverified | False | False | point_in_time_provenance_not_verified |

## Historical Research Gap Analysis

| field | available_anywhere | point_in_time_verified | historical_backtest_status | next_action |
| --- | --- | --- | --- | --- |
| sector | True | False | blocked | verify_source_provenance |
| industry | True | False | blocked | verify_source_provenance |
| market_cap | True | False | blocked | verify_source_provenance |
| shares_outstanding | False | False | blocked | source_data |
| book_value | False | False | blocked | source_data |
| book_to_market | False | False | blocked | source_data |
| price_to_book | False | False | blocked | source_data |
| price_to_earnings | False | False | blocked | source_data |
| revenue | False | False | blocked | source_data |
| operating_income | False | False | blocked | source_data |
| net_income | False | False | blocked | source_data |
| return_on_equity | False | False | blocked | source_data |
| return_on_assets | False | False | blocked | source_data |
| gross_margin | False | False | blocked | source_data |
| debt_to_equity | False | False | blocked | source_data |

## Interpretation

- `current_or_dated_snapshot` means the file can describe the universe at its snapshot date, but does not establish a historical point-in-time series.
- `historical_panel_unverified` means a ticker/date panel exists, but provenance still must be verified before using it for historical factor or sector attribution.
- `historical_backtest_status = blocked` is intentional. Salarium prefers missing data over look-ahead contamination.
