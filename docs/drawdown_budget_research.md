# Drawdown-Budget Controller Research

## Objective

Reduce the simulated maximum drawdown of Salarium's risk-controlled mandate below 25% without changing the Liquid-500 ranking model, Top-10 selection rule, covariance estimator, or 25% signal-aware blend.

## Design

The candidate is a transparent capital-cushion controller inspired by constant-proportion portfolio insurance. Before each 10-trading-day holding period, it calculates:

1. a soft floor equal to 78% of the running account high-water mark;
2. the current capital cushion above that floor;
3. an equity-exposure ceiling equal to three times the cushion as a fraction of current NAV; and
4. the final equity exposure as the lower of that ceiling and the existing Salarium risk-scaled exposure.

Unused capital earns the BIL adjusted-close total-return proxy. The equity return stream retains the original modeled transaction costs, and changes in the cash allocation add a separate 10-basis-point turnover charge. Total capital is capped at 1.0x.

The controller uses only NAV, the prior running high-water mark, and the exposure already known before each forward return. It does not use future returns, future volatility, or revised regime labels.

## Result

Across 139 simulated rebalance observations from January 2021 through May 2026:

| Record | Annualized net return | Net Sharpe | Maximum drawdown |
|---|---:|---:|---:|
| Existing risk-scaled policy plus Treasury-bill yield | 50.14% | 1.335 | -49.24% |
| Drawdown-budget candidate | 35.11% | 1.435 | -21.57% |
| Candidate, 2024-2026 temporal segment | 75.93% | 2.208 | -12.23% |

The candidate retained 70.04% of the comparator's annualized return and improved full-period Sharpe by 0.099. Its worst observed rebalance return was -8.83%.

## Robustness

- The maximum drawdown remained -21.59% at the frozen 25-basis-point cash-turnover stress.
- All 27 development, confirmation, and overall checks in the 77%-79% floor and 2.75x-3.25x multiplier neighborhood remained below 25% at 25-basis-point turnover cost.
- In 10,000 path-dependent six-rebalance circular-block bootstrap samples, the candidate remained below a 25% drawdown in 100% of samples and improved drawdown versus the cash-yield comparator in 99.5%.

These bootstrap results resample the observed return blocks and re-run the path-dependent controller. They do not model an unseen market regime or guarantee future protection.

## Shadow-mandate approval

The candidate was approved on 2026-08-12 for a USD 100,000 paper-only shadow mandate. It has no live capital, brokerage connection, order generation, or order submission. Its forward ledger starts with the first eligible release-aligned portfolio snapshot produced after approval; historical returns are not backfilled.

See `docs/drawdown_budget_shadow_mandate.md` for activation, monitoring, and review rules.

## Why it is not the canonical release yet

The entire 2021-2026 record was inspected during exploratory design. The 2024-2026 slice is therefore a temporal confirmation segment, not a pristine holdout. The research target is achieved, but canonical promotion is withheld pending explicit release approval and genuinely independent forward or newly sequestered evidence.

## Failure modes

- The 78% floor is soft. A gap between rebalance observations can breach it.
- A deep loss can shrink exposure close to zero and delay recovery. The observed candidate's minimum equity exposure was 1.65%, and its longest underwater period was 1,032 days.
- The BIL proxy is historical ETF evidence, not a guaranteed cash rate or executable institutional cash-management specification.
- The study covers only 139 integrated Salarium observations and cannot establish performance across every crisis type.

Source configuration: `configs/drawdown_budget_research.json`.
