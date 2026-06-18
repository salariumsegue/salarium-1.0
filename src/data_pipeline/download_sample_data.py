import os
import pandas as pd
import yfinance as yf

TICKERS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META",
    "GOOGL", "GOOG", "TSLA", "JPM", "UNH",
    "V", "MA", "XOM", "LLY", "AVGO",
    "COST", "WMT", "HD", "KO", "PEP",
    "ORCL", "CRM", "AMD", "NFLX", "BAC",
    "QCOM", "MCD", "CSCO", "INTC", "ADBE"
]

START_DATE = "2018-01-01"
OUTPUT_DIR = "data/raw"

os.makedirs(OUTPUT_DIR, exist_ok=True)

for ticker in TICKERS:
    print(f"Downloading {ticker}...")

    try:
        df = yf.Ticker(ticker).history(
            start=START_DATE,
            auto_adjust=False,
            actions=False,
            interval="1d"
        )

        if df.empty:
            print(f"  No data returned for {ticker}")
            continue

        # Move Date from index to a regular column
        df = df.reset_index()

        # Clean column names
        df.columns = [
            str(col).strip().lower()
            .replace(" ", "_")
            .replace(".", "_")
            .replace(":", "_")
            for col in df.columns
        ]

        # Normalize date column
        if "datetime" in df.columns and "date" not in df.columns:
            df = df.rename(columns={"datetime": "date"})
        if "index" in df.columns and "date" not in df.columns:
            df = df.rename(columns={"index": "date"})

        # Keep only the columns we need
        keep_cols = ["date", "open", "high", "low", "close", "adj_close", "volume"]
        df = df[[c for c in keep_cols if c in df.columns]]

        # Final validation
        required = ["date", "open", "high", "low", "close", "volume"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"{ticker} missing required columns: {missing}. Got: {df.columns.tolist()}")

        file_path = os.path.join(OUTPUT_DIR, f"{ticker}.csv")
        df.to_csv(file_path, index=False)

        print(f"  Saved to {file_path} ({len(df)} rows)")

    except Exception as e:
        print(f"  Failed for {ticker}: {e}")

print("Done.")