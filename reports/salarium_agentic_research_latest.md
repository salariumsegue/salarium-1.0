# Salarium Agentic Research Final Report

**Status:** warn

**Summary:** Final research report status: warn. Phase status: complete_with_warnings. Agent report statuses: {'warn': 7}. Warnings: 1. Errors: 0.

## Phase Verdict

**Phase status:** `complete_with_warnings`

The v0.1 agentic research layer is structurally complete. It should be treated as a research MVP, not a tradable system.

## Git / Registry Snapshot

| Field | Value |
|---|---|
| Branch | `phase2-open-source-dashboard-universe` |
| Commit | `c33c0c77ce895cf1244a8d9d1b2ce000a55e3e16` |
| Dirty at final report run | `True` |
| Latest registry manifest | `data/runs/2026-07-08_195751_experiment_registry/manifest.json` |
| Latest registry run ID | `2026-07-08_195751_experiment_registry` |

## Agent Status Table

| Agent | Status | Summary |
|---|---|---|
| `backtest_reviewer` | `warn` | Backtest review status: warn. Overall avg net excess 5D return: 0.001446. Overall Spearman IC: 0.006883. Overall long/short 5D return: 0.001887. Diagnosis: Promising but not proven. The ranking signal appears positive overall, but weak periods need investigation. Warnings: 4. Errors: 0. |
| `model_tournament` | `warn` | Model tournament status: warn. Candidates evaluated: 18. Best in macro_holdout: technical_plus_macro_llm (score 1.3616). Best in strategy_walkforward: macro_signal_score_only (score -1.0661). Best in walkforward_rank: current_walkforward_rank_model (score 1.4581). Warnings: 4. Errors: 0. |
| `strategy_walkforward` | `warn` | Strategy walk-forward status: warn. Strategies evaluated: 15. Best strategy: macro_signal_score_only (score -1.0518, net excess 5D 0.000633, IC -0.001839). Warnings: 3. Errors: 0. |
| `data_quality_leakage` | `warn` | Data quality and leakage status: warn. Universe tickers: 125. Training rows: 261993. Training tickers: 125. Suspicious leakage columns: 0. Warnings: 3. Errors: 0. |
| `risk_portfolio` | `warn` | Risk portfolio status: warn. Net excess 5D: 0.001446. Max drawdown: -50.22%. Avg turnover: 1.083. Weak years: 6. Warnings: 7. Errors: 0. |
| `macro_feature_audit` | `warn` | Macro feature audit status: warn. Macro holdout excess Top-5 delta: 0.000310. Relative excess lift: 35.63%. AUC delta: 0.001800. Model-safe macro columns: 13. Warnings: 2. Errors: 0. |
| `experiment_registry` | `warn` | Experiment registry status: warn. Run ID: 2026-07-08_195751_experiment_registry. Branch: phase2-open-source-dashboard-universe. Commit: c33c0c77ce895cf1244a8d9d1b2ce000a55e3e16. Latest agent report statuses: {'warn': 6}. Warnings: 1. Errors: 0. |

## Strategic Read

Salarium now has an 8-agent local research loop. The system is structurally complete for v0.1, but the research conclusions remain cautionary.

### What is working
- The current walk-forward rank model still beats naive strategy walk-forward baselines.
- The model tournament, reviewer, data-quality, risk, macro-audit, and registry layers all produce auditable artifacts.
- The macro holdout result remains promising enough to justify a proper macro-aware walk-forward test.

### Main risks
- The walk-forward ranking signal has weak Spearman IC.
- Portfolio drawdown and turnover are still too high for strong strategy claims.
- The universe is currently a temporary 138-ticker consistency universe, not the final top-125 market-cap universe.
- Macro features are not yet present in the model-safe walk-forward file.
- Macro holdout and walk-forward tests are not directly comparable yet.

### Next phase
- Build macro-aware model-safe training data.
- Replace temporary 138-ticker universe with the true top-125 market-cap snapshot.
- Run macro-aware candidates through the same walk-forward engine.
- Add portfolio constraints: turnover caps, sector caps, position persistence, and drawdown controls.
- Then prepare open-source docs and reproducibility instructions.

## Stopping Point

This is the correct stopping point for Phase 1. Do not add more agents yet. The next phase should focus on data quality, macro-aware walk-forward testing, portfolio constraints, and open-source documentation.

## Recommended Tag

```bash
git tag v0.1-agentic-research-mvp
```

## Warnings
- One or more required agent reports has warning status.
