# Salarium Macro Merge Semantics Audit

## Summary

This audit checks whether macro features behave as global-by-date features or ticker-adjusted features.

| File | Exists | Rows | Ticker Col | Macro Cols | Inconsistent Cols | Max Inconsistent Ratio | Recommendation |
|---|---:|---:|---|---:|---:|---:|---|
| `data/processed/training_data_top125_model_safe_with_macro.csv` | True | 261993 | `ticker` | 13 | 12 | 74.13% | `ticker_adjusted_or_bad_merge` |
| `data/processed/training_data_model_safe_with_macro.csv` | True | 289527 | `ticker` | 13 | 12 | 74.13% | `ticker_adjusted_or_bad_merge` |
| `data/processed/salarium_training_with_macro.csv` | True | 31980 | `ticker` | 12 | 0 | 0.00% | `global_by_date` |
| `data/processed/macro_model_features.csv` | True | 25 | `` | 12 | 0 | 0.00% | `global_by_date` |
| `data/processed/macro_llm_features.csv` | True | 25 | `` | 2 | 0 | 0.00% | `global_by_date` |

## Detail

### `data/processed/training_data_top125_model_safe_with_macro.csv`

- Exists: `True`
- Rows: `261993`
- Date column: `date`
- Ticker column: `ticker`
- Macro columns: `['macro_tone_num', 'surprise_num', 'inflation_num', 'growth_num', 'rate_policy_num', 'liquidity_num', 'reaction_quality_num', 'five_day_bias_num', 'macro_tone_score', 'five_day_market_bias_score', 'macro_confidence', 'macro_signal_score', 'has_macro_context']`
- Expected macro columns present: `['macro_signal_score', 'macro_tone_score', 'surprise_num', 'inflation_num', 'growth_num', 'rate_policy_num', 'liquidity_num', 'reaction_quality_num', 'five_day_market_bias_score']`
- Recommendation: `ticker_adjusted_or_bad_merge`
- Notes: macro columns vary across tickers on same date

| Column | Inconsistent Dates | Inconsistent Ratio |
|---|---:|---:|
| `surprise_num` | 596 | 28.14% |
| `inflation_num` | 1570 | 74.13% |
| `growth_num` | 1446 | 68.27% |
| `rate_policy_num` | 1518 | 71.67% |
| `liquidity_num` | 166 | 7.84% |
| `reaction_quality_num` | 1156 | 54.58% |
| `five_day_bias_num` | 335 | 15.82% |
| `macro_tone_score` | 1570 | 74.13% |
| `five_day_market_bias_score` | 1570 | 74.13% |
| `macro_confidence` | 1570 | 74.13% |
| `macro_signal_score` | 1488 | 70.25% |
| `has_macro_context` | 1570 | 74.13% |

### `data/processed/training_data_model_safe_with_macro.csv`

- Exists: `True`
- Rows: `289527`
- Date column: `date`
- Ticker column: `ticker`
- Macro columns: `['macro_tone_num', 'surprise_num', 'inflation_num', 'growth_num', 'rate_policy_num', 'liquidity_num', 'reaction_quality_num', 'five_day_bias_num', 'macro_tone_score', 'five_day_market_bias_score', 'macro_confidence', 'macro_signal_score', 'has_macro_context']`
- Expected macro columns present: `['macro_signal_score', 'macro_tone_score', 'surprise_num', 'inflation_num', 'growth_num', 'rate_policy_num', 'liquidity_num', 'reaction_quality_num', 'five_day_market_bias_score']`
- Recommendation: `ticker_adjusted_or_bad_merge`
- Notes: macro columns vary across tickers on same date

| Column | Inconsistent Dates | Inconsistent Ratio |
|---|---:|---:|
| `surprise_num` | 596 | 28.14% |
| `inflation_num` | 1570 | 74.13% |
| `growth_num` | 1446 | 68.27% |
| `rate_policy_num` | 1518 | 71.67% |
| `liquidity_num` | 166 | 7.84% |
| `reaction_quality_num` | 1156 | 54.58% |
| `five_day_bias_num` | 335 | 15.82% |
| `macro_tone_score` | 1570 | 74.13% |
| `five_day_market_bias_score` | 1570 | 74.13% |
| `macro_confidence` | 1570 | 74.13% |
| `macro_signal_score` | 1488 | 70.25% |
| `has_macro_context` | 1570 | 74.13% |

### `data/processed/salarium_training_with_macro.csv`

- Exists: `True`
- Rows: `31980`
- Date column: `date`
- Ticker column: `ticker`
- Macro columns: `['macro_tone_num', 'surprise_num', 'inflation_num', 'growth_num', 'rate_policy_num', 'liquidity_num', 'reaction_quality_num', 'five_day_bias_num', 'macro_tone_score', 'five_day_market_bias_score', 'macro_confidence', 'macro_signal_score']`
- Expected macro columns present: `['macro_signal_score', 'macro_tone_score', 'surprise_num', 'inflation_num', 'growth_num', 'rate_policy_num', 'liquidity_num', 'reaction_quality_num', 'five_day_market_bias_score']`
- Recommendation: `global_by_date`
- Notes: macro columns mostly consistent by date

### `data/processed/macro_model_features.csv`

- Exists: `True`
- Rows: `25`
- Date column: `date`
- Ticker column: `None`
- Macro columns: `['macro_tone_num', 'surprise_num', 'inflation_num', 'growth_num', 'rate_policy_num', 'liquidity_num', 'reaction_quality_num', 'five_day_bias_num', 'macro_tone_score', 'five_day_market_bias_score', 'macro_confidence', 'macro_signal_score']`
- Expected macro columns present: `['macro_signal_score', 'macro_tone_score', 'surprise_num', 'inflation_num', 'growth_num', 'rate_policy_num', 'liquidity_num', 'reaction_quality_num', 'five_day_market_bias_score']`
- Recommendation: `global_by_date`
- Notes: macro columns mostly consistent by date

### `data/processed/macro_llm_features.csv`

- Exists: `True`
- Rows: `25`
- Date column: `date`
- Ticker column: `None`
- Macro columns: `['macro_tone_score', 'five_day_market_bias_score']`
- Expected macro columns present: `['macro_tone_score', 'five_day_market_bias_score']`
- Recommendation: `global_by_date`
- Notes: macro columns mostly consistent by date

## Decision

For Phase 2.2, Salarium will create a global-by-date macro dataset. Ticker-adjusted macro exposure features can be added later under explicit names.
