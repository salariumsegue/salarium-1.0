# Forward Paper Operations

Salarium publishes two records with different roles:

- The release backtest is frozen historical research. It is never rewritten by the forward job.
- The forward paper snapshot scores newly available market-close data with a frozen, hashed 20-day model and appends completed holding intervals to a paper ledger.

The forward process is paper-only. It cannot connect to a broker, create orders, submit orders, or allocate live capital.

## Daily operation

The refresh is intended to run after the US market close. A publication is rejected when the price data is stale, fewer than 95% of the governed Liquid-500 names are present, fewer than 95% of the names produce complete features, the universe hash changes unexpectedly, or the frozen model hash does not match its manifest.

Rankings may refresh after each eligible close. The paper portfolio changes only after ten new trading sessions. The first post-approval snapshot initializes the account without backfilling any previously observed return. Completed intervals are appended to `reports/shadow/drawdown_budget_shadow_ledger.csv`.

The current macro inputs do not have a governed live feed. Until one exists, forward exposure fails closed to the neutral 75% baseline before the drawdown-budget controller applies its lower cap. This fallback is disclosed in the public snapshot.

## Model updates

Daily inference does not retrain the model. A new model requires a separate training run, the complete validation suite, a new model hash and manifest, comparison against the frozen model, and explicit release approval. Replacing the model must never rewrite prior paper observations.

## Automation

The repository contains the manual refresh command and all validation gates. A scheduled job that writes commits and triggers deployments is intentionally not enabled until that ongoing external authority is explicitly approved.
