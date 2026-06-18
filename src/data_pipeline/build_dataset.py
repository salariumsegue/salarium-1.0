import os
import ast
import pandas as pd

RAW_DIR = "data/raw"
OUTPUT_DIR = "data/processed"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def normalize_col(col):
    """
    Convert headers like:
    "('date', '')" -> "date"
    "('open', 'csco')" -> "open"
    "Date" -> "date"
    """
    if isinstance(col, tuple):
        col = col[0] if len(col) > 0 else col
    else:
        col_str = str(col).strip()

        # Handle stringified tuples from pandas CSV output
        if col_str.startswith("(") and col_str.endswith(")"):
            try:
                parsed = ast.literal_eval(col_str)
                if isinstance(parsed, tuple) and len(parsed) > 0:
                    col = parsed[0]
                else:
                    col = col_str
            except Exception:
                col = col_str
        else:
            col = col_str

    col = str(col).strip().lower()
    col = col.replace(" ", "_")
    col = col.replace(".", "_")
    col = col.replace(":", "_")
    return col

def load_and_prepare_stock(file_path: str, ticker: str) -> pd.DataFrame:
    df = pd.read_csv(file_path)

    # Normalize column names
    df.columns = [normalize_col(col) for col in df.columns]

    # Find date column
    if "date" not in df.columns:
        if "datetime" in df.columns:
            df = df.rename(columns={"datetime": "date"})
        elif "unnamed__0" in df.columns:
            df = df.rename(columns={"unnamed__0": "date"})
        else:
            raise ValueError(
                f"No date column found in {file_path}. Columns: {df.columns.tolist()}"
            )

    # Required columns
    required_cols = ["open", "high", "low", "close", "volume"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(
            f"Missing columns in {file_path}: {missing}. Columns: {df.columns.tolist()}"
        )

    # Clean and sort
    df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True).dt.tz_localize(None)
    
    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

    # Keep ticker
    df["ticker"] = ticker

    # Target
    df["future_close_5d"] = df["close"].shift(-5)
    df["target_5d_return"] = (df["future_close_5d"] - df["close"]) / df["close"]

    # Basic features
    df["return_1d"] = df["close"].pct_change()
    df["return_5d"] = df["close"].pct_change(5)
    df["volume_change_1d"] = df["volume"].pct_change()
    df["high_low_spread"] = (df["high"] - df["low"]) / df["close"]
    df["open_close_spread"] = (df["close"] - df["open"]) / df["open"]

    df = df.dropna().reset_index(drop=True)

    return df

all_dfs = []

for filename in os.listdir(RAW_DIR):
    if filename.endswith(".csv"):
        ticker = filename.replace(".csv", "")
        file_path = os.path.join(RAW_DIR, filename)
        print(f"Processing {ticker}...")

        stock_df = load_and_prepare_stock(file_path, ticker)
        all_dfs.append(stock_df)

if not all_dfs:
    raise ValueError("No CSV files found in data/raw")

combined_df = pd.concat(all_dfs, ignore_index=True)

output_file = os.path.join(OUTPUT_DIR, "training_data.csv")
combined_df.to_csv(output_file, index=False)

print(f"Saved training data to {output_file}")
print(f"Rows: {len(combined_df)}")
print(f"Columns: {len(combined_df.columns)}")
print(f"Tickers: {combined_df['ticker'].nunique()}")
