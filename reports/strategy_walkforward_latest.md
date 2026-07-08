# Salarium Strategy Walkforward Agent Report

**Status:** fail

**Summary:** Strategy walk-forward failed because no strategy candidates could be created.

## Run Settings

| Setting | Value |
|---|---|
| `training_data_path` | `data/processed/training_data.csv` |
| `return_column` | `` |
| `top_n` | `` |
| `rebalance_step` | `` |
| `transaction_cost_per_turnover` | `` |
| `num_strategies` | `` |

## Warnings

- Not enough technical columns to create technical_combo.
- No macro score columns found. Macro baseline strategies will be skipped.

## Errors

- No strategy score columns could be created from the available features.

## Next Step

Run the Model Tournament Agent again. This agent wrote `results/model_tournament_inputs.csv`, so the tournament should now include these strategy walk-forward candidates.
