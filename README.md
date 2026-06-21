# Salarium 1.0

**Salarium** is a systematic equity research platform designed to rank stocks using quantitative signals, evaluate performance through backtesting, and test whether macroeconomic interpretation can improve stock selection.

The name comes from *salarium*, the Roman soldier’s pay allowance, which later influenced the modern word “salary.”

---

## Project Overview

Salarium 1.0 started as a quantitative stock-ranking and backtesting system. It has now expanded into an early **Salarium 2.0 research layer** that uses a local LLM to interpret macroeconomic events and convert them into structured model features.

The goal is not to build a black-box trading bot. The goal is to build a research platform that can answer:

> Do technical, market, and macro signals improve stock ranking and portfolio selection?

---

## Current Capabilities

### Quantitative Research Engine

* Historical market data collection
* Stock universe construction
* Technical feature engineering
* Momentum and relative strength signals
* Volatility and RSI features
* Moving-average distance features
* 5-day forward return target generation
* Cross-sectional stock ranking
* Top-N portfolio testing
* Random forest model comparison
* Feature importance analysis

### Local LLM Macro Layer

Salarium now includes an experimental local LLM pipeline powered by **Ollama**, allowing macro event interpretation to run locally on a laptop without paid API usage.

Current LLM macro pipeline:

```text
Raw macro event data
        ↓
Local Ollama LLM interpretation
        ↓
Structured macro classifications
        ↓
Numeric macro feature encoding
        ↓
Merged stock + macro training dataset
        ↓
Model comparison against baseline
```

The LLM interprets macro events such as:

* CPI reports
* FOMC decisions
* Jobs reports
* Retail sales
* Consumer confidence
* Banking stress events
* Market shocks
* Rate-cut and liquidity regime changes

The output is converted into structured features such as:

* `macro_tone_score`
* `surprise_num`
* `inflation_num`
* `growth_num`
* `rate_policy_num`
* `liquidity_num`
* `reaction_quality_num`
* `macro_signal_score`

---

## Current Dataset

Current experimental dataset:

```text
Stock universe: 20 large-cap stocks
Date range: 2020-01-31 to 2026-06-11
Rows: 31,980
Target: 5-day forward return
```

Current macro coverage is built from an expanded seed macro-event dataset covering major events from 2020 through 2025.

---

## Current Results

### Baseline Model vs. Macro LLM Model

The current model comparison tests whether adding macro LLM features improves stock ranking.

| Model                 | Accuracy |    AUC | Avg Universe 5D Return | Avg Top-5 5D Return | Excess Top-5 Return |
| --------------------- | -------: | -----: | ---------------------: | ------------------: | ------------------: |
| Technical Only        |   0.5508 | 0.5082 |                 0.528% |              0.615% |              0.087% |
| Technical + Macro LLM |   0.5408 | 0.5100 |                 0.528% |              0.646% |              0.118% |

### Interpretation

The macro LLM model currently improves the simulated top-5 ranking return from:

```text
0.087% excess return per 5-day period
```

to:

```text
0.118% excess return per 5-day period
```

This is a small but encouraging improvement. The result should be treated as **experimental**, because the macro event dataset is still a manually created research seed and needs to be expanded and validated before drawing strong conclusions.

---

## Architecture

```text
Data Layer
    ↓
Feature Engineering Layer
    ↓
Technical Signal Layer
    ↓
Local Macro LLM Layer
    ↓
Feature Encoding Layer
    ↓
Merged Training Dataset
    ↓
Ranking Model
    ↓
Portfolio Selection
    ↓
Backtesting / Model Comparison
```

---

## Key Files

```text
configs/
    stock_universe.csv
    llm_config.yaml

data/raw/
    macro_events_seed.csv
    macro_events_expanded.csv

data/processed/
    training_data.csv
    macro_llm_features.csv
    macro_model_features.csv
    salarium_training_with_macro.csv

src/data_pipeline/
    build_dataset.py
    download_sample_data.py

src/features/
    build_features.py
    build_stock_training_data.py

src/llm/
    macro_schema.py
    macro_prompt.py
    macro_interpreter.py
    macro_rules.py
    create_expanded_macro_events.py
    build_macro_features.py
    encode_macro_features.py
    merge_macro_features.py
    run_macro_example.py

src/models/
    train_baseline.py
    train_feature_model.py
    train_rank_portfolio.py
    train_timeseries_baseline.py
    diagnose_macro_dataset.py
    train_macro_comparison.py

results/
    macro_model_comparison.csv
    macro_feature_importance.csv
```

---

## How to Run

### 1. Create and activate virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install pandas numpy yfinance scikit-learn requests pydantic
```

### 3. Install and run Ollama

Install Ollama from:

```text
https://ollama.com
```

Then pull a local model:

```bash
ollama pull llama3.2:1b
```

### 4. Build stock training data

```bash
python -m src.features.build_stock_training_data
```

### 5. Build expanded macro event dataset

```bash
python -m src.llm.create_expanded_macro_events
```

### 6. Run local LLM macro interpretation

```bash
python -m src.llm.build_macro_features
```

### 7. Encode macro outputs into numeric model features

```bash
python -m src.llm.encode_macro_features
```

### 8. Merge macro features with stock training data

```bash
python -m src.llm.merge_macro_features
```

### 9. Diagnose macro dataset coverage

```bash
python -m src.models.diagnose_macro_dataset
```

### 10. Compare baseline vs macro-enhanced model

```bash
python -m src.models.train_macro_comparison
```

---

## Salarium 2.0 Roadmap

### Macro / LLM Research

* Expand macro event dataset from seed events to 100+ verified events
* Add real actual-vs-consensus economic release data
* Add FRED/BLS/BEA macro data integrations
* Improve local LLM prompt quality
* Add stronger rule-based validation for macro contradictions
* Compare local models such as Llama, Qwen, and Mistral
* Test whether macro features improve results across different market regimes

### Modeling

* Add XGBoost / LightGBM models
* Add walk-forward validation
* Add rolling-window retraining
* Add sector-neutral ranking
* Add long/short portfolio construction
* Add transaction cost assumptions
* Add drawdown and Sharpe analysis
* Add confidence-weighted position sizing

### Additional Signal Layers

* Earnings transcript analysis
* News sentiment layer
* SEC filing analysis
* Market regime detection
* Yield curve and liquidity regime features
* Sector rotation signals

### Product Layer

* Streamlit dashboard
* Daily top-pick report
* Model explanation view
* Portfolio backtest dashboard
* Macro regime dashboard

---

## Current Research Question

The main research question for the next phase is:

> Does adding structured macro interpretation from a local LLM improve Salarium’s stock ranking performance out of sample?

Current early evidence suggests a small improvement in top-5 ranking returns, but the dataset is not yet large enough to claim a durable edge.

---

## Disclaimer

This project is for educational and research purposes only. It is not financial advice, investment advice, or a live trading system.

