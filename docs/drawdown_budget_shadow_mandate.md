# Drawdown-Budget Shadow Mandate

## Approval

The `drawdown_budget_78_m3` candidate is approved for shadow/paper tracking only as of 2026-08-12 03:32:34 UTC. The mandate uses a hypothetical USD 100,000 notional balance.

Approval does not change the canonical Salarium release, connect a brokerage, generate orders, submit trades, or allocate live capital.

## Activation

The ledger begins with the first release-aligned, point-in-time portfolio snapshot generated after approval. Historical observations are not backfilled into the forward ledger. This prevents previously inspected returns from being relabeled as paper performance.

The mandate is currently `approved_awaiting_first_eligible_snapshot` because no post-approval release-aligned portfolio snapshot exists in the governed artifacts.

## Policy

- Soft floor: 78% of the running paper-account high-water mark.
- Cushion multiplier: 3.0x.
- Maximum equity exposure: 1.0x.
- Residual cash proxy: BIL.
- Cash-turnover assumption: 10 basis points.
- Rebalance cadence: each governed 10-trading-day Salarium rebalance.

## Monitoring

Every observation must retain the source snapshot timestamp and SHA-256 hash, baseline and shadow exposures, cash weight, paper NAV before and after the interval, net return, and resulting drawdown.

Mandatory review events include a 20% or 25% paper drawdown, exposure below 5% for three consecutive rebalances, a provenance failure, or any policy-parameter change.

No promotion review occurs before at least 26 forward observations and 365 calendar days. Promotion is never automatic and continues to require independent evidence plus explicit release approval.

Mandate configuration: `configs/drawdown_budget_shadow_mandate.json`.

Forward ledger: `reports/shadow/drawdown_budget_shadow_ledger.csv`.
