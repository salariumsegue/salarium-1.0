# Roadmap

## Phase 1: Agentic research MVP

Completed:

- Backtest Reviewer Agent
- Model Tournament Agent
- Strategy Walkforward Agent
- Data Quality & Leakage Agent
- Risk & Portfolio Agent
- Macro Feature Audit Agent
- Experiment Registry Agent
- Final Research Report Agent

## Phase 2.1: Open-source architecture

Current focus:

- README
- Architecture docs
- Data docs
- Reproducibility docs
- Dashboard docs
- Audit script
- Research pipeline runner

## Phase 2.2: Macro merge semantics

Next technical priority:

- Determine whether macro features are global-by-date or ticker-adjusted.
- Rename ticker-adjusted macro columns if needed.
- Create clean global macro regime features if needed.
- Rerun data quality, macro audit, and tournament.

## Phase 2.3: Portfolio construction

Planned:

- Turnover-capped Top-10 / Top-20
- Position persistence
- Sector caps
- Volatility weighting
- Drawdown-aware risk mode

## Phase 2.4: Same-engine model tournament

Planned:

- Run every candidate through the same walk-forward engine.
- Compare technical, macro, technical+macro, and ML rankers fairly.

## Phase 2.5: Public dashboard

Planned:

- Better charts
- Equity curve
- Drawdown curve
- Turnover visualization
- Macro regime timeline
- Downloadable CSVs
