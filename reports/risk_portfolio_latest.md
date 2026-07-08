# Salarium Risk & Portfolio Agent Report

**Status:** warn

**Summary:** Risk portfolio status: warn. Net excess 5D: 0.001446. Max drawdown: -50.22%. Avg turnover: 1.083. Weak years: 6. Warnings: 9. Errors: 0.

## Overall Portfolio Risk

| Metric | Value |
|---|---:|
| `avg_net_top10_5d` | 0.004666 |
| `avg_universe_5d` | 0.003221 |
| `avg_net_excess_5d` | 0.001446 |
| `avg_long_short_5d` | 0.001887 |
| `avg_spearman_ic` | 0.006883 |
| `avg_turnover` | 1.082609 |
| `avg_transaction_cost` | 0.001083 |
| `net_hit_rate` | 0.565217 |
| `excess_hit_rate` | 0.510870 |
| `annualized_net_return` | 0.202255 |
| `net_sharpe` | 0.738870 |
| `excess_sharpe` | 0.362395 |
| `max_drawdown` | -0.502249 |

## Yearly Risk Flags

| Period | Net Excess 5D | Spearman IC | Long/Short 5D | Max Drawdown | Turnover | Flags |
|---|---:|---:|---:|---:|---:|---|
| 2021 | -0.003511 | -0.014626 | -0.004523 | -0.162598 | 1.121569 | negative_net_excess, negative_spearman_ic, negative_long_short, high_turnover |
| 2022 | -0.003027 | -0.029522 | -0.001270 | -0.364325 | 0.933333 | negative_net_excess, negative_spearman_ic, negative_long_short, drawdown_worse_than_20pct |
| 2023 | 0.006833 | 0.024756 | 0.007597 | -0.149104 | 1.148000 | high_turnover |
| 2024 | -0.000317 | 0.002409 | 0.001881 | -0.095924 | 1.019608 | negative_net_excess, high_turnover |
| 2025 | 0.006338 | 0.061748 | 0.008585 | -0.272591 | 1.184000 | drawdown_worse_than_20pct, high_turnover |
| 2026 | 0.003914 | -0.012897 | -0.003857 | -0.072980 | 1.104348 | negative_spearman_ic, negative_long_short, high_turnover |

## Top Name Concentration

| Ticker | Count | Frequency |
|---|---:|---:|
| `COIN` | 117 | 42.39% |
| `ROKU` | 116 | 42.03% |
| `NET` | 112 | 40.58% |
| `MDB` | 109 | 39.49% |
| `SHOP` | 105 | 38.04% |
| `WBD` | 87 | 31.52% |
| `ALB` | 82 | 29.71% |
| `UAL` | 69 | 25.00% |
| `AMD` | 64 | 23.19% |
| `INTC` | 61 | 22.10% |

## Tournament Risk Context

- Groups: `macro_holdout, strategy_walkforward, walkforward_rank`
- Best overall candidate by tournament score: `current_walkforward_rank_model` from `walkforward_rank` with score `1.4581177889106796`
- Positive simple strategy baselines: `0`

## Warnings

- Current walk-forward model has severe max drawdown worse than -30%.
- Current walk-forward model has high average turnover.
- Current walk-forward model has weak excess Sharpe.
- Current walk-forward model has weak ranking IC.
- At least one rebalance period has a net return worse than -10%.
- One ticker appears in more than 35% of selected portfolios.
- No simple strategy walk-forward baseline has positive net excess return.
- Best simple strategy baseline has non-positive net excess return.
- Best simple strategy baseline has non-positive Spearman IC.

## Interpretation

This agent does not decide whether Salarium is tradable. It identifies portfolio-level risks that must be solved before strategy claims are credible.
