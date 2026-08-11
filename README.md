# Salarium 1.0

**Salarium** is an open-source quantitative equity research platform for systematic stock ranking, walk-forward validation, portfolio construction, macro/risk analysis, experiment governance, and public research reporting.

> Salarium is a research and engineering project. It is not a live trading bot and it is not investment advice.

## Release Candidate

Salarium 1.0 is now in release-candidate hardening. The current research architecture is intentionally frozen while the project moves from model experimentation into documentation, reproducibility, deployment, and public presentation.

### Locked research architecture

```text
Liquid-500 universe
        ↓
20-trading-day alpha target
        ↓
Annual expanding-window walk-forward model
        ↓
Out-of-sample equity rankings
        ↓
Top-10 selection + rank-15 persistence buffer
        ↓
60D Ledoit-Wolf covariance
        ↓
75% covariance-risk / 25% signal-aware weighting
        ↓
Maximum-diversification risk anchor
        ↓
Governed portfolio exposure
        ↓
Hard leverage ceiling: 1.25x
```

The defensive comparator substitutes a shrinkage minimum-variance anchor.

## Current Research Evidence

The current core balanced candidate is the **Top-10 / 20D target / 10D rebalance / 60D shrinkage maximum-diversification / 25% signal-aware blend / governed risk-scaling** configuration.

Committed 2021-2026 expanding-window research results show approximately:

| Metric | Core balanced candidate |
|---|---:|
| Annualized simulated net return | 48.2% |
| Net Sharpe | 1.298 |
| Net Sortino | 2.678 |
| Maximum drawdown | -49.6% |
| Average exposure | 0.534x |
| Maximum realized exposure | 1.00x |

These are simulated historical results, not live trading performance. The backtest has meaningful limitations and should not be interpreted as evidence of future investment returns.

## Why the architecture changed

Salarium's research process explicitly tested and rejected several tempting assumptions:

- Expanding the universe toward ~2,000 names was technically feasible but reduced ranking quality under the existing model.
- Rebalancing every five days was not the strongest implementation. A 20-day prediction target with a 10-day rebalance cadence produced a stronger research frontier.
- Broadening the portfolio beyond the highest-ranked names reduced volatility but diluted alpha faster than it improved risk-adjusted performance.
- Covariance-aware Top-10 weighting improved the risk/return trade-off versus simple inverse-volatility weighting.
- More leverage was not automatically better. Salarium keeps a 1.25x ceiling, but the current governed research candidate did not need leverage above 1.00x.

## System Components

```text
Data & universe governance
        ↓
Feature engineering
        ↓
Walk-forward alpha model
        ↓
Out-of-sample score artifacts
        ↓
Portfolio construction
        ↓
Covariance + signal-aware weighting
        ↓
Macro / risk exposure control
        ↓
Research reports + experiment archive
        ↓
Streamlit command center + Next.js website
```

The repository includes:

- Liquid-500 and broad-universe research infrastructure
- Expanding-window walk-forward scoring
- Horizon/rebalance ablations
- Transaction-cost and turnover analysis
- Risk scaling and leverage governance
- Portfolio breadth experiments
- Ledoit-Wolf covariance research
- Signal-aware covariance optimization
- Macro-regime and risk-state tooling
- Data-quality and leakage audits
- Agentic research/reporting workflows
- Streamlit research dashboard
- Next.js public research website
- GitHub Actions continuous integration

## Reproducibility

Install Python dependencies:

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

Run the Python test suite:

```bash
python -m pytest -q
```

Run the Streamlit command center locally:

```bash
streamlit run app/streamlit_app.py
```

Build the public website:

```bash
cd web
npm ci
npm run lint
npm run build
```

## Release Documentation

- `docs/SALARIUM_1_0_MODEL_CARD.md`
- `docs/RELEASE_NOTES_1_0.md`
- `docs/RELEASE_CHECKLIST.md`
- `web/public/data/release_snapshot.json`

## Limitations

Salarium remains a research platform. Historical results are simulated and can be affected by data quality, survivorship or universe-selection effects, model overfitting, covariance-estimation error, regime shifts, approximate transaction costs, financing assumptions, and other implementation risks. The system does not place live orders.

## Name

*Salarium* refers to the Latin term associated with Roman pay/allowance and is the historical root of the modern word *salary*.
