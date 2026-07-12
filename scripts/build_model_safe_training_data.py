from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


SRC = Path("data/processed/training_data.csv")
OUT = Path("data/processed/training_data_model_safe.csv")


def compute_rsi(price: pd.Series, window: int = 14) -> pd.Series:
    delta = price.diff()
    gain = delta.clip(lower=0).rolling(window).mean()
    loss = (-delta.clip(upper=0)).rolling(window).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def main() -> None:
    if not SRC.exists():
        raise FileNotFoundError(f"Missing source file: {SRC}")

    df = pd.read_csv(SRC)

    required = {"date", "ticker"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    price_col = "adj_close" if "adj_close" in df.columns else "close"

    if price_col not in df.columns:
        raise ValueError("Need adj_close or close column.")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()

    df = df.sort_values(["ticker", "date"]).reset_index(drop=True)

    # Drop explicit leakage helper column. Keep target_5d_return as target only.
    if "future_close_5d" in df.columns:
        df = df.drop(columns=["future_close_5d"])

    # Replace infinities with NaN before feature work.
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    if numeric_cols:
        df[numeric_cols] = df[numeric_cols].replace([np.inf, -np.inf], np.nan)

    if "return_1d" not in df.columns:
        df["return_1d"] = df.groupby("ticker")[price_col].pct_change()

    if "return_5d" not in df.columns:
        df["return_5d"] = df.groupby("ticker")[price_col].pct_change(5)

    df["momentum_5d"] = df["return_5d"]
    df["momentum_20d"] = df.groupby("ticker")[price_col].pct_change(20)

    df["volatility_20d"] = (
        df.groupby("ticker")["return_1d"]
        .rolling(20)
        .std()
        .reset_index(level=0, drop=True)
    )

    df["ma20"] = (
        df.groupby("ticker")[price_col]
        .rolling(20)
        .mean()
        .reset_index(level=0, drop=True)
    )

    df["ma50"] = (
        df.groupby("ticker")[price_col]
        .rolling(50)
        .mean()
        .reset_index(level=0, drop=True)
    )

    df["price_vs_ma20"] = df[price_col] / df["ma20"] - 1
    df["price_vs_ma50"] = df[price_col] / df["ma50"] - 1

    df["rsi_14d"] = (
        df.groupby("ticker")[price_col]
        .apply(lambda s: compute_rsi(s, 14))
        .reset_index(level=0, drop=True)
    )

    date_avg_momentum = df.groupby("date")["momentum_20d"].transform("mean")
    df["relative_strength"] = df["momentum_20d"] - date_avg_momentum

    # Final safety cleanup.
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    if numeric_cols:
        df[numeric_cols] = df[numeric_cols].replace([np.inf, -np.inf], np.nan)

    target_col = "target_5d_return"
    if target_col in df.columns:
        before = len(df)
        df = df.dropna(subset=["date", "ticker", target_col])
        after = len(df)
        print(f"Dropped {before - after} rows with missing date/ticker/target.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)

    print(f"Wrote {OUT}")
    print(f"Rows: {len(df):,}")
    print(f"Tickers: {df['ticker'].nunique():,}")
    print(f"Columns: {len(df.columns):,}")
    print("Columns:", list(df.columns))


if __name__ == "__main__":
    main()
