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

The approved automation is defined in `.github/workflows/forward-paper.yml`. It
runs at 6:30 p.m. `America/New_York` every Monday through Friday, after the
regular US market close and with additional time for the research feed to
settle. Market holidays and delayed closes are handled by the existing
coverage/staleness gates. If there is no newly eligible close, the job exits
without changing the ledger, snapshot, or repository.

Only three generated files may enter an automated release: the append-only
ledger, the current paper state, and the public forward-paper snapshot. A
dedicated diff gate rejects additions, deletions, untracked outputs, or any
change outside that allowlist. Fresh releases must then pass the full Python
suite, the tracked-artifact audit, and the website validation/build/smoke
checks before the workflow creates and pushes a commit. One concurrency group
prevents overlapping closes. A failed gate leaves the remote repository and
production site unchanged.

The workflow uses GitHub's short-lived `GITHUB_TOKEN` with repository-content
write permission; it does not require or commit a personal access token or
Vercel credential. The repository's Vercel Git integration is expected to
deploy the successful push.

GitHub runs scheduled workflows only from the repository's default branch.
Therefore this workflow becomes active only after the release branch containing
it is merged into the default branch. Repository rules must also permit the
workflow token to push governed snapshot commits. If either condition is not
met, the automation fails closed rather than weakening the safeguards.
