from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf


UNIVERSE_FILE = Path("configs/stock_universe.csv")
OUTPUT_FILE = Path("data/processed/training_data.csv")

START_DATE = "2020-01-01"
BENCHMARK = "SPY"


def calculate_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    return rsi.fillna(50)


def get_close_prices(raw: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    closes = {}

    for ticker in tickers:
        try:
            closes[ticker] = raw[ticker]["Close"]
        except Exception:
            print(f"Skipping {ticker}: no close price found")

    return pd.DataFrame(closes)


def build_features_for_ticker(
    ticker: str,
    sector: str,
    close: pd.Series,
    spy_close: pd.Series,
) -> pd.DataFrame:
    df = pd.DataFrame()
    df["date"] = close.index
    df["ticker"] = ticker
    df["sector"] = sector
    df["close"] = close.values

    close = close.sort_index()
    spy_close = spy_close.reindex(close.index).ffill()

    returns_1d = close.pct_change()
    returns_5d = close.pct_change(5)
    returns_20d = close.pct_change(20)
    spy_returns_20d = spy_close.pct_change(20)

    df["return_1d"] = returns_1d.values
    df["momentum_5d"] = returns_5d.values
    df["momentum_20d"] = returns_20d.values
    df["volatility_20d"] = returns_1d.rolling(20).std().values
    df["rsi_14d"] = calculate_rsi(close, 14).values
    df["relative_strength"] = (returns_20d - spy_returns_20d).values

    df["ma_20"] = close.rolling(20).mean().values
    df["ma_50"] = close.rolling(50).mean().values
    df["price_vs_ma20"] = (close / close.rolling(20).mean() - 1).values
    df["price_vs_ma50"] = (close / close.rolling(50).mean() - 1).values

    future_return = close.shift(-5) / close - 1
    df["target_5d_return"] = future_return.values
    df["target_label"] = (future_return > 0).astype(int).values

    return df


def main():
    if not UNIVERSE_FILE.exists():
        raise FileNotFoundError(
            "configs/stock_universe.csv not found. Create the stock universe first."
        )

    universe = pd.read_csv(UNIVERSE_FILE)
    tickers = universe["ticker"].dropna().unique().tolist()

    all_tickers = sorted(set(tickers + [BENCHMARK]))

    print(f"Downloading {len(all_tickers)} tickers from Yahoo Finance...")
    raw = yf.download(
        all_tickers,
        start=START_DATE,
        auto_adjust=True,
        progress=True,
        group_by="ticker",
        threads=True,
    )

    closes = get_close_prices(raw, all_tickers)

    if BENCHMARK not in closes.columns:
        raise ValueError("SPY benchmark data was not downloaded correctly.")

    rows = []

    for _, row in universe.iterrows():
        ticker = row["ticker"]
        sector = row["sector"]

        if ticker not in closes.columns:
            print(f"Skipping {ticker}: missing close data")
            continue

        print(f"Building features for {ticker}")

        ticker_features = build_features_for_ticker(
            ticker=ticker,
            sector=sector,
            close=closes[ticker],
            spy_close=closes[BENCHMARK],
        )

        rows.append(ticker_features)

    dataset = pd.concat(rows, ignore_index=True)

    dataset = dataset.dropna(
        subset=[
            "momentum_20d",
            "volatility_20d",
            "rsi_14d",
            "relative_strength",
            "target_5d_return",
        ]
    )

    dataset["date"] = pd.to_datetime(dataset["date"]).dt.date

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(OUTPUT_FILE, index=False)

    print()
    print(f"Saved stock training data to {OUTPUT_FILE}")
    print(f"Rows: {len(dataset):,}")
    print(f"Tickers: {dataset['ticker'].nunique()}")
    print(f"Date range: {dataset['date'].min()} to {dataset['date'].max()}")
    print()
    print("Columns:")
    print(list(dataset.columns))


if __name__ == "__main__":
    main()
