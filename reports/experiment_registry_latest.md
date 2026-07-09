# Salarium Experiment Registry Agent Report

**Status:** pass

**Summary:** Experiment registry status: pass. Run ID: 2026-07-08_200623_experiment_registry. Branch: phase2-open-source-dashboard-universe. Commit: 8a440dd7d29f7cef0398ef3f68a7451764dbc97f. Latest agent report statuses: {'warn': 6}. Warnings: 0. Errors: 0.

## Git Snapshot

| Field | Value |
|---|---|
| Branch | `phase2-open-source-dashboard-universe` |
| Commit | `8a440dd7d29f7cef0398ef3f68a7451764dbc97f` |
| Dirty before registry run | `False` |

## Latest Agent Reports

| Agent | Status | Path | Summary |
|---|---|---|---|
| `backtest_reviewer` | `warn` | `reports/backtest_reviewer_latest.md` | Backtest review status: warn. Overall avg net excess 5D return: 0.001446. Overall Spearman IC: 0.006883. Overall long/short 5D return: 0.001887. Diagnosis: Promising but not proven. The ranking signal appears positive overall, but weak periods need investigation. Warnings: 4. Errors: 0. |
| `model_tournament` | `warn` | `reports/model_tournament_latest.md` | Model tournament status: warn. Candidates evaluated: 18. Best in macro_holdout: technical_plus_macro_llm (score 1.3616). Best in strategy_walkforward: macro_signal_score_only (score -1.0661). Best in walkforward_rank: current_walkforward_rank_model (score 1.4581). Warnings: 4. Errors: 0. |
| `strategy_walkforward` | `warn` | `reports/strategy_walkforward_latest.md` | Strategy walk-forward status: warn. Strategies evaluated: 15. Best strategy: macro_signal_score_only (score -1.0518, net excess 5D 0.000633, IC -0.001839). Warnings: 3. Errors: 0. |
| `data_quality_leakage` | `warn` | `reports/data_quality_leakage_latest.md` | Data quality and leakage status: warn. Universe tickers: 125. Training rows: 261993. Training tickers: 125. Suspicious leakage columns: 0. Warnings: 3. Errors: 0. |
| `risk_portfolio` | `warn` | `reports/risk_portfolio_latest.md` | Risk portfolio status: warn. Net excess 5D: 0.001446. Max drawdown: -50.22%. Avg turnover: 1.083. Weak years: 6. Warnings: 7. Errors: 0. |
| `macro_feature_audit` | `warn` | `reports/macro_feature_audit_latest.md` | Macro feature audit status: warn. Macro holdout excess Top-5 delta: 0.000310. Relative excess lift: 35.63%. AUC delta: 0.001800. Model-safe macro columns: 13. Warnings: 2. Errors: 0. |

## Registered Result Artifacts

| Name | Exists | Path | SHA256 |
|---|---:|---|---|
| `walkforward_rank_summary` | `True` | `results/walkforward_rank_backtest_summary.csv` | `448caf6645ba` |
| `walkforward_rank_detail` | `True` | `results/walkforward_rank_backtest_results.csv` | `5d470fe31ebf` |
| `model_tournament_leaderboard` | `True` | `results/model_tournament_leaderboard.csv` | `bc8bf39fc36e` |
| `strategy_walkforward_summary` | `True` | `results/strategy_walkforward_tournament_summary.csv` | `8b144258315a` |
| `strategy_walkforward_detail` | `True` | `results/strategy_walkforward_tournament_results.csv` | `16c9a7b43129` |
| `model_tournament_inputs` | `True` | `results/model_tournament_inputs.csv` | `8b144258315a` |
| `data_quality_leakage_summary` | `True` | `results/data_quality_leakage_summary.csv` | `483a9de27c42` |
| `risk_portfolio_summary` | `True` | `results/risk_portfolio_summary.csv` | `3b1b81cc84e2` |
| `macro_feature_audit_summary` | `True` | `results/macro_feature_audit_summary.csv` | `f400eda4eece` |
| `macro_model_comparison` | `True` | `results/macro_model_comparison.csv` | `3a5ac7b5931b` |
| `macro_feature_importance` | `True` | `results/macro_feature_importance.csv` | `de6d8dd052d1` |

## Known Limitations

- Current walk-forward rank model still has material drawdown and turnover risk.
- Macro holdout and walk-forward rank tests are still not directly comparable.

## Manifest

`data/runs/2026-07-08_200623_experiment_registry/manifest.json`

## Next Step

Proceed to Agent 8: Final Research Report / Orchestrator Agent. Agent 8 should read this manifest and all latest reports, then produce one final phase summary.
