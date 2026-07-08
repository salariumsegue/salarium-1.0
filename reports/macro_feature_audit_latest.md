# Salarium Macro Feature Audit Agent Report

**Status:** warn

**Summary:** Macro feature audit status: warn. Macro holdout excess Top-5 delta: 0.000310. Relative excess lift: 35.63%. AUC delta: 0.001800. Model-safe macro columns: 13. Warnings: 2. Errors: 0.

## Macro Holdout Comparison

| Metric | Baseline | Macro | Delta |
|---|---:|---:|---:|
| `accuracy` | 0.550800 | 0.540800 | -0.010000 |
| `auc` | 0.508200 | 0.510000 | 0.001800 |
| `avg_all_5d_return` | 0.005280 | 0.005280 | 0.000000 |
| `avg_top5_5d_return` | 0.006150 | 0.006460 | 0.000310 |
| `excess_top5_return` | 0.000870 | 0.001180 | 0.000310 |

**Relative excess-return lift:** 35.63%

## Macro Feature Importance

- Selected scope: `macro_model_only`
- Macro-like feature importance share: `0.484689`
- Macro-like feature count: `12`

### Top Macro-Like Features

| Feature | Importance |
|---|---:|
| `surprise_num` | 0.113848 |
| `macro_signal_score` | 0.099349 |
| `macro_tone_score` | 0.079520 |
| `liquidity_num` | 0.049985 |
| `five_day_market_bias_score` | 0.047156 |
| `reaction_quality_num` | 0.022999 |
| `growth_num` | 0.022259 |
| `five_day_bias_num` | 0.021873 |
| `macro_confidence` | 0.017099 |
| `rate_policy_num` | 0.006244 |

## Macro Presence In Training Data

- Model-safe training file: `data/processed/training_data_model_safe_with_macro.csv`
- Model-safe macro columns: `['macro_tone_num', 'surprise_num', 'inflation_num', 'growth_num', 'rate_policy_num', 'liquidity_num', 'reaction_quality_num', 'five_day_bias_num', 'macro_tone_score', 'five_day_market_bias_score', 'macro_confidence', 'macro_signal_score', 'has_macro_context']`
- Existing training files with macro columns: `1`

| File | Exists | Macro-like columns | Expected macro columns present |
|---|---:|---|---|
| `data/processed/training_data_model_safe_with_macro.csv` | True | `['macro_tone_num', 'surprise_num', 'inflation_num', 'growth_num', 'rate_policy_num', 'liquidity_num', 'reaction_quality_num', 'five_day_bias_num', 'macro_tone_score', 'five_day_market_bias_score', 'macro_confidence', 'macro_signal_score', 'has_macro_context']` | `['macro_signal_score', 'macro_tone_score', 'surprise_num', 'inflation_num', 'growth_num', 'rate_policy_num', 'liquidity_num', 'reaction_quality_num', 'five_day_market_bias_score']` |
| `data/processed/training_data_with_macro.csv` | False | `[]` | `[]` |
| `data/processed/stock_training_data_with_macro.csv` | False | `[]` | `[]` |
| `data/processed/merged_stock_macro_features.csv` | False | `[]` | `[]` |
| `data/llm_training/training_data_with_macro.csv` | False | `[]` | `[]` |
| `data/llm_training/stock_training_data_with_macro.csv` | False | `[]` | `[]` |
| `data/llm_training/merged_stock_macro_features.csv` | False | `[]` | `[]` |

## Available Macro-Related Files

- Files found: `7`
- `data/processed/macro_llm_features.csv`
- `data/processed/macro_model_features.csv`
- `data/processed/salarium_training_with_macro.csv`
- `data/processed/training_data_model_safe_with_macro.csv`
- `results/macro_feature_audit_summary.csv`
- `results/macro_feature_importance.csv`
- `results/macro_model_comparison.csv`

## Tournament Context

- Groups: `['macro_holdout', 'strategy_walkforward', 'walkforward_rank']`
- Macro candidates: `['technical_plus_macro_llm', 'macro_signal_score_only', 'macro_tone_score_only', 'technical_plus_macro_combo']`
- Positive strategy walk-forward baselines: `6`

## Warnings

- Macro model has lower accuracy than baseline. This may be acceptable if ranking return improves.
- Macro holdout and strategy walk-forward candidates are still not directly comparable. Macro needs to be tested through the same walk-forward engine.

## Required Next Upgrade

Build a macro-aware model-safe training dataset, then run macro-aware candidates through the same walk-forward engine used by the Strategy Walkforward Agent. Until then, the macro edge is promising but not proven under walk-forward validation.
