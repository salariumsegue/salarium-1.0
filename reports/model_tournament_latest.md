# Salarium Model Tournament Agent Report

**Status:** warn

**Summary:** Model tournament status: warn. Candidates evaluated: 3. Best in macro_holdout: technical_plus_macro_llm (score 1.3616). Best in walkforward_rank: current_walkforward_rank_model (score 1.4581). Warnings: 4. Errors: 0.

## Tournament Leaderboard

| Group | Rank | Candidate | Score | Scope | Net Excess 5D | Long/Short 5D | Spearman IC | Excess Top-5 | AUC | Weak Periods |
|---|---:|---|---:|---|---:|---:|---:|---:|---:|---:|
| macro_holdout | 1 | `technical_plus_macro_llm` | 1.361600 | single_train_test_top5 |  |  |  | 0.001180 | 0.510000 |  |
| macro_holdout | 2 | `baseline_technical_only` | 1.053600 | single_train_test_top5 |  |  |  | 0.000870 | 0.508200 |  |
| walkforward_rank | 1 | `current_walkforward_rank_model` | 1.458118 | top10_walkforward | 0.001446 | 0.001887 | 0.006883 |  |  | 4 |

## Group Winners

- **macro_holdout**: `technical_plus_macro_llm` (score 1.3616, scope `single_train_test_top5`)
- **walkforward_rank**: `current_walkforward_rank_model` (score 1.4581, scope `top10_walkforward`)

## Interpretation

This is a tournament aggregator, not a full retraining engine yet. It ranks all available strategy/model result files using a consistent scoring formula. The next upgrade is to make every candidate run through the same walk-forward backtest.

## Warnings

- Walk-forward ranking IC is positive but weak.
- Walk-forward model has three or more weak periods.
- Macro holdout candidates are from a single train/test comparison. Current best macro-holdout candidate: technical_plus_macro_llm.
- Do not compare macro_holdout and walkforward_rank as identical tests yet. The next upgrade is to run every candidate through the same walk-forward engine.

## Score Formula

```json
{
  "avg_net_excess_5d": "1000x",
  "avg_long_short_5d": "500x",
  "avg_spearman_ic": "10x",
  "excess_top5_return": "1000x",
  "auc_above_0_5": "10x",
  "accuracy_above_0_5": "2x",
  "weak_period_count": "-0.25 each"
}
```
