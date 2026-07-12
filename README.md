# Salarium

**Salarium** is a local-first, open-source, agentic equity research platform for systematic stock ranking, macro feature auditing, walk-forward validation, risk review, model tournaments, experiment tracking, and dashboard reporting.

It is designed to answer one core question:

> Can a modular research system combine technical signals, macro context, data-quality checks, backtesting, risk diagnostics, and agentic review to produce more credible equity-ranking research?

- Salarium is **not** a live trading bot.
- Salarium is **not** investment advice.
- Salarium is a research and engineering project.

---

## Current Status

Salarium is currently in **Phase 2: Open-source research platform buildout**.

The system has moved beyond a single model script into a modular architecture with:

- Top-125 equity universe construction
- Model-safe training data
- Macro-aware training data
- Global-by-date macro regime features
- Walk-forward strategy testing
- Model tournament comparison
- Data quality and leakage audits
- Risk and portfolio diagnostics
- Macro feature auditing
- Experiment registry manifests
- Final research report generation
- Streamlit dashboard

The current research conclusion is:

> Salarium has a real research pipeline and some promising signal evidence, but the strategy is not yet portfolio-ready. The main open problems are weak ranking IC, high turnover, large drawdown, and the need for same-engine macro interaction testing.

---

## Why Salarium Exists

Most beginner “AI trading bot” projects are fragile because they skip the hard parts:

- data leakage checks
- walk-forward validation
- transaction costs
- turnover
- drawdown
- weak periods
- model comparison
- reproducibility
- macro regime context
- honest limitations

Salarium is built to confront those problems directly.

The goal is not to claim that the model “beats the market.”
The goal is to build a research system that can say:

1. what worked,
2. what failed,
3. why it failed,
4. what should be tested next.

---

## Architecture Overview

```text
                             ┌─────────────────────────┐
                             │  Stock Universe Config  │
                             │ Top-125 Yahoo Universe  │
                             └────────────┬────────────┘
                                          │
                                          ▼
┌──────────────────────┐       ┌─────────────────────────┐
│ Price / OHLCV Data   │──────▶│ Technical Feature Build │
└──────────────────────┘       └────────────┬────────────┘
                                            │
                                            ▼
                             ┌──────────────────────────────┐
                             │ Model-Safe Training Dataset  │
                             │ returns, momentum, RSI, etc. │
                             └────────────┬─────────────────┘
                                          │
                                          ▼
┌──────────────────────┐       ┌──────────────────────────────┐
│ Macro LLM / Macro    │──────▶│ Global Macro Feature Builder │
│ Event Features       │       │ same macro value per date    │
└──────────────────────┘       └────────────┬─────────────────┘
                                            │
                                            ▼
                             ┌──────────────────────────────┐
                             │ Top-125 Global Macro Dataset │
                             └────────────┬─────────────────┘
                                          │
                                          ▼
          ┌────────────────────────────────────────────────────┐
          │                 Agentic Research Layer             │
          ├────────────────────────────────────────────────────┤
          │ 1. Backtest Reviewer Agent                         │
          │ 2. Model Tournament Agent                          │
          │ 3. Strategy Walkforward Agent                      │
          │ 4. Data Quality & Leakage Agent                    │
          │ 5. Risk & Portfolio Agent                          │
          │ 6. Macro Feature Audit Agent                       │
          │ 7. Experiment Registry Agent                       │
          │ 8. Final Research Report Agent                     │
          └──────────────────────┬─────────────────────────────┘
                                 │
                                 ▼
              ┌────────────────────────────────────┐
              │ Reports, CSV Results, Manifests    │
              └──────────────────┬─────────────────┘
                                 │
                                 ▼
              ┌────────────────────────────────────┐
              │ Streamlit Research Dashboard       │
              └────────────────────────────────────┘

